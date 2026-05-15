# app/services/tts_service.py

import uuid
import logging
import asyncio
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_audio(
    text       : str,
    student_id : int,
    lecture_id : int,
) -> str:
    """
    Convert answer text to audio using the existing TTS pipeline.

    Returns the absolute path to the generated audio file —
    stored in QAMessage.audio_output_path and sent to mobile as audio_url.

    Args:
        text:       the answer text from RAG
        student_id: for folder scoping
        lecture_id: for folder scoping
    """
    # Build output directory
    # data/tts_audio/student_{id}/lecture_{id}/
    audio_dir = (
        Path(settings.TTS_AUDIO_DIR)
        / f"student_{student_id}"
        / f"lecture_{lecture_id}"
    )
    audio_dir.mkdir(parents=True, exist_ok=True)

    output_path = audio_dir / f"{uuid.uuid4().hex}.wav"

    logger.info(f"[TTSService] Generating audio for student={student_id} lecture={lecture_id}")

    try:
        # Run TTS in thread pool — it's a blocking CPU operation
        await asyncio.get_event_loop().run_in_executor(
            None,
            _run_tts,
            text,
            str(output_path),
        )
    except Exception as e:
        logger.error(f"[TTSService] TTS generation failed: {e}")
        raise

    abs_path = str(output_path.resolve())
    logger.info(f"[TTSService] Audio saved → {abs_path}")

    return abs_path


def _run_tts(text: str, output_path: str) -> None:
    """
    Blocking TTS call — runs in thread pool via run_in_executor.
    Plug in your existing Chatterbox TTS pipeline here.
    """
    # ── Plug your existing TTS here ───────────────────────────────
    # Example with Chatterbox:
    #
    # from chatterbox.tts import ChatterboxTTS
    # model = ChatterboxTTS.from_pretrained(device="cuda")
    # wav = model.generate(text)
    # torchaudio.save(output_path, wav, model.sr)
    #
    # Replace the above with however your pipeline currently works.
    # The only requirement: save the audio to output_path.
    # ─────────────────────────────────────────────────────────────
    raise NotImplementedError(
        "Plug your existing TTS pipeline into _run_tts(). "
        "Save the output audio to output_path."
    )