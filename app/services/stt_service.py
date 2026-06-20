# app/services/stt_service.py

import logging
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


async def transcribe_voice(audio_path: str) -> str:
    """
    Transcribe a student's voice question using Groq Whisper.

    Backend now owns transcription — RAG never receives raw audio.
    This guarantees QAMessage.content_text always holds real,
    readable text (needed for the PDF export feature).

    Args:
        audio_path: absolute path to the saved voice file

    Returns:
        Transcribed text. Raises RuntimeError on failure.
    """
    if not settings.GROQ_API_KEY_WHISPER:
        raise RuntimeError("GROQ_API_KEY_WHISPER not set in .env")

    path = Path(audio_path)
    if not path.exists():
        raise RuntimeError(f"Voice file not found: {audio_path}")

    logger.info(f"[STTService] Transcribing → {path.name}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    GROQ_WHISPER_URL,
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY_WHISPER}"},
                    files={"file": (path.name, f, "application/octet-stream")},
                    data={
                        "model": "whisper-large-v3-turbo",
                        "response_format": "text",
                    },
                )
    except httpx.TimeoutException as e:
        raise RuntimeError("Whisper transcription timed out") from e
    except httpx.ConnectError as e:
        raise RuntimeError("Cannot reach Groq Whisper API") from e

    if response.status_code != 200:
        raise RuntimeError(
            f"Whisper transcription failed ({response.status_code}): {response.text[:300]}"
        )

    text = response.text.strip()

    if not text:
        raise RuntimeError("Whisper returned empty transcript")

    logger.info(f"[STTService] ✓ Transcribed {len(text)} chars")
    return text