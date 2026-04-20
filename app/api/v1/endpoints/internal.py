# app/api/v1/endpoints/internal.py
"""
Internal endpoints — called by the AI server (friend's PC), NOT by the frontend.

Token accepted in any of these forms (checked in order):
  1. Authorization: Bearer <token>   header   (Swagger / httpx standard)
  2. X-Internal-Token: <token>       header   (used by ai_server _download_file)
  3. token                           form field (used by ai_server callbacks)

Endpoints
---------
GET  /internal/files
    AI server downloads a file by absolute path on the laptop.
    Auth via X-Internal-Token or Authorization header.

POST /internal/onboarding-done
    AI server calls after preprocess_image.py finishes.
    Receives preprocessed PNG as multipart `image` field.
    Saves PNG to disk, sets teacher.onboarding_status = 'ready'.

POST /internal/pipeline-done
    AI server calls after avatar pipeline finishes.
    Receives MP4 as multipart `video` field.
    Saves MP4 to disk, updates lecture_pipelines + lectures.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.models.lecture import Lecture, LectureStatus
from app.models.lecture_pipeline import LecturePipeline, PipelineStatus
from app.models.teacher import Teacher

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Flexible token guard ───────────────────────────────────────────────────────
# Accepts token from Authorization header, X-Internal-Token header, or form field.

_bearer_scheme = HTTPBearer(auto_error=False)


def _check_token(token: Optional[str]) -> None:
    """Raise 403/503 if token is wrong; raise nothing if correct."""
    if not settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_API_TOKEN is not configured on this server.",
        )
    if not token or token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal API token.",
        )


def _resolve_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    x_internal_token: Optional[str],
    form_token: Optional[str] = None,
) -> str:
    """Pick token from whichever source was provided."""
    if credentials:
        return credentials.credentials
    if x_internal_token:
        return x_internal_token
    if form_token:
        return form_token
    return ""


# ── GET /internal/files ────────────────────────────────────────────────────────

@router.get("/files")
def serve_file(
    path: str = Query(..., description="Absolute path on the laptop's disk"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_internal_token: Optional[str] = Header(None),
):
    """
    Serve any file on the laptop's disk to the AI server.

    Used by ai_server to download:
      - raw teacher photo      (raw.jpg)
      - generated script       (script.txt)
      - voice reference sample (voice_ref.wav)

    Token accepted as:
      Authorization: Bearer <token>   OR   X-Internal-Token: <token>
    """
    _check_token(_resolve_token(credentials, x_internal_token))

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file.")

    logger.info(f"[InternalFiles] Serving → {path}")
    return FileResponse(path=str(file_path), filename=file_path.name)


# ── POST /internal/onboarding-done ────────────────────────────────────────────

@router.post("/onboarding-done")
async def onboarding_done(
    teacher_id: int                 = Form(...),
    status_field: str               = Form(..., alias="status"),
    token: Optional[str]            = Form(None),
    error_message: Optional[str]    = Form(None),
    image: Optional[UploadFile]     = File(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_internal_token: Optional[str] = Header(None),
    db: Session = Depends(get_session),
):
    """
    Called by ai_server after preprocess_image.py finishes.

    Success  → ai_server sends form fields (teacher_id, status="completed", token)
               + multipart file field `image` (the preprocessed PNG)
               Laptop saves PNG to UPLOADS_DIR/instructors/<id>/raw_preprocessed.png
               and sets teacher.onboarding_status = 'ready'.

    Failure  → ai_server sends form fields (teacher_id, status="failed",
               token, error_message).  No file.
               Laptop sets teacher.onboarding_status = 'failed'.
    """
    _check_token(_resolve_token(credentials, x_internal_token, token))

    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher {teacher_id} not found.")

    now = datetime.utcnow()

    # ── Failure path ──────────────────────────────────────────────────────────
    if status_field == "failed":
        teacher.onboarding_status = "failed"
        db.add(teacher)
        db.commit()
        logger.error(f"[OnboardingDone] Teacher {teacher_id} FAILED — {(error_message or '')[:200]}")
        return {"teacher_id": teacher_id, "result": "failed"}

    # ── Success path ──────────────────────────────────────────────────────────
    if not image:
        raise HTTPException(
            status_code=422,
            detail="image file is required when status='completed'.",
        )

    # Save preprocessed PNG next to raw.jpg
    uploads_dir = Path(settings.UPLOADS_DIR) if settings.UPLOADS_DIR else Path("uploads")
    teacher_dir = uploads_dir / "instructors" / str(teacher_id)
    teacher_dir.mkdir(parents=True, exist_ok=True)

    save_path = teacher_dir / "raw_preprocessed.png"
    try:
        with save_path.open("wb") as f:
            shutil.copyfileobj(image.file, f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save image: {exc}")
    finally:
        await image.close()

    saved_path_str = str(save_path.resolve())

    teacher.onboarding_status       = "ready"
    teacher.preprocessed_image_path = saved_path_str
    db.add(teacher)
    db.commit()

    logger.info(f"[OnboardingDone] Teacher {teacher_id} → ready | PNG saved → {saved_path_str}")
    return {
        "teacher_id":              teacher_id,
        "onboarding_status":       "ready",
        "preprocessed_image_path": saved_path_str,
        "detail":                  "Teacher onboarding marked as ready.",
    }


# ── POST /internal/pipeline-done ──────────────────────────────────────────────

@router.post("/pipeline-done")
async def pipeline_done(
    lecture_id: int                 = Form(...),
    status_field: str               = Form(..., alias="status"),
    token: Optional[str]            = Form(None),
    error_message: Optional[str]    = Form(None),
    video: Optional[UploadFile]     = File(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_internal_token: Optional[str] = Header(None),
    db: Session = Depends(get_session),
):
    """
    Called by ai_server when avatar generation finishes.

    Success  → ai_server sends form fields (lecture_id, status="completed", token)
               + multipart file field `video` (the avatar MP4).
               Laptop saves MP4 to OUTPUTS_DIR/lectures/<id>/avatar_<id>.mp4
               and marks lecture + pipeline as COMPLETED.

    Failure  → ai_server sends form fields (lecture_id, status="failed",
               token, error_message).  No file.
               Laptop marks lecture + pipeline as FAILED.
    """
    _check_token(_resolve_token(credentials, x_internal_token, token))

    pipeline = db.get(LecturePipeline, lecture_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail=f"No pipeline found for lecture_id={lecture_id}")

    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail=f"No lecture found for lecture_id={lecture_id}")

    now = datetime.utcnow()

    # ── Failure path ──────────────────────────────────────────────────────────
    if status_field == "failed":
        logger.error(f"[PipelineDone] Lecture {lecture_id} FAILED — {(error_message or '')[:200]}")
        pipeline.status        = PipelineStatus.FAILED
        pipeline.error_message = (error_message or "")[:2000]
        pipeline.completed_at  = now
        lecture.status         = LectureStatus.FAILED
        db.add(pipeline)
        db.add(lecture)
        db.commit()
        return {"lecture_id": lecture_id, "result": "failed"}

    # ── Success path ──────────────────────────────────────────────────────────
    if not video:
        raise HTTPException(
            status_code=422,
            detail="video file is required when status='completed'.",
        )

    filename = video.filename or ""
    if not filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an .mp4 file.")

    outputs_dir = Path(settings.OUTPUTS_DIR) if settings.OUTPUTS_DIR else Path("outputs")
    lecture_out_dir = outputs_dir / "lectures" / str(lecture_id)
    lecture_out_dir.mkdir(parents=True, exist_ok=True)

    save_path = lecture_out_dir / f"avatar_{lecture_id}.mp4"
    try:
        with save_path.open("wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save video: {exc}")
    finally:
        await video.close()

    saved_path_str = str(save_path.resolve())
    logger.info(f"[PipelineDone] Lecture {lecture_id} — MP4 saved → {saved_path_str}")

    pipeline.status            = PipelineStatus.COMPLETED
    pipeline.output_video_path = saved_path_str
    pipeline.error_message     = None
    pipeline.completed_at      = now
    lecture.status             = LectureStatus.COMPLETED

    db.add(pipeline)
    db.add(lecture)
    db.commit()

    return {
        "lecture_id": lecture_id,
        "result":     "completed",
        "saved_to":   saved_path_str,
    }
