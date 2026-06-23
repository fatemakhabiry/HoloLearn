# # app/workers/tts_worker.py
# import logging
# from datetime import datetime
# from pathlib import Path
# from sqlmodel import Session

# from app.core.database import engine
# from app.core.config import settings
# from app.models.lecture import Lecture, LectureStatus
# from app.models.lecture_pipeline import LecturePipeline, PipelineStatus
# from app.models.teacher import Teacher

# from app.services.tts_service import generate_lecture_audio

# logger = logging.getLogger(__name__)


# async def run_tts(ctx: dict, lecture_id: int) -> None:
#     """
#     ARQ background job — Job 1 of the generation chain.

#     Runs locally (laptop) — calls educational_tts_pipeline.py via tts_service
#     to produce the lecture's audio + timestamped transcript from its script.

#     On success:
#         - LecturePipeline.transcript_path is set immediately, so the student
#           transcript view becomes available as soon as this job finishes —
#           independent of whether avatar generation (run_generation) has
#           completed yet.
#         - Enqueues run_generation with the audio path, which sends it to the
#           GPU machine for LongCAT avatar generation.

#     On failure:
#         - Marks both LecturePipeline and Lecture as FAILED, same convention
#           as generation_worker.py's _fail(). run_generation is never enqueued.
#     """
#     with Session(engine) as session:

#         # ── Fetch records ──────────────────────────────────────────
#         lecture = session.get(Lecture, lecture_id)
#         if not lecture:
#             logger.error(f"[TTS:{lecture_id}] Lecture not found in DB")
#             return

#         pipeline = session.get(LecturePipeline, lecture_id)
#         if not pipeline:
#             logger.error(f"[TTS:{lecture_id}] LecturePipeline record not found in DB")
#             lecture.status = LectureStatus.FAILED
#             session.add(lecture)
#             session.commit()
#             return

#         teacher = session.get(Teacher, lecture.teacher_id)
#         if not teacher:
#             logger.error(f"[TTS:{lecture_id}] Teacher {lecture.teacher_id} not found in DB")
#             _fail(session, lecture, pipeline, "Teacher record not found")
#             return

#         # ── Guard: script must be set and exist on disk ────────────
#         if not pipeline.script_path:
#             logger.error(f"[TTS:{lecture_id}] script_path is not set on LecturePipeline")
#             _fail(session, lecture, pipeline, "script_path is not set. Upstream module must set it before triggering.")
#             return

#         if not Path(pipeline.script_path).exists():
#             logger.error(f"[TTS:{lecture_id}] script_path not found on disk: {pipeline.script_path}")
#             _fail(session, lecture, pipeline, f"Script file not found on disk: {pipeline.script_path}")
#             return

#         # ── Mark as GENERATING ──────────────────────────────────────
#         pipeline.status     = PipelineStatus.GENERATING
#         pipeline.started_at = datetime.utcnow()
#         lecture.status       = LectureStatus.GENERATING
#         session.add(pipeline)
#         session.add(lecture)
#         session.commit()

#         logger.info(f"[TTS:{lecture_id}] Starting local TTS generation")

#         # ── Run TTS (audio + transcript) ────────────────────────────
#         try:
#             tts_result = await generate_lecture_audio(
#                 lecture_id=lecture_id,
#                 script_path=pipeline.script_path,
#                 teacher_id=teacher.user_id,
#                 voice_ref=teacher.voice_sample,
#                 cached_voice_path=teacher.cached_voice_path,
#             )
#         except Exception as e:
#             logger.error(f"[TTS:{lecture_id}] TTS generation failed: {e}")
#             _fail(session, lecture, pipeline, f"TTS generation failed: {e}")
#             return

#         audio_path      = tts_result["audio_path"]
#         transcript_path = tts_result["transcript_path"]

#         # ── Save transcript_path immediately ────────────────────────
#         # This is the moment the student transcript view becomes available —
#         # commits separately from anything avatar-related, since avatar
#         # generation (run_generation) hasn't started yet.
#         pipeline.transcript_path = transcript_path
#         session.add(pipeline)
#         session.commit()

#         if transcript_path:
#             logger.info(f"[TTS:{lecture_id}] ✓ Transcript ready → {transcript_path}")
#         else:
#             logger.warning(f"[TTS:{lecture_id}] Audio succeeded but transcript was not produced")

#         # ── Enqueue run_generation (Job 2 — GPU machine) ────────────
#         redis = ctx["redis"]
#         await redis.enqueue_job("run_generation", lecture_id, audio_path)

#         logger.info(f"[TTS:{lecture_id}] ✓ TTS complete → enqueued run_generation with audio={audio_path}")
#         # tts_worker.py — at the end of run_tts, replace the unconditional enqueue:

#         if settings.GPU_PIPELINE_ENABLED:
#             redis = ctx["redis"]
#             await redis.enqueue_job("run_generation", lecture_id, audio_path)
#             logger.info(f"[TTS:{lecture_id}] ✓ TTS complete → enqueued run_generation with audio={audio_path}")
#         else:
#             logger.info(
#                 f"[TTS:{lecture_id}] ✓ TTS complete — GPU_PIPELINE_ENABLED=False, "
#                 f"skipping run_generation. Audio at {audio_path}, transcript at {transcript_path}"
#             )
#             # Mark pipeline as done-for-now so it doesn't sit in GENERATING forever
#             pipeline.status = PipelineStatus.COMPLETED
#             pipeline.completed_at = datetime.utcnow()
#             lecture.status = LectureStatus.COMPLETED  # or a distinct status if you want to track "audio-only"
#             session.add(pipeline)
#             session.add(lecture)
#             session.commit()

# def _fail(
#     session: Session,
#     lecture: Lecture,
#     pipeline: LecturePipeline,
#     message: str,
# ) -> None:
#     """
#     Mark both LecturePipeline and Lecture as FAILED and commit.
#     Same convention as generation_worker.py's _fail() — kept identical so
#     failures from either stage of the chain look the same to the frontend.
#     """
#     pipeline.status        = PipelineStatus.FAILED
#     pipeline.error_message  = message
#     pipeline.completed_at  = datetime.utcnow()

#     lecture.status          = LectureStatus.FAILED

#     session.add(pipeline)
#     session.add(lecture)
#     session.commit()

#     logger.error(f"[TTS:{lecture.lecture_id}] FAILED: {message}")

# app/workers/tts_worker.py
import logging
from datetime import datetime
from pathlib import Path
from sqlmodel import Session

from app.core.database import engine

from app.models.lecture import Lecture, LectureStatus
from app.models.lecture_pipeline import LecturePipeline, PipelineStatus
from app.models.teacher import Teacher

from app.services.tts_service import generate_lecture_audio

logger = logging.getLogger(__name__)


async def run_tts(ctx: dict, lecture_id: int) -> None:
    """
    ARQ background job — Job 1 of the generation chain.

    Runs locally (laptop) — calls educational_tts_pipeline.py via tts_service
    to produce the lecture's audio + timestamped transcript from its script.

    On success:
        - LecturePipeline.transcript_path is set immediately, so the student
          transcript view becomes available as soon as this job finishes —
          independent of whether avatar generation (run_generation) has
          completed yet.
        - Enqueues run_generation with the audio path, which sends it to the
          GPU machine for LongCAT avatar generation.

    On failure:
        - Marks both LecturePipeline and Lecture as FAILED, same convention
          as generation_worker.py's _fail(). run_generation is never enqueued.
    """
    with Session(engine) as session:

        # ── Fetch records ──────────────────────────────────────────
        lecture = session.get(Lecture, lecture_id)
        if not lecture:
            logger.error(f"[TTS:{lecture_id}] Lecture not found in DB")
            return

        pipeline = session.get(LecturePipeline, lecture_id)
        if not pipeline:
            logger.error(f"[TTS:{lecture_id}] LecturePipeline record not found in DB")
            lecture.status = LectureStatus.FAILED
            session.add(lecture)
            session.commit()
            return

        teacher = session.get(Teacher, lecture.teacher_id)
        if not teacher:
            logger.error(f"[TTS:{lecture_id}] Teacher {lecture.teacher_id} not found in DB")
            _fail(session, lecture, pipeline, "Teacher record not found")
            return

        # ── Guard: script must be set and exist on disk ────────────
        if not pipeline.script_path:
            logger.error(f"[TTS:{lecture_id}] script_path is not set on LecturePipeline")
            _fail(session, lecture, pipeline, "script_path is not set. Upstream module must set it before triggering.")
            return

        if not Path(pipeline.script_path).exists():
            logger.error(f"[TTS:{lecture_id}] script_path not found on disk: {pipeline.script_path}")
            _fail(session, lecture, pipeline, f"Script file not found on disk: {pipeline.script_path}")
            return

        # ── Mark as GENERATING ──────────────────────────────────────
        pipeline.status     = PipelineStatus.GENERATING
        pipeline.started_at = datetime.utcnow()
        lecture.status       = LectureStatus.GENERATING
        session.add(pipeline)
        session.add(lecture)
        session.commit()

        # ── Reuse existing audio+transcript if this is a retry ──────
        # If a previous run_tts attempt already produced these files and
        # we're only here again because run_generation failed downstream
        # (e.g. GPU unreachable) and someone re-triggered start-pipeline,
        # there's no need to re-run Chatterbox synthesis — just reuse what
        # is already on disk and re-enqueue run_generation with it.
        if (
            pipeline.audio_path
            and Path(pipeline.audio_path).exists()
            and pipeline.transcript_path
            and Path(pipeline.transcript_path).exists()
        ):
            logger.info(f"[TTS:{lecture_id}] Found existing audio+transcript on disk — skipping re-synthesis")
            audio_path      = pipeline.audio_path
            transcript_path = pipeline.transcript_path
        else:
            logger.info(f"[TTS:{lecture_id}] Starting local TTS generation")

            # ── Run TTS (audio + transcript) ────────────────────────
            try:
                tts_result = await generate_lecture_audio(
                    lecture_id=lecture_id,
                    script_path=pipeline.script_path,
                    teacher_id=teacher.user_id,
                    voice_ref=teacher.voice_sample,
                    cached_voice_path=teacher.cached_voice_path,
                )
            except Exception as e:
                logger.error(f"[TTS:{lecture_id}] TTS generation failed: {e}")
                _fail(session, lecture, pipeline, f"TTS generation failed: {e}")
                return

            audio_path      = tts_result["audio_path"]
            transcript_path = tts_result["transcript_path"]

        # ── Save audio_path + transcript_path immediately ───────────
        # Persisting audio_path here (not just passing it as a job arg to
        # run_generation) is what makes retry possible — if run_generation
        # fails for any reason, the audio is still findable in the DB and
        # run_generation can simply be re-enqueued with it, with zero
        # re-synthesis. transcript_path being set here is also the moment
        # the student transcript view becomes available — independent of
        # whether avatar generation has completed yet.
        pipeline.audio_path      = audio_path
        pipeline.transcript_path = transcript_path
        session.add(pipeline)
        session.commit()

        if transcript_path:
            logger.info(f"[TTS:{lecture_id}] ✓ Transcript ready → {transcript_path}")
        else:
            logger.warning(f"[TTS:{lecture_id}] Audio succeeded but transcript was not produced")

        # ── Enqueue run_generation (Job 2 — GPU machine) ────────────
        redis = ctx["redis"]
        await redis.enqueue_job("run_generation", lecture_id, audio_path)

        logger.info(f"[TTS:{lecture_id}] ✓ TTS complete → enqueued run_generation with audio={audio_path}")


def _fail(
    session: Session,
    lecture: Lecture,
    pipeline: LecturePipeline,
    message: str,
) -> None:
    """
    Mark both LecturePipeline and Lecture as FAILED and commit.
    Same convention as generation_worker.py's _fail() — kept identical so
    failures from either stage of the chain look the same to the frontend.
    """
    pipeline.status        = PipelineStatus.FAILED
    pipeline.error_message  = message
    pipeline.completed_at  = datetime.utcnow()

    lecture.status          = LectureStatus.FAILED

    session.add(pipeline)
    session.add(lecture)
    session.commit()

    logger.error(f"[TTS:{lecture.lecture_id}] FAILED: {message}")