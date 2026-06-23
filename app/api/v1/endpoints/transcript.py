# app/api/routes/transcript.py
#
# Mount this router in your main FastAPI app (or merge into your existing
# lecture router) — e.g.:
#     app.include_router(transcript_router)

import re
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.core.database import get_session   # adjust import if your dependency lives elsewhere
from app.models.lecture_pipeline import LecturePipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# Matches one line of the transcript .txt: "[MM:SS] text..."
_LINE_PATTERN = re.compile(r"^\[(\d{2}):(\d{2})\]\s?(.*)$")


def _parse_transcript(raw_text: str) -> list[dict]:
    """
    Parse the [MM:SS] text per-line transcript format written by
    educational_tts_pipeline.py into structured segments.

    Lines that don't match the expected format are skipped (logged, not
    raised) — a malformed line shouldn't take down the whole transcript.
    """
    segments = []
    for line_num, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        match = _LINE_PATTERN.match(line)
        if not match:
            logger.warning(f"[Transcript] Skipping malformed line {line_num}: {line[:80]!r}")
            continue

        minutes, seconds, text = match.groups()
        start_seconds = int(minutes) * 60 + int(seconds)

        segments.append({
            "start_seconds": start_seconds,
            "timestamp":     f"{minutes}:{seconds}",
            "text":          text,
        })

    return segments


@router.get("/{lecture_id}/transcript")
def get_lecture_transcript(
    lecture_id: int,
    session: Session = Depends(get_session),
) -> list[dict]:
    """
    Returns the lecture's timestamped transcript as a list of segments,
    sorted by start_seconds (the .txt file is already written in order,
    so this is naturally sorted — no explicit sort needed, but the field
    is included for client-side use, e.g. seeking).

    Called once by the student app when a lecture goes live/ongoing —
    not polled or re-fetched repeatedly.

    404 if no pipeline record exists for this lecture, or if TTS hasn't
    finished yet (transcript_path not set) — both are "not ready", just
    distinguished in the error detail for easier debugging.
    """
    pipeline = session.get(LecturePipeline, lecture_id)

    if not pipeline:
        raise HTTPException(status_code=404, detail="No generation pipeline found for this lecture")

    if not pipeline.transcript_path:
        raise HTTPException(status_code=404, detail="Transcript not ready yet")

    transcript_file = Path(pipeline.transcript_path)
    if not transcript_file.exists():
        logger.error(
            f"[Transcript] lecture={lecture_id} transcript_path set "
            f"but file missing on disk: {pipeline.transcript_path}"
        )
        raise HTTPException(status_code=404, detail="Transcript file missing on disk")

    raw_text = transcript_file.read_text(encoding="utf-8")
    segments = _parse_transcript(raw_text)

    return segments