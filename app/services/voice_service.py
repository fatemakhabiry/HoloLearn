# app/services/voice_service.py

import uuid
import logging
from pathlib import Path
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_voice_file(
    file       : UploadFile,
    student_id : int,
    lecture_id : int,
) -> str:
    """
    Save a student's voice input file to disk.

    Returns the absolute path as a string —
    passed directly to RAG /query as the query field.

    Args:
        file:       uploaded audio file from Flutter
        student_id: for folder scoping
        lecture_id: for folder scoping
    """
    # Build student-scoped directory
    # data/voice_uploads/student_{id}/lecture_{id}/
    voice_dir = (
        Path(settings.VOICE_UPLOADS_DIR)
        / f"student_{student_id}"
        / f"lecture_{lecture_id}"
    )
    voice_dir.mkdir(parents=True, exist_ok=True)

    # Keep original extension — RAG needs it to detect audio
    suffix    = Path(file.filename).suffix.lower() if file.filename else ".wav"
    filename  = f"{uuid.uuid4().hex}{suffix}"
    file_path = voice_dir / filename

    # Save to disk
    contents = await file.read()
    file_path.write_bytes(contents)

    abs_path = str(file_path.resolve())
    logger.info(f"[VoiceService] Saved voice file → {abs_path}")

    return abs_path