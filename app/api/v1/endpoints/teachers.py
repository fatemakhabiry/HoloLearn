
# # app/api/v1/endpoints/teachers.py
# import logging

# import httpx
# from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
# from sqlmodel import Session, select

# from app.core.database import get_session
# from app.api.deps import get_current_user
# from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
# from app.models.user import User
# from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus
# from app.workers.onboarding_worker import run_onboarding
# from app.core.database import engine

# logger = logging.getLogger(__name__)

# router = APIRouter()


# @router.post("/upload-photo", response_model=TeacherPublic)
# async def upload_teacher_photo(
#     background_tasks: BackgroundTasks,                  # ← NEW
#     photo: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Upload or update teacher's photo and trigger face preprocessing.

#     - **Allowed formats**: .jpg, .jpeg, .png (all converted to JPEG internally)
#     - **Max size**: 5MB
#     - **Access**: Only teachers

#     After upload, preprocessing runs in the background (~30–60s).
#     Poll GET /teachers/profile-status to check when onboarding_status = 'ready'.
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can upload photos"
#         )

#     # Get or create teacher record
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         teacher = Teacher(user_id=current_user.user_id)
#         session.add(teacher)
#         session.commit()
#         session.refresh(teacher)

#     ensure_upload_dir_exists()

#     # Delete old raw photo from disk if it exists
#     if teacher.photo:
#         delete_teacher_file(teacher.photo)

#     # Save new photo → returns absolute path to uploads/instructors/{id}/raw.jpg
#     photo_path = await save_teacher_file(photo, current_user.user_id, "photo")

#     from app.core.config import settings as app_settings

#     ai_server_ready = bool(
#         app_settings.AI_SERVER_URL
#         and app_settings.BACKEND_PUBLIC_URL
#         and app_settings.INTERNAL_API_TOKEN
#     )

#     # ── Reset onboarding state ─────────────────────────────────────
#     teacher.photo = photo_path
#     teacher.preprocessed_image_path = None          # clear any stale path
#     teacher.onboarding_status = "processing" if ai_server_ready else "pending"

#     session.add(teacher)
#     session.commit()
#     session.refresh(teacher)
#     # ── Dispatch reference-embedding extraction ─────────────────────
#     # Always runs, independent of AI server availability.
#     background_tasks.add_task(
#         _extract_reference_embedding,
#         teacher_id=teacher.user_id,
#         photo_path=photo_path,
#     )

#     # ── Dispatch preprocessing to AI server ────────────────────────
#     if ai_server_ready:
#         background_tasks.add_task(
#             _dispatch_preprocess,
#             teacher_id=teacher.user_id,
#             photo_path=photo_path,
#         )
#     # ── Dispatch preprocessing to AI server ────────────────────────
#     if ai_server_ready:
#         background_tasks.add_task(
#             _dispatch_preprocess,
#             teacher_id=teacher.user_id,
#             photo_path=photo_path,
#         )

#     return teacher



# async def _dispatch_preprocess(teacher_id: int, photo_path: str) -> None:
#     """
#     Background task — POSTs to the AI server's /ai/preprocess endpoint.
#     The AI server will download the raw photo, run preprocess_image.py,
#     then call back POST /internal/onboarding-done with the PNG.
#     """
#     from app.core.config import settings as app_settings

#     base     = app_settings.BACKEND_PUBLIC_URL.rstrip("/")
#     token    = app_settings.INTERNAL_API_TOKEN
#     ai_url   = app_settings.AI_SERVER_URL.rstrip("/")

#     payload = {
#         "teacher_id":         teacher_id,
#         "image_download_url": f"{base}/api/v1/internal/files?path={photo_path}",
#         "callback_url":       f"{base}/api/v1/internal/onboarding-done",
#         "token":              token,
#     }

#     try:
#         async with httpx.AsyncClient(timeout=15.0) as client:
#             response = await client.post(
#                 f"{ai_url}/ai/preprocess",
#                 json=payload,
#                 headers={"Authorization": f"Bearer {token}"},
#             )
#         if response.status_code not in (200, 202):
#             logger.error(
#                 f"[Onboarding:{teacher_id}] AI server rejected preprocess job "
#                 f"(HTTP {response.status_code}): {response.text[:300]}"
#             )
#     except httpx.ConnectError:
#         logger.error(
#             f"[Onboarding:{teacher_id}] Could not reach AI server at {ai_url}. "
#             "Is it running and is ngrok active?"
#         )
#     except httpx.TimeoutException:
#         logger.error(f"[Onboarding:{teacher_id}] AI server did not respond within 15 seconds.")
# # Add this function in teachers.py, near _dispatch_preprocess

# def _extract_reference_embedding(teacher_id: int, photo_path: str) -> None:
#     """
#     Background task — extracts an ArcFace reference embedding from the raw
#     teacher photo and stores it on Teacher.reference_embedding.

#     Deliberately NOT async: this is CPU-bound work (DeepFace inference),
#     so Starlette runs it in a thread pool automatically rather than
#     blocking the event loop, the way it would for a plain async def here.

#     Independent of _dispatch_preprocess and ai_server_ready — ArcFace runs
#     locally on this machine and doesn't need the AI server at all, so
#     identity verification keeps working even before that's configured.
#     """
#     from app.services.face_verification import (
#         extract_embedding,
#         embedding_to_json,
#         NoFaceDetectedError,
#         MultipleFacesDetectedError,
#         FaceVerificationError,
#     )

#     try:
#         embedding = extract_embedding(photo_path)
#     except NoFaceDetectedError:
#         logger.warning(f"[ReferenceEmbedding:{teacher_id}] No face detected in {photo_path}")
#         return
#     except MultipleFacesDetectedError as e:
#         logger.warning(f"[ReferenceEmbedding:{teacher_id}] {e}")
#         return
#     except FaceVerificationError as e:
#         logger.error(f"[ReferenceEmbedding:{teacher_id}] Extraction failed: {e}")
#         return

#     with Session(engine) as session:
#         teacher = session.get(Teacher, teacher_id)
#         if not teacher:
#             logger.error(f"[ReferenceEmbedding:{teacher_id}] Teacher not found in DB")
#             return
#         teacher.reference_embedding = embedding_to_json(embedding)
#         session.add(teacher)
#         session.commit()

#     logger.info(f"[ReferenceEmbedding:{teacher_id}] Stored ({len(embedding)} dims)")

# @router.post("/upload-voice", response_model=TeacherPublic)
# async def upload_teacher_voice(
#     voice: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Upload or update teacher's voice sample.

#     - **Allowed formats**: .wav only
#     - **Max size**: 10MB
#     - **Access**: Only teachers
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can upload voice samples"
#         )

#     # Get or create teacher record
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         teacher = Teacher(user_id=current_user.user_id)
#         session.add(teacher)
#         session.commit()
#         session.refresh(teacher)

#     ensure_upload_dir_exists()

#     # Delete old voice file from disk if it exists
#     if teacher.voice_sample:
#         delete_teacher_file(teacher.voice_sample)

#     # Save new voice → returns absolute path to uploads/instructors/{id}/voice_ref.wav
#     voice_path = await save_teacher_file(voice, current_user.user_id, "voice")

#     teacher.voice_sample = voice_path
#     session.add(teacher)
#     session.commit()
#     session.refresh(teacher)

#     return teacher


# @router.get("/profile-status", response_model=TeacherProfileStatus)
# async def check_teacher_profile_status(
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Check teacher profile and onboarding state.

#     Returns:
#     - needs_profile_setup: True if photo or voice not yet uploaded
#     - has_photo: Whether teacher has uploaded a photo
#     - has_voice_sample: Whether teacher has uploaded a voice sample
#     - onboarding_status: pending | processing | ready | failed

#     Poll this endpoint after photo upload to know when preprocessing completes.
#     Generation jobs are only accepted when onboarding_status = 'ready'.

#     - **Access**: Only teachers
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can access this endpoint"
#         )

#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     # No teacher record at all — fresh account, nothing uploaded yet
#     if not teacher:
#         return {
#             "needs_profile_setup": True,
#             "has_photo": False,
#             "has_voice_sample": False,
#             "onboarding_status": "pending",          # ← NEW: was missing before
#         }

#     has_photo = teacher.photo is not None
#     has_voice_sample = teacher.voice_sample is not None
#     needs_setup = not (has_photo and has_voice_sample)

#     return {
#         "needs_profile_setup": needs_setup,
#         "has_photo": has_photo,
#         "has_voice_sample": has_voice_sample,
#         "onboarding_status": teacher.onboarding_status,   # ← NEW
#     }


# @router.get("/me", response_model=TeacherPublic)
# async def get_teacher_profile(
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Get current teacher's profile.

#     - **Access**: Only teachers
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can access this endpoint"
#         )

#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         teacher = Teacher(user_id=current_user.user_id)
#         session.add(teacher)
#         session.commit()
#         session.refresh(teacher)

#     return teacher


# @router.delete("/photo")
# async def delete_teacher_photo(
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Delete teacher's photo.

#     - **Access**: Only teachers
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can delete photos"
#         )

#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

#     if not teacher.photo:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No photo to delete")

#     delete_teacher_file(teacher.photo)

#     teacher.photo = None
#     session.add(teacher)
#     session.commit()

#     return {"message": "Photo deleted successfully"}


# @router.delete("/voice")
# async def delete_teacher_voice(
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Delete teacher's voice sample.

#     - **Access**: Only teachers
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can delete voice samples"
#         )

#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher profile not found")

#     if not teacher.voice_sample:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No voice sample to delete")

#     delete_teacher_file(teacher.voice_sample)

#     teacher.voice_sample = None
#     session.add(teacher)
#     session.commit()

#     return {"message": "Voice sample deleted successfully"}
# # ```

# # ---

# # ### What changed — summary

# # | Handler | Change | Why |
# # |---|---|---|
# # | `upload_teacher_photo` | + `BackgroundTasks` parameter | FastAPI needs it declared to inject it |
# # | `upload_teacher_photo` | + `onboarding_status = "processing"` | Frontend sees correct state immediately |
# # | `upload_teacher_photo` | + `preprocessed_image_path = None` | Clears stale path on re-upload |
# # | `upload_teacher_photo` | + `background_tasks.add_task(run_onboarding, ...)` | Dispatches preprocessing after response |
# # | `upload_teacher_voice` | Updated docstring | `.wav` only now |
# # | `check_teacher_profile_status` | + `onboarding_status` in both return paths | Matches updated `TeacherProfileStatus` schema |

# # ---

# # ### The full onboarding flow is now complete
# # ```
# # Teacher uploads photo
# #         ↓
# # save raw.jpg to disk
# #         ↓
# # DB: onboarding_status = "processing"  ← visible to frontend immediately
# #         ↓
# # HTTP 200 returned to teacher ← instant response
# #         ↓  (background, ~30–60s)
# # run_onboarding() subprocess
# #         ↓
# # DB: onboarding_status = "ready"  ← frontend polling sees this
# #     preprocessed_image_path = absolute path


# app/api/v1/endpoints/teachers.py
import logging
import os
import tempfile
from datetime import datetime
import io
from PIL import Image, ImageOps
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select

from app.core.database import get_session
from app.api.deps import get_current_user
from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
from app.models.user import User
from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus
from app.models.identity_verification import IdentityVerification, IdentityVerificationPublic
from app.services.face_verification import (
    extract_embedding,
    embedding_to_json,
    verify as verify_embeddings,
    VerificationResult,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    FaceVerificationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Add to imports at the top of app/api/v1/endpoints/teachers.py:
# import io
# from PIL import Image, ImageOps


# ──────────────────────────────────────────────────────────────────
# Orientation fix — must run BEFORE _verify_photo_pair on both files
# ──────────────────────────────────────────────────────────────────

async def _normalize_image_orientation(upload: UploadFile) -> None:
    """
    Bakes EXIF orientation into the actual pixel data, then rewrites the
    UploadFile's underlying buffer in place — so every later .read() /
    .seek(0) call (ours in _verify_photo_pair, and save_teacher_file's)
    sees the already-correctly-oriented image.

    Phone cameras (especially front/selfie cameras) commonly save sideways
    pixel data plus an EXIF "Orientation" tag telling viewers how to
    rotate it for display. PIL, OpenCV, and therefore DeepFace and
    preprocess_image.py all ignore that tag by default — they just read
    the raw pixels. Without this, the saved photo (and the preprocessed
    avatar source downstream on the AI server) ends up sideways.

    Re-encoding through PIL here also strips the EXIF tag entirely —
    the rotation is now physically baked into the pixels, so there's
    nothing left for anything downstream to misinterpret.
    """
    raw = await upload.read()
    img = Image.open(io.BytesIO(raw))

    corrected = ImageOps.exif_transpose(img)  # no-op if there's no orientation tag
    if corrected is None:
        corrected = img

    if corrected.mode in ("RGBA", "P"):
        corrected = corrected.convert("RGB")

    buf = io.BytesIO()
    corrected.save(buf, format="JPEG", quality=92)
    corrected_bytes = buf.getvalue()

    await upload.seek(0)
    upload.file.truncate()
    upload.file.write(corrected_bytes)
    await upload.seek(0)


# ──────────────────────────────────────────────────────────────────
# Shared helper — used by both verify-photo and upload-photo so the
# extraction/comparison logic exists in exactly one place.
# ──────────────────────────────────────────────────────────────────

async def _verify_photo_pair(
    photo: UploadFile,
    live_capture: UploadFile,
) -> tuple[VerificationResult, list[float]]:
    """
    Extract embeddings from both images and compare them.

    Always cleans up its own temp files. Raises HTTPException directly on
    extraction failures (no face / multiple faces / processing error) —
    both callers want identical error behavior here.

    Returns (VerificationResult, photo_embedding) — photo_embedding lets
    upload-photo store it without re-extracting.
    """
    photo_tmp_path: str | None = None
    live_tmp_path: str | None = None

    try:
        photo_bytes = await photo.read()
        live_bytes = await live_capture.read()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(photo_bytes)
            photo_tmp_path = tmp.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(live_bytes)
            live_tmp_path = tmp.name

        try:
            photo_embedding = extract_embedding(photo_tmp_path)
        except NoFaceDetectedError:
            raise HTTPException(status_code=422, detail="No face detected in the photo. Please try a clearer photo.")
        except MultipleFacesDetectedError as e:
            raise HTTPException(status_code=422, detail=f"Photo: {e}")
        except FaceVerificationError as e:
            raise HTTPException(status_code=500, detail=f"Could not process the photo: {e}")

        try:
            live_embedding = extract_embedding(live_tmp_path)
        except NoFaceDetectedError:
            raise HTTPException(status_code=422, detail="No face detected in the live capture. Please retake.")
        except MultipleFacesDetectedError as e:
            raise HTTPException(status_code=422, detail=f"Live capture: {e}")
        except FaceVerificationError as e:
            raise HTTPException(status_code=500, detail=f"Could not process the live capture: {e}")

        result = verify_embeddings(photo_embedding, live_embedding)
        return result, photo_embedding

    finally:
        if photo_tmp_path and os.path.exists(photo_tmp_path):
            os.unlink(photo_tmp_path)
        if live_tmp_path and os.path.exists(live_tmp_path):
            os.unlink(live_tmp_path)


# ──────────────────────────────────────────────────────────────────
# Optional stateless pre-check — saves nothing
# ──────────────────────────────────────────────────────────────────

@router.post("/verify-photo", response_model=IdentityVerificationPublic)
async def verify_teacher_photo(
    photo: UploadFile = File(..., description="Avatar source photo — from gallery or camera"),
    live_capture: UploadFile = File(..., description="Live camera capture taken right after selecting the photo"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Stateless pre-check: does this live capture match this photo?

    Saves nothing. Useful for instant UI feedback before committing to
    upload-photo. Calling this first is OPTIONAL — upload-photo performs
    the identical check itself before saving anything, so Flutter can
    call upload-photo directly and skip this if it doesn't need a
    separate "checking..." step.
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only teachers can verify photos")

    # ── Fix rotation before anything reads/compares/saves these images ──
    await _normalize_image_orientation(photo)
    await _normalize_image_orientation(live_capture)

    result, _ = await _verify_photo_pair(photo, live_capture)

    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if teacher:
        record = IdentityVerification(
            teacher_id=teacher.user_id,
            distance=result.distance,
            passed=result.passed,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        created_at = record.created_at
    else:
        created_at = datetime.utcnow()

    return IdentityVerificationPublic(
        passed=result.passed,
        distance=result.distance,
        created_at=created_at,
    )


# ──────────────────────────────────────────────────────────────────
# Upload or change the avatar photo — verify, then save
# ──────────────────────────────────────────────────────────────────

@router.post("/upload-photo", response_model=TeacherPublic)
async def upload_teacher_photo(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(..., description="Avatar source photo — from gallery or camera"),
    live_capture: UploadFile = File(..., description="Live camera capture taken right after selecting the photo, used to confirm it's really the teacher"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's photo and trigger face preprocessing.

    Both `photo` and `live_capture` are required on every call, including
    later photo changes. If they don't match closely enough, NOTHING is
    saved — any existing photo stays untouched, and the teacher must retry.
    This is the only identity check in the system; there is no separate
    check at hologram-generation time.

    - **Allowed formats**: .jpg, .jpeg, .png (all converted to JPEG internally)
    - **Max size**: 5MB per file
    - **Access**: Only teachers

    After a verified upload, preprocessing runs in the background (~30–60s).
    Poll GET /teachers/profile-status to check when onboarding_status = 'ready'.
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload photos"
        )

    # ── Fix rotation before anything reads/compares/saves these images ──
    await _normalize_image_orientation(photo)
    await _normalize_image_orientation(live_capture)

    # Get or create teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)

    # ── Verify live capture against the candidate photo ─────────────
    result, photo_embedding = await _verify_photo_pair(photo, live_capture)

    session.add(IdentityVerification(
        teacher_id=teacher.user_id,
        distance=result.distance,
        passed=result.passed,
    ))
    session.commit()

    if not result.passed:
        raise HTTPException(
            status_code=422,
            detail="The live photo doesn't match the uploaded photo. Please retry with a clear, current photo of yourself.",
        )

    # ── Verified — persist the photo as official ────────────────────
    ensure_upload_dir_exists()

    # Delete old raw photo from disk if it exists
    if teacher.photo:
        delete_teacher_file(teacher.photo)

    # Rewind: _verify_photo_pair already consumed photo.read() internally,
    # and save_teacher_file needs to read it again from the start. This
    # now reads the orientation-corrected bytes, not the original ones —
    # _normalize_image_orientation already rewrote photo's buffer in place.
    await photo.seek(0)
    photo_path = await save_teacher_file(photo, current_user.user_id, "photo")

    from app.core.config import settings as app_settings

    ai_server_ready = bool(
        app_settings.AI_SERVER_URL
        and app_settings.BACKEND_PUBLIC_URL
        and app_settings.INTERNAL_API_TOKEN
    )

    # ── Reset onboarding state ─────────────────────────────────────
    teacher.photo = photo_path
    teacher.reference_embedding = embedding_to_json(photo_embedding)
    teacher.preprocessed_image_path = None          # clear any stale path
    teacher.onboarding_status = "processing" if ai_server_ready else "pending"

    session.add(teacher)
    session.commit()
    session.refresh(teacher)

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


@router.post("/upload-voice", response_model=TeacherPublic)
async def upload_teacher_voice(
    voice: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's voice sample.

    - **Allowed formats**: .wav, .mp3, .m4a, .aac, .ogg, .flac
      (automatically transcoded to mono 16-bit WAV on upload)
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
            "onboarding_status": "pending",
        }

    has_photo = teacher.photo is not None
    has_voice_sample = teacher.voice_sample is not None
    needs_setup = not (has_photo and has_voice_sample)

    return {
        "needs_profile_setup": needs_setup,
        "has_photo": has_photo,
        "has_voice_sample": has_voice_sample,
        "onboarding_status": teacher.onboarding_status,
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