from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
from app.services.google_drive import drive_service
import os

from app.core.database import get_session
from app.models.lecture import Lecture, LectureType, LectureStatus , LecturePublic
from app.models.schedule import Schedule, SchedulePublic, ScheduleCreate
from app.models.user import User, UserRole
from app.models.course import Course
from app.api.deps import get_current_user,get_current_teacher
from app.schemas.schedule_schemas import ConfirmPublishResponse,ConfirmPublishRequest

router = APIRouter()



@router.post("/create-draft", response_model=LecturePublic, status_code=status.HTTP_201_CREATED)
async def create_lecture_draft(
    title: str = Form(..., description="Lecture title"),
    course_code: str = Form(..., description="Course code"),
    file: UploadFile = File(..., description="Lecture file (PDF, PPTX, or TXT)"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    STEP 1: Create lecture draft with file upload to Google Drive
    
    Flow:
    1. Receive file from Flutter
    2. Upload to Google Drive
    3. Create lecture record with Drive URL
    4. Return lecture_id for next step
    """
    
    # 1. Verify user is a teacher
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create lectures"
        )
    
    # 2. Verify course exists and belongs to teacher
    course = session.get(Course, course_code)
    print("mo4kla")
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}'not found in database"
        )
    print("errooooooor")
    if course.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create lectures for your own courses"
        )
    
    # 3. Validate file
    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed: PDF, PPTX, TXT"
        )
    
    # 4. Save file temporarily
    temp_dir = "/tmp/hololearn_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filename = f"temp_{current_user.user_id}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 5. Upload to Google Drive
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"{course_code}_{title}_{timestamp}{file_ext}"
        
        drive_result = drive_service.upload_file(
            file_path=temp_path,
            filename=drive_filename,
            mime_type=file.content_type
        )
        
        # 6. Create lecture record with Drive URL
        lecture = Lecture(
            title=title,
            teacher_id=current_user.user_id,
            course_code=course_code,
            lecture_type=LectureType.PREPARED,
            status=LectureStatus.DRAFT,
            final_content=drive_result['view_link']  # ← Google Drive URL
        )
        
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        
        return lecture
        
    except Exception as e:
        # Rollback if anything fails
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lecture: {str(e)}"
        )
    
    finally:
        # 7. Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass  # Ignore cleanup errors



# ============================================
# STEP 2: Confirm & Publish with Schedule
# ============================================

@router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
async def confirm_and_publish_lecture(
    lecture_id: int,
    request_data: ConfirmPublishRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    STEP 2: Confirm and publish lecture by reserving an existing schedule slot
    
    Flow:
    1. Verify lecture exists and belongs to teacher
    2. Verify schedule exists and is available
    3. Reserve the schedule (assign lecture_id and change status)
    4. Update lecture status to COMPLETED
    5. Return success
    
    Request Body (JSON):
    {
        "schedule_id": 5
    }
    
    Response:
    {
        "message": "Lecture published successfully",
        "lecture_id": 1,
        "schedule_id": 5,
        "lecture_title": "Intro to Computing",
        "course_code": "CS101",
        "lecture_status": "completed",
        "schedule_status": "scheduled",
        "scheduled_date": "2025-01-20",
        "start_time": "10:00:00",
        "end_time": "11:00:00"
    }
    """
    
    # 1. Get lecture
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    # 2. Verify ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own lectures"
        )
    
    # 3. Verify lecture is in draft status
    if lecture.status != LectureStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lecture is already {lecture.status}. Can only publish draft lectures."
        )
    
    # 4. Get the schedule slot
    schedule = session.get(Schedule, request_data.schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule slot with ID {request_data.schedule_id} not found"
        )
    
    # 5. Verify schedule belongs to current teacher
    if schedule.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This schedule slot does not belong to you"
        )
    
    # 6. Verify schedule is available (not already reserved)
    if schedule.lecture_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This schedule slot is already reserved for another lecture"
        )
    
    # 7. Verify schedule status is available
    if schedule.status not in ["available", "scheduled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This schedule slot is not available (status: {schedule.status})"
        )
    
    # 8. Reserve the schedule slot
    schedule.lecture_id = lecture_id
    schedule.status = "scheduled"  # Change from "available" to "scheduled"
    session.add(schedule)
    
    # 9. Update lecture status to COMPLETED
    lecture.status = LectureStatus.COMPLETED
    session.add(lecture)
    
    # 10. Commit both changes
    session.commit()
    session.refresh(lecture)
    session.refresh(schedule)
    
    # 11. Return success response
    return ConfirmPublishResponse(
        message="Lecture published  and scheduled successfully",
        lecture_id=lecture.lecture_id,
        schedule_id=schedule.schedule_id,
        lecture_title=lecture.title,
        course_code=lecture.course_code,
        lecture_status=lecture.status.value,
        schedule_status=schedule.status,
        scheduled_date=schedule.date,
        start_time=schedule.start_time,
        end_time=schedule.end_time
    )


# ============================================
# CANCEL: Delete Lecture and Schedule
# ============================================

# @router.delete("/{lecture_id}/cancel", status_code=status.HTTP_200_OK)
# async def cancel_lecture(
#     lecture_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Cancel and delete a lecture
    
#     This deletes:
#     1. The lecture record
#     2. All associated schedules
#     3. Optionally: the uploaded file
    
#     Can be called from either screen
    
#     Response:
#     {
#         "message": "Lecture cancelled successfully",
#         "deleted_lecture_id": 1,
#         "deleted_schedules": 2
#     }
#     """
    
#     # 1. Get lecture
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     # 2. Verify ownership
#     if lecture.teacher_id != current_user.user_id and current_user.role != UserRole.ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only cancel your own lectures"
#         )
    
#     # 3. Delete associated schedules
#     schedules = session.exec(
#         select(Schedule).where(Schedule.lecture_id == lecture_id)
#     ).all()
    
#     schedules_count = len(schedules)
    
#     for schedule in schedules:
#         session.delete(schedule)
    
#     # 4. Optionally delete the file
#     if lecture.final_content and os.path.exists(lecture.final_content):
#         try:
#             os.remove(lecture.final_content)
#         except Exception as e:
#             # Log error but don't fail the deletion
#             print(f"Warning: Could not delete file {lecture.final_content}: {e}")
    
#     # 5. Delete lecture
#     lecture_title = lecture.title
#     session.delete(lecture)
    
#     session.commit()
    
#     return {
#         "message": "Lecture cancelled successfully",
#         "deleted_lecture_id": lecture_id,
#         "lecture_title": lecture_title,
#         "deleted_schedules": schedules_count
#     }


# # ============================================
# # HELPER ENDPOINTS
# # ============================================

# @router.get("/{lecture_id}", response_model=LecturePublic)
# async def get_lecture(
#     lecture_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get a specific lecture"""
    
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     # Check permissions
#     if (current_user.role == UserRole.TEACHER and 
#         lecture.teacher_id != current_user.user_id):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only view your own lectures"
#         )
    
#     return lecture


# @router.get("/{lecture_id}/schedule", response_model=SchedulePublic)
# async def get_lecture_schedule(
#     lecture_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get the schedule for a specific lecture"""
    
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     # Get schedule
#     schedule = session.exec(
#         select(Schedule).where(Schedule.lecture_id == lecture_id)
#     ).first()
    
#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No schedule found for lecture {lecture_id}"
#         )
    
#     return schedule


# @router.put("/{lecture_id}/schedule", response_model=SchedulePublic)
# async def update_lecture_schedule(
#     lecture_id: int,
#     schedule_data: ScheduleCreate,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """Update the schedule for a lecture"""
    
#     # Verify lecture exists and belongs to teacher
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only update your own lecture schedules"
#         )
    
#     # Get existing schedule
#     schedule = session.exec(
#         select(Schedule).where(Schedule.lecture_id == lecture_id)
#     ).first()
    
#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No schedule found for lecture {lecture_id}"
#         )
    
#     # Update schedule
#     schedule.start_time = schedule_data.start_time
#     schedule.end_time = schedule_data.end_time
#     schedule.date = schedule_data.date
#     if schedule_data.status:
#         schedule.status = schedule_data.status
    
#     session.add(schedule)
#     session.commit()
#     session.refresh(schedule)
    
#     return schedule
