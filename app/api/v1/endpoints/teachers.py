from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select
from typing import Optional

from app.core.database import get_session
from app.api.deps import get_current_user
from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
from app.models.user import User
from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate, TeacherProfileStatus

router=APIRouter()

@router.post("/upload-photo",response_model=TeacherPublic)
async def upload_teacher_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's photo
    
    - **Allowed formats**: .jpg, .jpeg, .png
    - **Max size**: 5MB
    - **Access**: Only the teacher themselves
    """
    # Ensure user is a teacher
    if current_user.role !="teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload photos"
        )
    
    # Get or create teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        # Auto-create teacher profile on first upload
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)
    
    # Ensure upload directory exists
    ensure_upload_dir_exists()

    # Delete old photo if exists
    if teacher.photo:
        delete_teacher_file(teacher.photo)

    # Save new photo
    photo_path=await save_teacher_file(photo,current_user.user_id,"photo")

    # Update database
    teacher.photo=photo_path
    session.add(teacher)
    session.commit()
    session.refresh(teacher)

    return teacher


@router.post("/upload-voice",response_model=TeacherPublic)
async def upload_teacher_voice(
    voice: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Upload or update teacher's voice sample
    
    - **Allowed formats**: .mp3, .wav, .m4a
    - **Max size**: 10MB
    - **Access**: Only the teacher themselves
    """
    # Ensure user is a teacher
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload voice samples"
        )
    
    # Get or create teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()
    
    if not teacher:
        # Auto-create teacher profile on first upload
        teacher = Teacher(user_id=current_user.user_id)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)
    
    # Ensure upload directory exists
    ensure_upload_dir_exists()
    
    # Delete old voice sample if exists
    if teacher.voice_sample:
        delete_teacher_file(teacher.voice_sample)
    
    # Save new voice sample
    voice_path = await save_teacher_file(voice, current_user.user_id, "voice")
    
    # Update database
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
    Check if teacher needs to complete profile setup (upload photo and voice sample).
    
    Returns:
    - needs_profile_setup: True if teacher hasn't uploaded both photo and voice sample
    - has_photo: Whether teacher has uploaded a photo
    - has_voice_sample: Whether teacher has uploaded a voice sample
    
    - **Access**: Only teachers
    """
    # Verify user is a teacher
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )

    # Query Teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()
    
    # If no Teacher record exists, they need to set up profile
    if not teacher:
        return {
            "needs_profile_setup": True,
            "has_photo": False,
            "has_voice_sample": False
        }
    
    # Check if both photo and voice_sample are uploaded
    has_photo = teacher.photo is not None
    has_voice_sample = teacher.voice_sample is not None
    needs_setup = not (has_photo and has_voice_sample)
    
    return {
        "needs_profile_setup": needs_setup,
        "has_photo": has_photo,
        "has_voice_sample": has_voice_sample
    }
















@router.get("/me", response_model=TeacherPublic)
async def get_teacher_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get current teacher's profile
    
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
        # Auto-create if doesn't exist
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
    Delete teacher's photo
    
    - **Access**: Only the teacher themselves
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete photos"
        )
    
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    
    if not teacher.photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No photo to delete"
        )
    
    # Delete file
    delete_teacher_file(teacher.photo)
    
    # Update database
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
    Delete teacher's voice sample
    
    - **Access**: Only the teacher themselves
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete voice samples"
        )
    
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    
    if not teacher.voice_sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No voice sample to delete"
        )
    
    # Delete file
    delete_teacher_file(teacher.voice_sample)
    
    # Update database
    teacher.voice_sample = None
    session.add(teacher)
    session.commit()
    
    return {"message": "Voice sample deleted successfully"}