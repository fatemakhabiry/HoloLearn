# # # app/services/tts_service.py

# # import uuid
# # import logging
# # import asyncio
# # from pathlib import Path

# # from app.core.config import settings

# # logger = logging.getLogger(__name__)


# # async def generate_audio(
# #     text       : str,
# #     student_id : int,
# #     lecture_id : int,
# # ) -> str:
# #     """
# #     Convert answer text to audio using the existing TTS pipeline.

# #     Returns the absolute path to the generated audio file —
# #     stored in QAMessage.audio_output_path and sent to mobile as audio_url.

# #     Args:
# #         text:       the answer text from RAG
# #         student_id: for folder scoping
# #         lecture_id: for folder scoping
# #     """
# #     # Build output directory
# #     # data/tts_audio/student_{id}/lecture_{id}/
# #     audio_dir = (
# #         Path(settings.TTS_AUDIO_DIR)
# #         / f"student_{student_id}"
# #         / f"lecture_{lecture_id}"
# #     )
# #     audio_dir.mkdir(parents=True, exist_ok=True)

# #     output_path = audio_dir / f"{uuid.uuid4().hex}.wav"

# #     logger.info(f"[TTSService] Generating audio for student={student_id} lecture={lecture_id}")

# #     try:
# #         # Run TTS in thread pool — it's a blocking CPU operation
# #         await asyncio.get_event_loop().run_in_executor(
# #             None,
# #             _run_tts,
# #             text,
# #             str(output_path),
# #         )
# #     except Exception as e:
# #         logger.error(f"[TTSService] TTS generation failed: {e}")
# #         raise

# #     abs_path = str(output_path.resolve())
# #     logger.info(f"[TTSService] Audio saved → {abs_path}")

# #     return abs_path


# # def _run_tts(text: str, output_path: str) -> None:
# #     """
# #     Blocking TTS call — runs in thread pool via run_in_executor.
# #     Plug in your existing Chatterbox TTS pipeline here.
# #     """
# #     # ── Plug your existing TTS here ───────────────────────────────
# #     # Example with Chatterbox:
# #     #
# #     # from chatterbox.tts import ChatterboxTTS
# #     # model = ChatterboxTTS.from_pretrained(device="cuda")
# #     # wav = model.generate(text)
# #     # torchaudio.save(output_path, wav, model.sr)
# #     #
# #     # Replace the above with however your pipeline currently works.
# #     # The only requirement: save the audio to output_path.
# #     # ─────────────────────────────────────────────────────────────
# #     raise NotImplementedError(
# #         "Plug your existing TTS pipeline into _run_tts(). "
# #         "Save the output audio to output_path."
# #     )


# # app/services/tts_service.py

# import uuid
# import logging
# import asyncio
# import subprocess
# import tempfile
# from pathlib import Path
# from typing import Optional

# from app.core.config import settings

# logger = logging.getLogger(__name__)


# async def generate_audio(
#     text       : str,
#     student_id : int,
#     lecture_id : int,
#     teacher_id : int,
#     voice_ref  : Optional[str] = None,
# ) -> str:
#     """
#     Generate audio for a Q&A answer using the teacher's cloned voice.
#     Runs Chatterbox in its own subprocess (separate venv).

#     Args:
#         text:       answer text from RAG
#         student_id: for folder scoping
#         lecture_id: for folder scoping
#         teacher_id: used as voice cache name (one cached voice per teacher)
#         voice_ref:  teacher's reference voice file path (Teacher.voice_sample)

#     Returns absolute path to the generated .wav file.
#     """

#     # ── Guard: TTS env configured ──────────────────────────────
#     if not settings.TTS_ENV_PYTHON or not settings.TTS_SCRIPT:
#         raise RuntimeError(
#             "TTS not configured. Set TTS_ENV_PYTHON and TTS_SCRIPT in .env."
#         )

#     if not Path(settings.TTS_ENV_PYTHON).exists():
#         raise RuntimeError(f"TTS Python not found: {settings.TTS_ENV_PYTHON}")

#     if not Path(settings.TTS_SCRIPT).exists():
#         raise RuntimeError(f"TTS script not found: {settings.TTS_SCRIPT}")

#     # ── Build output directory ─────────────────────────────────
#     audio_dir = (
#         Path(settings.TTS_AUDIO_DIR).resolve()  # ← .resolve()
#         / f"student_{student_id}"
#         / f"lecture_{lecture_id}"
#     )
#     audio_dir.mkdir(parents=True, exist_ok=True)
#     output_path = audio_dir / f"{uuid.uuid4().hex}.wav"

#     # ── Write text to temp file ────────────────────────────────
#     text_dir = Path(settings.TTS_AUDIO_DIR).resolve() / "_temp_text"  # ← .resolve()
#     text_dir.mkdir(parents=True, exist_ok=True)
#     text_file = text_dir / f"{uuid.uuid4().hex}.txt"
#     text_file.write_text(text, encoding="utf-8")

#     logger.info(
#         f"[TTSService] Generating audio — "
#         f"teacher={teacher_id} student={student_id} lecture={lecture_id}"
#     )

#     # ── Run Chatterbox subprocess ──────────────────────────────
#     try:
#         await asyncio.get_event_loop().run_in_executor(
#             None,
#             _run_subprocess,
#             str(text_file),
#             str(output_path),
#             teacher_id,
#             voice_ref,
#         )
#     finally:
#         # Clean up temp text file
#         try:
#             text_file.unlink()
#         except OSError:
#             pass

#     if not output_path.exists():
#         raise RuntimeError(
#             f"TTS subprocess exited but no output file found at {output_path}"
#         )

#     abs_path = str(output_path.resolve())
#     logger.info(f"[TTSService] ✓ Audio saved → {abs_path}")
#     return abs_path


# def _run_subprocess(
#     text_file_path  : str,
#     output_path     : str,
#     teacher_id      : int,
#     voice_ref       : Optional[str],
# ) -> None:
#     """Blocking subprocess call to Chatterbox env."""
#     voice_name = f"teacher_{teacher_id}"

#     # Build command
#     cmd = [
#         settings.TTS_ENV_PYTHON,
#         settings.TTS_SCRIPT,
#         "--text",       text_file_path,
#         "--output",     output_path,
#         "--voice-name", voice_name,
#         "--preset",     settings.TTS_PRESET,
#     ]

#     # Add voice reference if provided
#     if voice_ref and Path(voice_ref).exists():
#         cmd += ["--reference", voice_ref]
#     else:
#         logger.warning(
#             f"[TTSService] No voice_ref for teacher {teacher_id} — "
#             "Chatterbox will use cached voice or default conditioning"
#         )

#     logger.info(f"[TTSService] Subprocess cmd: {' '.join(cmd)}")
#     logger.info(f"[TTSService] Subprocess cmd: {' '.join(cmd)}")

#     # ── ADD THESE DEBUG LINES ──────────────────────────────────
#     logger.info(f"[TTSService] text_file_path: {text_file_path}")
#     logger.info(f"[TTSService] text_file exists: {Path(text_file_path).exists()}")
#     logger.info(f"[TTSService] output_path: {output_path}")
#     logger.info(f"[TTSService] cwd: {str(Path(settings.TTS_SCRIPT).parent)}")
#     # ───────────────────────────────────────────────────────────
#     # Run subprocess
#     try:
#         result = subprocess.run(
#             cmd,
#             cwd            = str(Path(settings.TTS_SCRIPT).parent),
#             capture_output = True,
#             text           = True,
#             timeout        = 300,   # 5 min hard cap — Q&A answers are short
#         )
#     except subprocess.TimeoutExpired:
#         raise RuntimeError("TTS subprocess timed out after 5 minutes")
#     except Exception as e:
#         raise RuntimeError(f"TTS subprocess failed to launch: {e}")

#     # Check exit code
#     if result.returncode != 0:
#         error_tail = result.stderr[-1000:] if result.stderr else "No stderr"
#         logger.error(f"[TTSService] subprocess failed:\n{error_tail}")
#         raise RuntimeError(f"TTS subprocess exited {result.returncode}: {error_tail[:300]}")

# app/services/tts_service.py

import uuid
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Q&A ANSWER AUDIO — existing, unchanged.
# Short answer text → single .wav. No transcript needed (the answer
# text is already stored as QAMessage.content_text).
# ════════════════════════════════════════════════════════════════════

async def generate_audio(
    text       : str,
    student_id : int,
    lecture_id : int,
    teacher_id : int,
    voice_ref  : Optional[str] = None,
) -> str:
    """
    Generate audio for a Q&A answer using the teacher's cloned voice.
    Runs Chatterbox in its own subprocess (separate venv).

    Args:
        text:       answer text from RAG
        student_id: for folder scoping
        lecture_id: for folder scoping
        teacher_id: used as voice cache name (one cached voice per teacher)
        voice_ref:  teacher's reference voice file path (Teacher.voice_sample)

    Returns absolute path to the generated .wav file.
    """

    # ── Guard: TTS env configured ──────────────────────────────
    if not settings.TTS_ENV_PYTHON or not settings.TTS_SCRIPT:
        raise RuntimeError(
            "TTS not configured. Set TTS_ENV_PYTHON and TTS_SCRIPT in .env."
        )

    if not Path(settings.TTS_ENV_PYTHON).exists():
        raise RuntimeError(f"TTS Python not found: {settings.TTS_ENV_PYTHON}")

    if not Path(settings.TTS_SCRIPT).exists():
        raise RuntimeError(f"TTS script not found: {settings.TTS_SCRIPT}")

    # ── Build output directory ─────────────────────────────────
    audio_dir = (
        Path(settings.TTS_AUDIO_DIR).resolve()
        / f"student_{student_id}"
        / f"lecture_{lecture_id}"
    )
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{uuid.uuid4().hex}.wav"

    # ── Write text to temp file ────────────────────────────────
    text_dir = Path(settings.TTS_AUDIO_DIR).resolve() / "_temp_text"
    text_dir.mkdir(parents=True, exist_ok=True)
    text_file = text_dir / f"{uuid.uuid4().hex}.txt"
    text_file.write_text(text, encoding="utf-8")

    logger.info(
        f"[TTSService] Generating Q&A audio — "
        f"teacher={teacher_id} student={student_id} lecture={lecture_id}"
    )

    # ── Run Chatterbox subprocess ──────────────────────────────
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            _run_subprocess,
            str(text_file),
            str(output_path),
            None,            # transcript_output_path — not needed for Q&A answers
            teacher_id,
            voice_ref,
            None,            # cached_voice_path — Q&A path uses --reference/--voice-name only
        )
    finally:
        # Clean up temp text file
        try:
            text_file.unlink()
        except OSError:
            pass

    if not output_path.exists():
        raise RuntimeError(
            f"TTS subprocess exited but no output file found at {output_path}"
        )

    abs_path = str(output_path.resolve())
    logger.info(f"[TTSService] ✓ Q&A audio saved → {abs_path}")
    return abs_path


# ════════════════════════════════════════════════════════════════════
# FULL-LECTURE AUDIO + TRANSCRIPT — new.
# Runs locally on this machine (laptop). Produces both the audio file
# (later sent to the GPU machine for LongCAT avatar generation) and a
# [MM:SS]-timestamped transcript .txt (served to students once the
# lecture is ongoing). Called by the run_tts ARQ job.
# ════════════════════════════════════════════════════════════════════

async def generate_lecture_audio(
    lecture_id        : int,
    script_path       : str,
    teacher_id        : int,
    voice_ref         : Optional[str] = None,
    cached_voice_path : Optional[str] = None,
) -> dict:
    """
    Generate full-lecture audio + timestamped transcript from a script file.

    Args:
        lecture_id:        for output folder scoping (matches generation_worker.py's
                            OUTPUTS_DIR / "jobs" / {lecture_id} convention)
        script_path:       path to LectureVersion.txt_path (the full lecture script)
        teacher_id:        used as voice cache name
        voice_ref:         Teacher.voice_sample — used if no cached_voice_path
        cached_voice_path: Teacher.cached_voice_path — pre-baked .pt, skips voice cloning

    Returns:
        {"audio_path": str, "transcript_path": Optional[str]}

        transcript_path is None only if the transcript failed to write —
        audio_path is still returned in that case since the audio itself
        succeeded (transcript failure is non-fatal, see educational_tts_pipeline.py).

    Raises:
        RuntimeError if TTS is not configured, the script is missing, or the
        subprocess fails / produces no audio output.
    """

    # ── Guard: TTS env configured ──────────────────────────────
    if not settings.TTS_ENV_PYTHON or not settings.TTS_SCRIPT:
        raise RuntimeError(
            "TTS not configured. Set TTS_ENV_PYTHON and TTS_SCRIPT in .env."
        )

    if not Path(settings.TTS_ENV_PYTHON).exists():
        raise RuntimeError(f"TTS Python not found: {settings.TTS_ENV_PYTHON}")

    if not Path(settings.TTS_SCRIPT).exists():
        raise RuntimeError(f"TTS script not found: {settings.TTS_SCRIPT}")

    if not Path(script_path).exists():
        raise RuntimeError(f"Lecture script not found: {script_path}")

    # ── Build output directory ─────────────────────────────────
    # Shared with generation_worker.py's video output dir — everything
    # for one lecture's generation job lives under one folder.
    output_dir = Path(settings.OUTPUTS_DIR).resolve() / "jobs" / str(lecture_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path      = output_dir / "audio.wav"
    transcript_path = output_dir / "transcript.txt"

    logger.info(
        f"[TTSService] Generating lecture audio — "
        f"lecture={lecture_id} teacher={teacher_id} script={script_path}"
    )

    # ── Run Chatterbox subprocess ──────────────────────────────
    await asyncio.get_event_loop().run_in_executor(
        None,
        _run_subprocess,
        script_path,
        str(audio_path),
        str(transcript_path),
        teacher_id,
        voice_ref,
        cached_voice_path,
    )

    if not audio_path.exists():
        raise RuntimeError(
            f"TTS subprocess exited but no audio file found at {audio_path}"
        )

    result = {
        "audio_path": str(audio_path.resolve()),
        "transcript_path": str(transcript_path.resolve()) if transcript_path.exists() else None,
    }

    if result["transcript_path"] is None:
        logger.warning(
            f"[TTSService] Lecture {lecture_id}: audio succeeded but transcript.txt "
            "was not produced — student transcript view will be unavailable for this lecture"
        )

    logger.info(f"[TTSService] ✓ Lecture audio saved → {result['audio_path']}")
    return result


# ════════════════════════════════════════════════════════════════════
# Shared subprocess runner — used by both paths above.
# ════════════════════════════════════════════════════════════════════

def _run_subprocess(
    text_file_path         : str,
    output_path             : str,
    transcript_output_path  : Optional[str],
    teacher_id               : int,
    voice_ref                : Optional[str],
    cached_voice_path        : Optional[str],
) -> None:
    """
    Blocking subprocess call to educational_tts_pipeline.py (Chatterbox env).

    transcript_output_path is None for Q&A answers (no transcript needed),
    set for full-lecture generation (run_tts job).

    cached_voice_path takes priority over voice_ref (matches generation_worker.py's
    voice priority chain — cached_voice_path is the speedup path, voice_ref is
    the cold-start path that creates the cache).
    """
    voice_name = f"teacher_{teacher_id}"

    cmd = [
        settings.TTS_ENV_PYTHON,
        settings.TTS_SCRIPT,
        "--text",       text_file_path,
        "--output",     output_path,
        "--voice-name", voice_name,
        "--preset",     settings.TTS_PRESET,
    ]

    if transcript_output_path:
        cmd += ["--transcript-output", transcript_output_path]

    # Voice priority: cached .pt > reference wav > default conditioning
    if cached_voice_path and Path(cached_voice_path).exists():
        cmd += ["--cached-voice", cached_voice_path]
    elif voice_ref and Path(voice_ref).exists():
        cmd += ["--reference", voice_ref]
    else:
        logger.warning(
            f"[TTSService] No cached_voice_path or voice_ref for teacher {teacher_id} — "
            "Chatterbox will use default conditioning"
        )

    logger.info(f"[TTSService] Subprocess cmd: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd            = str(Path(settings.TTS_SCRIPT).parent),
            capture_output = True,
            text           = True,
            timeout        = 1800,   # 30 min cap — full lectures take longer than Q&A answers
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("TTS subprocess timed out after 30 minutes")
    except Exception as e:
        raise RuntimeError(f"TTS subprocess failed to launch: {e}")

    if result.returncode != 0:
        error_tail = result.stderr[-1000:] if result.stderr else "No stderr"
        logger.error(f"[TTSService] subprocess failed:\n{error_tail}")
        raise RuntimeError(f"TTS subprocess exited {result.returncode}: {error_tail[:300]}")