from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlmodel import Session, select
from typing import Optional ,List
from datetime import time , date,datetime
from app.services.google_drive import drive_service
import os

from app.core.database import get_session
from app.models.lecture import Lecture, LectureType, LectureStatus , LecturePublic
from app.models.schedule import Schedule, SchedulePublic, ScheduleCreate
from app.models.user import User, UserRole
from app.models.course import Course
from app.api.deps import get_current_user,get_current_teacher
from app.schemas.schedule_schemas import (ConfirmPublishResponse,
 ConfirmPublishRequest,
 LectureEditDetails,
 EditLectureResponse,
 FullTimeSlot2,
 EditLectureRequest,
 DeleteLectureResponse
)

router = APIRouter()



# ============================================
# 1: Create Draft Lecture
# ============================================

@router.post("/create-draft", response_model=LecturePublic, status_code=status.HTTP_201_CREATED)
async def create_lecture_draft(
    title: str = Form(...),
    course_code: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Create lecture draft with file upload to Google Drive"""
    
    # Verify course exists and belongs to teacher
    course = session.get(Course, course_code)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_code}' not found"
        )
    
    if course.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create lectures for your own courses"
        )
    
    # Validate file
    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed: PDF, PPTX, TXT"
        )
    
    # Save file temporarily and upload to Drive
    temp_dir = "/tmp/hololearn_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filename = f"temp_{current_user.user_id}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"{course_code}_{title}_{timestamp}{file_ext}"
        
        drive_result = drive_service.upload_file(
            file_path=temp_path,
            filename=drive_filename,
            mime_type=file.content_type
        )
        
        # Create lecture
        lecture = Lecture(
            title=title,
            teacher_id=current_user.user_id,
            course_code=course_code,
            lecture_type=LectureType.PREPARED,
            status=LectureStatus.DRAFT,
            final_content=drive_result['view_link']
        )
        
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        
        return lecture
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lecture: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


# ============================================
# 2: Confirm & Publish (PUBLIC SCHEDULE)
# ============================================

@router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
async def confirm_and_publish_lecture(
    lecture_id: int,
    request_data: ConfirmPublishRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Confirm and publish lecture by reserving a schedule slot
    
    ✅ UPDATED: No schedule ownership check - schedules are public!
    Any teacher can use any available slot.
    """
    
    # Get lecture
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    # Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own lectures"
        )
    
    # Get schedule slot
    schedule = session.get(Schedule, request_data.schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule slot with ID {request_data.schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
    # Verify schedule is available
    if schedule.lecture_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This schedule slot is already reserved"
        )
    
    if schedule.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This schedule slot is not available (status: {schedule.status})"
        )
    
    # Reserve the schedule
    schedule.lecture_id = lecture_id
    schedule.status = "scheduled"
    session.add(schedule)
    
    # Update lecture status
    lecture.status = LectureStatus.COMPLETED
    session.add(lecture)
    
    session.commit()
    session.refresh(lecture)
    session.refresh(schedule)
    
    return ConfirmPublishResponse(
        message="Lecture published and scheduled successfully",
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
# 3: Get Lecture Details for Editing
# ============================================

@router.get("/schedule/{schedule_id}/edit-details", response_model=LectureEditDetails)
async def get_lecture_edit_details_by_schedule(
    schedule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Get lecture details for editing"""
    
    schedule = session.get(Schedule, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
    if schedule.lecture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule has no lecture assigned"
        )
    
    lecture = session.get(Lecture, schedule.lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found"
        )
    
    # ✅ KEPT: Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )
    
    return LectureEditDetails(
        lecture_id=lecture.lecture_id,
        schedule_id=schedule.schedule_id,
        title=lecture.title,
        course_code=lecture.course_code,
        current_file_url=lecture.final_content or "",
        scheduled_date=schedule.date,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        status=schedule.status
    )


# ============================================
# 4: Edit Lecture and Schedule
# ============================================

@router.put("/schedule/{schedule_id}/edit", response_model=EditLectureResponse)
async def edit_lecture_by_schedule(
    schedule_id: int,
    request_data: EditLectureRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Edit lecture title, course code, and/or schedule
    
    ✅ UPDATED: No schedule ownership checks - schedules are public!
    """
    
    current_schedule = session.get(Schedule, schedule_id)
    
    if not current_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    # ✅ REMOVED: schedule.teacher_id check
    
    if current_schedule.lecture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule has no lecture assigned"
        )
    
    lecture = session.get(Lecture, current_schedule.lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found"
        )
    
    # ✅ KEPT: Verify lecture ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )
    
    try:
        # Update title
        if request_data.title is not None:
            lecture.title = request_data.title
        
        # Update course code
        if request_data.course_code is not None and request_data.course_code != lecture.course_code:
            course = session.get(Course, request_data.course_code)
            
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Course '{request_data.course_code}' not found"
                )
            
            if course.teacher_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only assign lectures to your own courses"
                )
            
            lecture.course_code = request_data.course_code
        
        # Handle schedule change
        schedule_changed = False
        final_schedule = current_schedule
        
        if request_data.new_schedule_id and request_data.new_schedule_id != schedule_id:
            new_schedule = session.get(Schedule, request_data.new_schedule_id)
            
            if not new_schedule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"New schedule with ID {request_data.new_schedule_id} not found"
                )
            
            # ✅ REMOVED: new_schedule.teacher_id check (schedules are public!)
            
            # Verify new schedule is available
            if new_schedule.lecture_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The new schedule slot is already reserved"
                )
            
            if new_schedule.status != "available":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The new schedule slot is not available (status: {new_schedule.status})"
                )
            
            # Free old schedule
            current_schedule.lecture_id = None
            current_schedule.status = "available"
            session.add(current_schedule)
            
            # Reserve new schedule
            new_schedule.lecture_id = lecture.lecture_id
            new_schedule.status = "scheduled"
            session.add(new_schedule)
            
            final_schedule = new_schedule
            schedule_changed = True
        
        # Save changes
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        session.refresh(final_schedule)
        
        return EditLectureResponse(
            message="Lecture updated successfully",
            lecture_id=lecture.lecture_id,
            schedule_id=final_schedule.schedule_id,
            lecture_title=lecture.title,
            course_code=lecture.course_code,
            lecture_status=lecture.status.value,
            scheduled_date=final_schedule.date,
            start_time=final_schedule.start_time,
            end_time=final_schedule.end_time,
            schedule_status=final_schedule.status,
            schedule_changed=schedule_changed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lecture: {str(e)}"
        )


# ============================================
# 5: Get All My Lectures
# ============================================

@router.get("/all-my-lectures", response_model=List[FullTimeSlot2])
def get_all_my_lectures(
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """Get ALL lectures created by teacher (scheduled + draft)"""
    
    lectures = session.exec(
        select(Lecture)
        .where(Lecture.teacher_id == current_user.user_id)
        .order_by(Lecture.lecture_id.desc())
    ).all()
    
    result = []
    teacher_name = current_user.full_name or "Unknown"
    
    for lecture in lectures:
        schedules = session.exec(
            select(Schedule)
            .where(
                Schedule.lecture_id == lecture.lecture_id,
                Schedule.status == "scheduled"
            )
            .order_by(Schedule.date, Schedule.start_time)
        ).all()
        
        if schedules:
            for schedule in schedules:
                start_datetime = datetime.combine(schedule.date, schedule.start_time)
                end_datetime = datetime.combine(schedule.date, schedule.end_time)
                
                result.append(
                    FullTimeSlot2(
                        schedule_id=schedule.schedule_id,
                        lecture_id=lecture.lecture_id,
                        course_code=lecture.course_code,
                        lecture_title=lecture.title,
                        teacher_name=teacher_name,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        status=schedule.status
                    )
                )
        else:
            result.append(
                FullTimeSlot2(
                    schedule_id=None,
                    lecture_id=lecture.lecture_id,
                    course_code=lecture.course_code,
                    lecture_title=lecture.title,
                    teacher_name=teacher_name,
                    start_time=None,
                    end_time=None,
                    status=lecture.status.value
                )
            )
    
    return result


# ============================================
# 6: Delete Lecture
# ============================================

@router.delete("/{lecture_id}", response_model=DeleteLectureResponse)
async def delete_lecture(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Delete lecture and free all its schedules"""
    
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own lectures"
        )
    
    # Free all schedules
    schedules = session.exec(
        select(Schedule).where(Schedule.lecture_id == lecture_id)
    ).all()
    
    for schedule in schedules:
        schedule.lecture_id = None
        schedule.status = "available"
        session.add(schedule)
    
    # Delete lecture
    session.delete(lecture)
    session.commit()
    
    return DeleteLectureResponse(
        message="Lecture deleted successfully"
    )