# app/workers/generation_worker.py
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.models.lecture import Lecture, LectureStatus
from app.models.teacher import Teacher

logger = logging.getLogger(__name__)


async def run_generation(ctx: dict, lecture_id: int) -> None:
    """
    ARQ background job — runs hololearn_pipeline.py for a single lecture.

    Called by the ARQ worker after trigger-pipeline enqueues the lecture_id.
    ctx is injected by ARQ (worker context) — we don't use it but it's required.

    Flow:
      1. Fetch lecture + teacher from DB
      2. Guard: preprocessed image must exist on disk
      3. Resolve voice priority chain
      4. Create isolated output directory for this lecture
      5. Build subprocess command
      6. Set status = GENERATING, commit (visible to frontend immediately)
      7. subprocess.run() — blocks for 5–25 min
      8. On success: COMPLETED + output_video_path
      9. On failure: FAILED + error_message
    """
    with Session(engine) as session:

        # ── Fetch records ──────────────────────────────────────────
        lecture = session.get(Lecture, lecture_id)
        if not lecture:
            logger.error(f"[Generation:{lecture_id}] Lecture not found in DB")
            return

        teacher = session.get(Teacher, lecture.teacher_id)
        if not teacher:
            logger.error(f"[Generation:{lecture_id}] Teacher {lecture.teacher_id} not found in DB")
            _fail(session, lecture, "Teacher record not found")
            return

        # ── Guard: pipeline must be configured ────────────────────
        if not settings.LONGCAT_ENV_PYTHON or not settings.PIPELINE_SCRIPT:
            logger.error(f"[Generation:{lecture_id}] Pipeline not configured in .env")
            _fail(session, lecture, "Pipeline not configured. Set LONGCAT_ENV_PYTHON and PIPELINE_SCRIPT in .env")
            return

        # ── Guard: preprocessed image must exist on disk ───────────
        # The onboarding worker writes this after preprocess_image.py succeeds.
        # If it's missing, avatar model has no face to work with.
        if not teacher.preprocessed_image_path:
            logger.error(f"[Generation:{lecture_id}] preprocessed_image_path is not set on teacher")
            _fail(session, lecture, "preprocessed_image_path is not set. Teacher must re-upload photo.")
            return

        if not Path(teacher.preprocessed_image_path).exists():
            logger.error(f"[Generation:{lecture_id}] preprocessed_image_path not found on disk: {teacher.preprocessed_image_path}")
            _fail(session, lecture, f"Preprocessed image not found on disk: {teacher.preprocessed_image_path}")
            return

        # ── Guard: script file must exist on disk ─────────────────
        if not lecture.script_path:
            logger.error(f"[Generation:{lecture_id}] script_path is not set on lecture")
            _fail(session, lecture, "script_path is not set. Upstream module must set it before triggering.")
            return

        if not Path(lecture.script_path).exists():
            logger.error(f"[Generation:{lecture_id}] script_path not found on disk: {lecture.script_path}")
            _fail(session, lecture, f"Script file not found on disk: {lecture.script_path}")
            return

        # ── Resolve voice priority chain ───────────────────────────
        # Priority: cached .pt > voice_ref .wav > no flag (pipeline default)
        # If cached_voice_path is set in DB but missing on disk → fall back silently
        voice_flag = []

        if teacher.cached_voice_path:
            if Path(teacher.cached_voice_path).exists():
                voice_flag = ["--cached-voice", teacher.cached_voice_path]
                logger.info(f"[Generation:{lecture_id}] Using cached voice: {teacher.cached_voice_path}")
            else:
                # File missing — clear stale DB value and fall back to voice_sample
                logger.warning(
                    f"[Generation:{lecture_id}] cached_voice_path set but file missing — "
                    f"falling back to voice_sample"
                )
                teacher.cached_voice_path = None
                session.add(teacher)
                session.commit()

        if not voice_flag and teacher.voice_sample:
            if Path(teacher.voice_sample).exists():
                voice_flag = ["--voice-ref", teacher.voice_sample]
                logger.info(f"[Generation:{lecture_id}] Using voice ref: {teacher.voice_sample}")
            else:
                logger.error(
                    f"[Generation:{lecture_id}] voice_sample set but file missing on disk: "
                    f"{teacher.voice_sample}"
                )
                _fail(session, lecture, f"Voice sample not found on disk: {teacher.voice_sample}")
                return

        if not voice_flag:
            logger.info(f"[Generation:{lecture_id}] No voice file — pipeline will use built-in default voice")

        # ── Create isolated output directory ───────────────────────
        # Each lecture gets its own folder so avatar_NNN.mp4 filenames
        # don't collide across lectures (LongCat auto-increments the number)
        output_dir = Path(settings.OUTPUTS_DIR) / "jobs" / str(lecture_id)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"[Generation:{lecture_id}] Failed to create output dir: {e}")
            _fail(session, lecture, f"Could not create output directory: {e}")
            return

        # ── Resolve backend ────────────────────────────────────────
        # Lecture-level override takes priority over global config default
        backend = lecture.avatar_backend or settings.AVATAR_BACKEND or "local"
        logger.info(f"[Generation:{lecture_id}] Using backend: {backend}")

        # ── Build subprocess command ───────────────────────────────
        cmd = [
            settings.LONGCAT_ENV_PYTHON,            # longcat-video conda env python
            settings.PIPELINE_SCRIPT,               # hololearn_pipeline.py orchestrator
            "--preprocessed-image", teacher.preprocessed_image_path,
            "--script",             lecture.script_path,
            "--output-dir",         str(output_dir),
            "--num-steps",          str(lecture.num_steps),
            "--audio-cfg",          str(lecture.audio_cfg),
            "--text-cfg",           str(lecture.text_cfg),
            "--seed",               str(lecture.seed),
            "--preset",             lecture.preset,
            "--backend",            backend,
        ]

        # Append voice flags (may be empty if using pipeline default)
        cmd += voice_flag

        # fal.ai backend needs key + resolution
        if backend == "fal":
            if settings.FAL_KEY:
                cmd += ["--fal-key", settings.FAL_KEY]
            cmd += ["--resolution", "480p"]   # 720p costs 2× more — use 480p by default

        logger.info(f"[Generation:{lecture_id}] Command: {' '.join(cmd)}")

        # ── Mark as GENERATING before the blocking call ────────────
        # This makes the status visible to frontend polling immediately.
        # Must commit BEFORE subprocess.run() since that blocks for 5–25 min.
        lecture.status    = LectureStatus.GENERATING
        lecture.started_at = datetime.utcnow()
        session.add(lecture)
        session.commit()

        # ── Run the pipeline ───────────────────────────────────────
        # This call BLOCKS until hololearn_pipeline.py finishes.
        # Stages run sequentially inside the pipeline:
        #   Stage 1: TTS  (~2–5 min, ~6 GB VRAM)  → lecture_audio.wav
        #   Stage 2: Avatar (~5–25 min, ~16–24 GB VRAM) → avatar_NNN.mp4
        logger.info(f"[Generation:{lecture_id}] Pipeline started — this will take 5–25 min")

        try:
            result = subprocess.run(
                cmd,
                cwd=settings.HOLOLEARN_DIR,
                capture_output=True,
                text=True,
                timeout=3600,   # 1 hour hard limit — kills hung jobs
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[Generation:{lecture_id}] Pipeline timed out after 1 hour")
            _fail(session, lecture, "Pipeline timed out after 1 hour")
            return
        except Exception as e:
            logger.error(f"[Generation:{lecture_id}] Subprocess launch failed: {e}")
            _fail(session, lecture, f"Failed to launch pipeline subprocess: {e}")
            return

        # ── Check exit code ────────────────────────────────────────
        if result.returncode != 0:
            error_tail = result.stderr[-2000:] if result.stderr else "No stderr output"
            logger.error(
                f"[Generation:{lecture_id}] Pipeline failed "
                f"(exit {result.returncode}):\n{error_tail}"
            )
            _fail(session, lecture, error_tail)
            return

        # ── Find the output MP4 ────────────────────────────────────
        # LongCat names outputs avatar_001.mp4, avatar_002.mp4, etc.
        # We sort and take the last one — handles re-runs in the same dir.
        mp4_files = sorted(output_dir.glob("avatar_*.mp4"))

        if not mp4_files:
            # Pipeline exited 0 but produced nothing — disk full edge case
            logger.error(
                f"[Generation:{lecture_id}] Pipeline exited 0 but no avatar_*.mp4 found "
                f"in {output_dir}"
            )
            _fail(session, lecture, "Pipeline exited successfully but no avatar_*.mp4 was found (disk full?)")
            return

        # ── Mark as COMPLETED ──────────────────────────────────────
        output_path = str(mp4_files[-1].resolve())
        lecture.status           = LectureStatus.COMPLETED
        lecture.output_video_path = output_path
        lecture.completed_at     = datetime.utcnow()
        session.add(lecture)
        session.commit()

        logger.info(f"[Generation:{lecture_id}] ✓ Completed → {output_path}")


def _fail(session: Session, lecture: Lecture, message: str) -> None:
    """
    Helper — mark lecture as FAILED with an error message and commit.
    Keeps the main function clean by centralizing failure logic.
    """
    lecture.status       = LectureStatus.FAILED
    lecture.error_message = message
    lecture.completed_at  = datetime.utcnow()
    session.add(lecture)
    session.commit()
    logger.error(f"[Generation:{lecture.lecture_id}] FAILED: {message}")