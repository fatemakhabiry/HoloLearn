# from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
# from sqlmodel import Session, select
# from typing import Optional

# from app.core.database import get_session
# from app.api.deps import get_current_user
# from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
# from app.models.user import User
# from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus

# router=APIRouter()

# @router.post("/upload-photo",response_model=TeacherPublic)
# async def upload_teacher_photo(
#     photo: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Upload or update teacher's photo
    
#     - **Allowed formats**: .jpg, .jpeg, .png
#     - **Max size**: 5MB
#     - **Access**: Only the teacher themselves
#     """
#     # Ensure user is a teacher
#     if current_user.role !="teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can upload photos"
#         )
    
#     # Get or create teacher record
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()

#     if not teacher:
#         # Auto-create teacher profile on first upload
#         teacher = Teacher(user_id=current_user.user_id)
#         session.add(teacher)
#         session.commit()
#         session.refresh(teacher)
    
#     # Ensure upload directory exists
#     ensure_upload_dir_exists()

#     # Delete old photo if exists
#     if teacher.photo:
#         delete_teacher_file(teacher.photo)

#     # Save new photo
#     photo_path=await save_teacher_file(photo,current_user.user_id,"photo")

#     # Update database
#     teacher.photo=photo_path
#     session.add(teacher)
#     session.commit()
#     session.refresh(teacher)

#     return teacher


# @router.post("/upload-voice",response_model=TeacherPublic)
# async def upload_teacher_voice(
#     voice: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Upload or update teacher's voice sample
    
#     - **Allowed formats**: .mp3, .wav, .m4a
#     - **Max size**: 10MB
#     - **Access**: Only the teacher themselves
#     """
#     # Ensure user is a teacher
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can upload voice samples"
#         )
    
#     # Get or create teacher record
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()
    
#     if not teacher:
#         # Auto-create teacher profile on first upload
#         teacher = Teacher(user_id=current_user.user_id)
#         session.add(teacher)
#         session.commit()
#         session.refresh(teacher)
    
#     # Ensure upload directory exists
#     ensure_upload_dir_exists()
    
#     # Delete old voice sample if exists
#     if teacher.voice_sample:
#         delete_teacher_file(teacher.voice_sample)
    
#     # Save new voice sample
#     voice_path = await save_teacher_file(voice, current_user.user_id, "voice")
    
#     # Update database
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
#     Check if teacher needs to complete profile setup (upload photo and voice sample).
    
#     Returns:
#     - needs_profile_setup: True if teacher hasn't uploaded both photo and voice sample
#     - has_photo: Whether teacher has uploaded a photo
#     - has_voice_sample: Whether teacher has uploaded a voice sample
    
#     - **Access**: Only teachers
#     """
#     # Verify user is a teacher
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can access this endpoint"
#         )

#     # Query Teacher record
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()
    
#     # If no Teacher record exists, they need to set up profile
#     if not teacher:
#         return {
#             "needs_profile_setup": True,
#             "has_photo": False,
#             "has_voice_sample": False
#         }
    
#     # Check if both photo and voice_sample are uploaded
#     has_photo = teacher.photo is not None
#     has_voice_sample = teacher.voice_sample is not None
#     needs_setup = not (has_photo and has_voice_sample)
    
#     return {
#         "needs_profile_setup": needs_setup,
#         "has_photo": has_photo,
#         "has_voice_sample": has_voice_sample
#     }
















# @router.get("/me", response_model=TeacherPublic)
# async def get_teacher_profile(
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session)
# ):
#     """
#     Get current teacher's profile
    
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
#         # Auto-create if doesn't exist
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
#     Delete teacher's photo
    
#     - **Access**: Only the teacher themselves
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can delete photos"
#         )
    
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()
    
#     if not teacher:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Teacher profile not found"
#         )
    
#     if not teacher.photo:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No photo to delete"
#         )
    
#     # Delete file
#     delete_teacher_file(teacher.photo)
    
#     # Update database
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
#     Delete teacher's voice sample
    
#     - **Access**: Only the teacher themselves
#     """
#     if current_user.role != "teacher":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only teachers can delete voice samples"
#         )
    
#     statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
#     teacher = session.exec(statement).first()
    
#     if not teacher:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Teacher profile not found"
#         )
    
#     if not teacher.voice_sample:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No voice sample to delete"
#         )
    
#     # Delete file
#     delete_teacher_file(teacher.voice_sample)
    
#     # Update database
#     teacher.voice_sample = None
#     session.add(teacher)
#     session.commit()
    
#     return {"message": "Voice sample deleted successfully"}


# app/api/v1/endpoints/teachers.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select

from app.core.database import get_session
from app.api.deps import get_current_user
from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
from app.models.user import User
from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus
from app.workers.onboarding_worker import run_onboarding

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

    # ── Reset onboarding state ─────────────────────────────────────
    # If teacher is re-uploading, the old preprocessed file is now stale.
    # Clear it so the worker writes a fresh one.
    teacher.photo = photo_path
    teacher.onboarding_status = "processing"        # ← NEW
    teacher.preprocessed_image_path = None          # ← NEW: clear stale path

    session.add(teacher)
    session.commit()
    session.refresh(teacher)

    # ── Dispatch background preprocessing ─────────────────────────
    # run_onboarding opens its own DB session internally.
    # We only pass IDs and paths — never the request session.
    background_tasks.add_task(                      # ← NEW
        run_onboarding,
        teacher_id=teacher.user_id,
        raw_image_path=photo_path,
    )

    return teacher


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