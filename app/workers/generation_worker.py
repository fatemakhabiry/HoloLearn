# app/workers/generation_worker.py
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine

from app.models.user import User
from app.models.teacher import Teacher
from app.models.lecture import Lecture, LectureStatus
from app.models.lecture_pipeline import LecturePipeline, PipelineStatus
from app.models.course import Course
from app.models.schedule import Schedule
from app.models.resource import Resource
from app.models.enrollment import Enrollment

logger = logging.getLogger(__name__)


async def run_generation(ctx: dict, lecture_id: int) -> None:
    """
    ARQ background job — runs hololearn_pipeline.py for a single lecture.

    Reads all pipeline params from LecturePipeline.
    Updates both LecturePipeline.status and Lecture.status together
    so both models stay in sync.
    """
    with Session(engine) as session:

        # ── Fetch records ──────────────────────────────────────────
        lecture = session.get(Lecture, lecture_id)
        if not lecture:
            logger.error(f"[Generation:{lecture_id}] Lecture not found in DB")
            return

        pipeline = session.get(LecturePipeline, lecture_id)
        if not pipeline:
            logger.error(f"[Generation:{lecture_id}] LecturePipeline record not found in DB")
            # Update lecture status so frontend sees the failure
            lecture.status = LectureStatus.FAILED
            session.add(lecture)
            session.commit()
            return

        teacher = session.get(Teacher, lecture.teacher_id)
        if not teacher:
            logger.error(f"[Generation:{lecture_id}] Teacher {lecture.teacher_id} not found in DB")
            _fail(session, lecture, pipeline, "Teacher record not found")
            return

        # ── Guard: pipeline must be configured ────────────────────
        if not settings.LONGCAT_ENV_PYTHON or not settings.PIPELINE_SCRIPT:
            logger.error(f"[Generation:{lecture_id}] Pipeline not configured in .env")
            _fail(session, lecture, pipeline, "Pipeline not configured. Set LONGCAT_ENV_PYTHON and PIPELINE_SCRIPT in .env")
            return

        # ── Guard: preprocessed image must exist on disk ───────────
        if not teacher.preprocessed_image_path:
            logger.error(f"[Generation:{lecture_id}] preprocessed_image_path is not set on teacher")
            _fail(session, lecture, pipeline, "preprocessed_image_path is not set. Teacher must re-upload photo.")
            return

        if not Path(teacher.preprocessed_image_path).exists():
            logger.error(f"[Generation:{lecture_id}] preprocessed_image_path not found on disk: {teacher.preprocessed_image_path}")
            _fail(session, lecture, pipeline, f"Preprocessed image not found on disk: {teacher.preprocessed_image_path}")
            return

        # ── Guard: script file must exist on disk ─────────────────
        # script_path now lives on LecturePipeline, not Lecture
        if not pipeline.script_path:
            logger.error(f"[Generation:{lecture_id}] script_path is not set on LecturePipeline")
            _fail(session, lecture, pipeline, "script_path is not set. Upstream module must set it before triggering.")
            return

        if not Path(pipeline.script_path).exists():
            logger.error(f"[Generation:{lecture_id}] script_path not found on disk: {pipeline.script_path}")
            _fail(session, lecture, pipeline, f"Script file not found on disk: {pipeline.script_path}")
            return

        # ── Resolve voice priority chain ───────────────────────────
        voice_flag = []

        if teacher.cached_voice_path:
            if Path(teacher.cached_voice_path).exists():
                voice_flag = ["--cached-voice", teacher.cached_voice_path]
                logger.info(f"[Generation:{lecture_id}] Using cached voice: {teacher.cached_voice_path}")
            else:
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
                _fail(session, lecture, pipeline, f"Voice sample not found on disk: {teacher.voice_sample}")
                return

        if not voice_flag:
            logger.info(f"[Generation:{lecture_id}] No voice file — pipeline will use built-in default voice")

        # ── Create isolated output directory ───────────────────────
        output_dir = Path(settings.OUTPUTS_DIR) / "jobs" / str(lecture_id)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"[Generation:{lecture_id}] Failed to create output dir: {e}")
            _fail(session, lecture, pipeline, f"Could not create output directory: {e}")
            return

        # ── Resolve backend ────────────────────────────────────────
        # Pipeline-level override → global config → default "local"
        backend = pipeline.avatar_backend or settings.AVATAR_BACKEND or "local"
        logger.info(f"[Generation:{lecture_id}] Using backend: {backend}")

        # ── Build subprocess command ───────────────────────────────
        # All generation params come from LecturePipeline now
        cmd = [
            settings.LONGCAT_ENV_PYTHON,
            settings.PIPELINE_SCRIPT,
            "--preprocessed-image", teacher.preprocessed_image_path,
            "--script",             pipeline.script_path,
            "--output-dir",         str(output_dir),
            "--num-steps",          str(pipeline.num_steps),
            "--audio-cfg",          str(pipeline.audio_cfg),
            "--text-cfg",           str(pipeline.text_cfg),
            "--seed",               str(pipeline.seed),
            "--preset",             pipeline.preset,
            "--backend",            backend,
        ]

        cmd += voice_flag

        if backend == "fal":
            if settings.FAL_KEY:
                cmd += ["--fal-key", settings.FAL_KEY]
            cmd += ["--resolution", "480p"]

        logger.info(f"[Generation:{lecture_id}] Command: {' '.join(cmd)}")

        # ── Mark as GENERATING before the blocking call ────────────
        # Update both models so frontend sees consistent state
        pipeline.status     = PipelineStatus.GENERATING
        pipeline.started_at = datetime.utcnow()
        lecture.status      = LectureStatus.GENERATING
        session.add(pipeline)
        session.add(lecture)
        session.commit()

        # ── Run the pipeline ───────────────────────────────────────
        logger.info(f"[Generation:{lecture_id}] Pipeline started — this will take 5–25 min")

        try:
            result = subprocess.run(
                cmd,
                cwd=settings.HOLOLEARN_DIR,
                capture_output=True,
                text=True,
                timeout=3600,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[Generation:{lecture_id}] Pipeline timed out after 1 hour")
            _fail(session, lecture, pipeline, "Pipeline timed out after 1 hour")
            return
        except Exception as e:
            logger.error(f"[Generation:{lecture_id}] Subprocess launch failed: {e}")
            _fail(session, lecture, pipeline, f"Failed to launch pipeline subprocess: {e}")
            return

        # ── Check exit code ────────────────────────────────────────
        if result.returncode != 0:
            error_tail = result.stderr[-2000:] if result.stderr else "No stderr output"
            logger.error(
                f"[Generation:{lecture_id}] Pipeline failed "
                f"(exit {result.returncode}):\n{error_tail}"
            )
            _fail(session, lecture, pipeline, error_tail)
            return

        # ── Find the output MP4 ────────────────────────────────────
        mp4_files = sorted(output_dir.glob("avatar_*.mp4"))

        if not mp4_files:
            logger.error(
                f"[Generation:{lecture_id}] Pipeline exited 0 but no avatar_*.mp4 found "
                f"in {output_dir}"
            )
            _fail(session, lecture, pipeline, "Pipeline exited successfully but no avatar_*.mp4 was found (disk full?)")
            return

        # ── Mark as COMPLETED ──────────────────────────────────────
        output_path = str(mp4_files[-1].resolve())

        pipeline.status           = PipelineStatus.COMPLETED
        pipeline.output_video_path = output_path
        pipeline.completed_at     = datetime.utcnow()

        lecture.status            = LectureStatus.COMPLETED

        session.add(pipeline)
        session.add(lecture)
        session.commit()

        logger.info(f"[Generation:{lecture_id}] ✓ Completed → {output_path}")


def _fail(
    session: Session,
    lecture: Lecture,
    pipeline: LecturePipeline,
    message: str
) -> None:
    """
    Mark both LecturePipeline and Lecture as FAILED and commit.
    Keeps both models in sync on any failure path.
    """
    pipeline.status        = PipelineStatus.FAILED
    pipeline.error_message = message
    pipeline.completed_at  = datetime.utcnow()

    lecture.status         = LectureStatus.FAILED

    session.add(pipeline)
    session.add(lecture)
    session.commit()

    logger.error(f"[Generation:{lecture.lecture_id}] FAILED: {message}")