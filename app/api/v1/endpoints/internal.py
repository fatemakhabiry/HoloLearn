# app/api/v1/endpoints/internal.py
"""
Internal endpoints — called by the AI server (friend's PC), NOT by the frontend.

Authentication: Bearer token matching INTERNAL_API_TOKEN in .env
                (NOT the usual JWT; this token never expires)

Endpoints
---------
GET  /internal/files
    AI server calls this to download a file (raw photo, voice sample, script …)
    by absolute path on the laptop's disk.

POST /internal/pipeline-done
    AI server calls this when it finishes generating the avatar video.
    Receives the MP4 as a multipart upload, saves it to OUTPUTS_DIR,
    then updates lecture_pipelines + lectures tables.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.lecture import Lecture, LectureStatus
from app.models.lecture_pipeline import LecturePipeline, PipelineStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Token guard ────────────────────────────────────────────────────────────────

def verify_internal_token(authorization: str = Header(...)) -> None:
    """
    Dependency that checks the Authorization header.

    Expected format:  Authorization: Bearer <INTERNAL_API_TOKEN>

    Raises 403 if:
    - INTERNAL_API_TOKEN is not set in .env (misconfiguration)
    - Token does not match
    """
    if not settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_API_TOKEN is not configured on this server.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal API token.",
        )


# ── GET /internal/files ────────────────────────────────────────────────────────

@router.get("/files")
def serve_file(
    path: str = Query(..., description="Absolute path on the laptop's disk"),
    _: None = Depends(verify_internal_token),
):
    """
    Serve any file on the laptop's disk to the AI server.

    The AI server uses this to download:
    - Teacher's preprocessed face image  (raw_preprocessed.png)
    - Teacher's voice reference sample   (voice_ref.wav)
    - Generated lecture script           (.txt)

    Query parameter
    ---------------
    path : absolute path on the laptop, e.g.
           D:/HoloLearn/uploads/instructors/7/raw_preprocessed.png

    Security
    --------
    Protected by INTERNAL_API_TOKEN.  Only the AI server knows this token.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file.",
        )

    logger.info(f"[InternalFiles] Serving file → {path}")
    return FileResponse(path=str(file_path), filename=file_path.name)


# ── POST /internal/pipeline-done ──────────────────────────────────────────────

class PipelineDoneError(BaseModel):
    lecture_id: int
    error_message: str


@router.post("/pipeline-done")
async def pipeline_done(
    lecture_id: int = Query(..., description="Lecture ID whose pipeline just finished"),
    mp4_file: UploadFile = File(None, description="Generated avatar MP4 (omit on failure)"),
    error_message: str = Query(None, description="Error details if the pipeline failed"),
    _: None = Depends(verify_internal_token),
    session: Session = Depends(get_session),
):
    """
    Called by the AI server when avatar generation finishes (success or failure).

    Success path
    ------------
    - AI server uploads the MP4 file as multipart `mp4_file`
    - Laptop saves it to OUTPUTS_DIR / lectures / <lecture_id> / avatar_<lecture_id>.mp4
    - Updates lecture_pipelines:
        status = COMPLETED
        output_video_path = saved path
        completed_at = now
    - Updates lectures:
        status = COMPLETED

    Failure path
    ------------
    - AI server sends ?error_message=<details> with no mp4_file
    - Updates lecture_pipelines:
        status = FAILED
        error_message = provided text
        completed_at = now
    - Updates lectures:
        status = FAILED

    Query parameters
    ----------------
    lecture_id    : int   — which lecture this result belongs to
    error_message : str   — (failure only) what went wrong

    Multipart body
    --------------
    mp4_file : UploadFile — (success only) the generated avatar video
    """

    # ── 1. Load the pipeline record ────────────────────────────────
    pipeline = session.get(LecturePipeline, lecture_id)
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lecture_pipelines row found for lecture_id={lecture_id}",
        )

    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lecture found for lecture_id={lecture_id}",
        )

    now = datetime.utcnow()

    # ── 2a. Failure path ───────────────────────────────────────────
    if error_message:
        logger.error(
            f"[PipelineDone] Lecture {lecture_id} FAILED — {error_message[:200]}"
        )
        pipeline.status        = PipelineStatus.FAILED
        pipeline.error_message = error_message[:2000]   # cap DB storage
        pipeline.completed_at  = now
        lecture.status         = LectureStatus.FAILED

        session.add(pipeline)
        session.add(lecture)
        session.commit()

        return {"lecture_id": lecture_id, "result": "failed", "detail": "Pipeline failure recorded."}

    # ── 2b. Success path ───────────────────────────────────────────
    if not mp4_file:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either mp4_file (success) or error_message (failure) must be provided.",
        )

    # Validate file type
    filename = mp4_file.filename or ""
    if not filename.lower().endswith(".mp4"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an .mp4 file.",
        )

    # Determine output directory
    outputs_dir = Path(settings.OUTPUTS_DIR) if settings.OUTPUTS_DIR else Path("outputs")
    lecture_out_dir = outputs_dir / "lectures" / str(lecture_id)
    lecture_out_dir.mkdir(parents=True, exist_ok=True)

    save_path = lecture_out_dir / f"avatar_{lecture_id}.mp4"

    # Save the uploaded MP4 to disk
    try:
        with save_path.open("wb") as f:
            shutil.copyfileobj(mp4_file.file, f)
    except Exception as exc:
        logger.error(f"[PipelineDone] Failed to save MP4 for lecture {lecture_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file: {exc}",
        )
    finally:
        await mp4_file.close()

    saved_path_str = str(save_path.resolve())
    logger.info(f"[PipelineDone] Lecture {lecture_id} — MP4 saved → {saved_path_str}")

    # Update pipeline record
    pipeline.status            = PipelineStatus.COMPLETED
    pipeline.output_video_path = saved_path_str
    pipeline.error_message     = None
    pipeline.completed_at      = now

    # Update lecture record
    lecture.status = LectureStatus.COMPLETED

    session.add(pipeline)
    session.add(lecture)
    session.commit()

    return {
        "lecture_id":   lecture_id,
        "result":       "completed",
        "saved_to":     saved_path_str,
        "detail":       "Pipeline result recorded successfully.",
    }
