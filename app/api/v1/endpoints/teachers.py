from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlmodel import Session, select
from typing import Optional

from app.core.database import get_session
from app.api.deps import get_current_user
from app.core.file_utils import save_teacher_file, delete_teacher_file, ensure_upload_dir_exists
from app.models.user import User
from app.models.teacher import Teacher, TeacherPublic, TeacherUpdate

router=APIRouter(prefix="/teachers",tags=["teachers"])

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
    
    # Get teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()

    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    
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
    
    # Get teacher record
    statement = select(Teacher).where(Teacher.user_id == current_user.user_id)
    teacher = session.exec(statement).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found"
        )
    
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


