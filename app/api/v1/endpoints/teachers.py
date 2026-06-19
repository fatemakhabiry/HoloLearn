
# app/api/v1/endpoints/teachers.py
import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select

from app.core.database import get_session
from app.api.deps import get_current_user
from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
from app.models.user import User
from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus
from app.workers.onboarding_worker import run_onboarding
from app.core.database import engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload-photo", response_model=TeacherPublic)
async def upload_teacher_photo(
    background_tasks: BackgroundTasks,                  # ← NEW
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's photo and trigger face preprocessing.

    - **Allowed formats**: .jpg, .jpeg, .png (all converted to JPEG internally)
    - **Max size**: 5MB
    - **Access**: Only teachers

    After upload, preprocessing runs in the background (~30–60s).
    Poll GET /teachers/profile-status to check when onboarding_status = 'ready'.
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload photos"
        )

    # Get or create teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)

    ensure_upload_dir_exists()

    # Delete old raw photo from disk if it exists
    if teacher.photo:
        delete_teacher_file(teacher.photo)

    # Save new photo → returns absolute path to uploads/instructors/{id}/raw.jpg
    photo_path = await save_teacher_file(photo, current_user.user_id, "photo")

    from app.core.config import settings as app_settings

    ai_server_ready = bool(
        app_settings.AI_SERVER_URL
        and app_settings.BACKEND_PUBLIC_URL
        and app_settings.INTERNAL_API_TOKEN
    )

    # ── Reset onboarding state ─────────────────────────────────────
    teacher.photo = photo_path
    teacher.preprocessed_image_path = None          # clear any stale path
    teacher.onboarding_status = "processing" if ai_server_ready else "pending"

    session.add(teacher)
    session.commit()
    session.refresh(teacher)
    # ── Dispatch reference-embedding extraction ─────────────────────
    # Always runs, independent of AI server availability.
    background_tasks.add_task(
        _extract_reference_embedding,
        teacher_id=teacher.user_id,
        photo_path=photo_path,
    )

    # ── Dispatch preprocessing to AI server ────────────────────────
    if ai_server_ready:
        background_tasks.add_task(
            _dispatch_preprocess,
            teacher_id=teacher.user_id,
            photo_path=photo_path,
        )
    # ── Dispatch preprocessing to AI server ────────────────────────
    if ai_server_ready:
        background_tasks.add_task(
            _dispatch_preprocess,
            teacher_id=teacher.user_id,
            photo_path=photo_path,
        )

    return teacher



async def _dispatch_preprocess(teacher_id: int, photo_path: str) -> None:
    """
    Background task — POSTs to the AI server's /ai/preprocess endpoint.
    The AI server will download the raw photo, run preprocess_image.py,
    then call back POST /internal/onboarding-done with the PNG.
    """
    from app.core.config import settings as app_settings

    base     = app_settings.BACKEND_PUBLIC_URL.rstrip("/")
    token    = app_settings.INTERNAL_API_TOKEN
    ai_url   = app_settings.AI_SERVER_URL.rstrip("/")

    payload = {
        "teacher_id":         teacher_id,
        "image_download_url": f"{base}/api/v1/internal/files?path={photo_path}",
        "callback_url":       f"{base}/api/v1/internal/onboarding-done",
        "token":              token,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{ai_url}/ai/preprocess",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code not in (200, 202):
            logger.error(
                f"[Onboarding:{teacher_id}] AI server rejected preprocess job "
                f"(HTTP {response.status_code}): {response.text[:300]}"
            )
    except httpx.ConnectError:
        logger.error(
            f"[Onboarding:{teacher_id}] Could not reach AI server at {ai_url}. "
            "Is it running and is ngrok active?"
        )
    except httpx.TimeoutException:
        logger.error(f"[Onboarding:{teacher_id}] AI server did not respond within 15 seconds.")
# Add this function in teachers.py, near _dispatch_preprocess

def _extract_reference_embedding(teacher_id: int, photo_path: str) -> None:
    """
    Background task — extracts an ArcFace reference embedding from the raw
    teacher photo and stores it on Teacher.reference_embedding.

    Deliberately NOT async: this is CPU-bound work (DeepFace inference),
    so Starlette runs it in a thread pool automatically rather than
    blocking the event loop, the way it would for a plain async def here.

    Independent of _dispatch_preprocess and ai_server_ready — ArcFace runs
    locally on this machine and doesn't need the AI server at all, so
    identity verification keeps working even before that's configured.
    """
    from app.services.face_verification import (
        extract_embedding,
        embedding_to_json,
        NoFaceDetectedError,
        MultipleFacesDetectedError,
        FaceVerificationError,
    )

    try:
        embedding = extract_embedding(photo_path)
    except NoFaceDetectedError:
        logger.warning(f"[ReferenceEmbedding:{teacher_id}] No face detected in {photo_path}")
        return
    except MultipleFacesDetectedError as e:
        logger.warning(f"[ReferenceEmbedding:{teacher_id}] {e}")
        return
    except FaceVerificationError as e:
        logger.error(f"[ReferenceEmbedding:{teacher_id}] Extraction failed: {e}")
        return

    with Session(engine) as session:
        teacher = session.get(Teacher, teacher_id)
        if not teacher:
            logger.error(f"[ReferenceEmbedding:{teacher_id}] Teacher not found in DB")
            return
        teacher.reference_embedding = embedding_to_json(embedding)
        session.add(teacher)
        session.commit()

    logger.info(f"[ReferenceEmbedding:{teacher_id}] Stored ({len(embedding)} dims)")

@router.post("/upload-voice", response_model=TeacherPublic)
async def upload_teacher_voice(
    voice: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's voice sample.

    - **Allowed formats**: .wav only
    - **Max size**: 10MB
    - **Access**: Only teachers
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload voice samples"
        )

    # Get or create teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)

    ensure_upload_dir_exists()

    # Delete old voice file from disk if it exists
    if teacher.voice_sample:
        delete_teacher_file(teacher.voice_sample)

    # Save new voice → returns absolute path to uploads/instructors/{id}/voice_ref.wav
    voice_path = await save_teacher_file(voice, current_user.user_id, "voice")

    teacher.voice_sample = voice_path
    session.add(teacher)
    session.commit()
    session.refresh(teacher)

    return teacher


@router.get("/profile-status", response_model=TeacherProfileStatus)
async def check_teacher_profile_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Check teacher profile and onboarding state.

    Returns:
    - needs_profile_setup: True if photo or voice not yet uploaded
    - has_photo: Whether teacher has uploaded a photo
    - has_voice_sample: Whether teacher has uploaded a voice sample
    - onboarding_status: pending | processing | ready | failed

    Poll this endpoint after photo upload to know when preprocessing completes.
    Generation jobs are only accepted when onboarding_status = 'ready'.

    - **Access**: Only teachers
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )

    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    # No teacher record at all — fresh account, nothing uploaded yet
    if not teacher:
        return {
            "needs_profile_setup": True,
            "has_photo": False,
            "has_voice_sample": False,
            "onboarding_status": "pending",          # ← NEW: was missing before
        }

    has_photo = teacher.photo is not None
    has_voice_sample = teacher.voice_sample is not None
    needs_setup = not (has_photo and has_voice_sample)

    return {
        "needs_profile_setup": needs_setup,
        "has_photo": has_photo,
        "has_voice_sample": has_voice_sample,
        "onboarding_status": teacher.onboarding_status,   # ← NEW
    }


@router.get("/me", response_model=TeacherPublic)
async def get_teacher_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get current teacher's profile.

    - **Access**: Only teachers
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )

    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)

    return teacher


@router.delete("/photo")
async def delete_teacher_photo(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete teacher's photo.

    - **Access**: Only teachers
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete photos"
        )

    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    if not teacher.photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No photo to delete")

    delete_teacher_file(teacher.photo)

    teacher.photo = None
    session.add(teacher)
    session.commit()

    return {"message": "Photo deleted successfully"}


@router.delete("/voice")
async def delete_teacher_voice(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete teacher's voice sample.

    - **Access**: Only teachers
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete voice samples"
        )

    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

    if not teacher.voice_sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No voice sample to delete")

    delete_teacher_file(teacher.voice_sample)

    teacher.voice_sample = None
    session.add(teacher)
    session.commit()

    return {"message": "Voice sample deleted successfully"}
# ```

# ---

# ### What changed — summary

# | Handler | Change | Why |
# |---|---|---|
# | `upload_teacher_photo` | + `BackgroundTasks` parameter | FastAPI needs it declared to inject it |
# | `upload_teacher_photo` | + `onboarding_status = "processing"` | Frontend sees correct state immediately |
# | `upload_teacher_photo` | + `preprocessed_image_path = None` | Clears stale path on re-upload |
# | `upload_teacher_photo` | + `background_tasks.add_task(run_onboarding, ...)` | Dispatches preprocessing after response |
# | `upload_teacher_voice` | Updated docstring | `.wav` only now |
# | `check_teacher_profile_status` | + `onboarding_status` in both return paths | Matches updated `TeacherProfileStatus` schema |

# ---

# ### The full onboarding flow is now complete
# ```
# Teacher uploads photo
#         ↓
# save raw.jpg to disk
#         ↓
# DB: onboarding_status = "processing"  ← visible to frontend immediately
#         ↓
# HTTP 200 returned to teacher ← instant response
#         ↓  (background, ~30–60s)
# run_onboarding() subprocess
#         ↓
# DB: onboarding_status = "ready"  ← frontend polling sees this
#     preprocessed_image_path = absolute path