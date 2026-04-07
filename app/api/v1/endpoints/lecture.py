# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
# from sqlmodel import Session, select
# from typing import Optional ,List
# from datetime import time , date,datetime
# from app.services.google_drive import drive_service
# import os

# from app.core.database import get_session
# from app.models.lecture import Lecture, LectureType, LectureStatus , LecturePublic
# from app.models.schedule import Schedule, SchedulePublic, ScheduleCreate
# from app.models.user import User, UserRole
# from app.models.course import Course
# from app.api.deps import get_current_user,get_current_teacher
# from app.schemas.schedule_schemas import (ConfirmPublishResponse,
#  ConfirmPublishRequest,
#  LectureEditDetails,
#  EditLectureResponse,
#  FullTimeSlot2,
#  EditLectureRequest,
#  DeleteLectureResponse
# )

# router = APIRouter()



# # ============================================
# # 1: Create Draft Lecture
# # ============================================

# @router.post("/create-draft", response_model=LecturePublic, status_code=status.HTTP_201_CREATED)
# async def create_lecture_draft(
#     title: str = Form(...),
#     course_code: str = Form(...),
#     file: UploadFile = File(...),
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """Create lecture draft with file upload to Google Drive"""
    
#     # Verify course exists and belongs to teacher
#     course = session.get(Course, course_code)
    
#     if not course:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Course '{course_code}' not found"
#         )
    
#     if course.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only create lectures for your own courses"
#         )
    
#     # Validate file
#     ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
#     file_ext = os.path.splitext(file.filename)[1].lower()
    
#     if file_ext not in ALLOWED_EXTENSIONS:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"File type {file_ext} not allowed. Allowed: PDF, PPTX, TXT"
#         )
    
#     # Save file temporarily and upload to Drive
#     temp_dir = "/tmp/hololearn_uploads"
#     os.makedirs(temp_dir, exist_ok=True)
    
#     temp_filename = f"temp_{current_user.user_id}_{file.filename}"
#     temp_path = os.path.join(temp_dir, temp_filename)
    
#     try:
#         with open(temp_path, "wb") as f:
#             content = await file.read()
#             f.write(content)
        
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         drive_filename = f"{course_code}_{title}_{timestamp}{file_ext}"
        
#         drive_result = drive_service.upload_file(
#             file_path=temp_path,
#             filename=drive_filename,
#             mime_type=file.content_type
#         )
        
#         # Create lecture
#         lecture = Lecture(
#             title=title,
#             teacher_id=current_user.user_id,
#             course_code=course_code,
#             lecture_type=LectureType.PREPARED,
#             status=LectureStatus.DRAFT,
#             final_content=drive_result['view_link']
#         )
        
#         session.add(lecture)
#         session.commit()
#         session.refresh(lecture)
        
#         return lecture
        
#     except Exception as e:
#         session.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create lecture: {str(e)}"
#         )
#     finally:
#         if os.path.exists(temp_path):
#             try:
#                 os.remove(temp_path)
#             except:
#                 pass


# # ============================================
# # 2: Confirm & Publish (PUBLIC SCHEDULE)
# # ============================================

# @router.post("/{lecture_id}/confirm-and-publish", response_model=ConfirmPublishResponse)
# async def confirm_and_publish_lecture(
#     lecture_id: int,
#     request_data: ConfirmPublishRequest,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """
#     Confirm and publish lecture by reserving a schedule slot
    
#     ✅ UPDATED: No schedule ownership check - schedules are public!
#     Any teacher can use any available slot.
#     """
    
#     # Get lecture
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     # Verify lecture ownership
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only publish your own lectures"
#         )
    
#     # Get schedule slot
#     schedule = session.get(Schedule, request_data.schedule_id)
    
#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule slot with ID {request_data.schedule_id} not found"
#         )
    
#     # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
#     # Verify schedule is available
#     if schedule.lecture_id is not None:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="This schedule slot is already reserved"
#         )
    
#     if schedule.status != "available":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"This schedule slot is not available (status: {schedule.status})"
#         )
    
#     # Reserve the schedule
#     schedule.lecture_id = lecture_id
#     schedule.status = "scheduled"
#     session.add(schedule)
    
#     # Update lecture status
#     lecture.status = LectureStatus.COMPLETED
#     session.add(lecture)
    
#     session.commit()
#     session.refresh(lecture)
#     session.refresh(schedule)
    
#     return ConfirmPublishResponse(
#         message="Lecture published and scheduled successfully",
#         lecture_id=lecture.lecture_id,
#         schedule_id=schedule.schedule_id,
#         lecture_title=lecture.title,
#         course_code=lecture.course_code,
#         lecture_status=lecture.status.value,
#         schedule_status=schedule.status,
#         scheduled_date=schedule.date,
#         start_time=schedule.start_time,
#         end_time=schedule.end_time
#     )


# # ============================================
# # 3: Get Lecture Details for Editing
# # ============================================

# @router.get("/schedule/{schedule_id}/edit-details", response_model=LectureEditDetails)
# async def get_lecture_edit_details_by_schedule(
#     schedule_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """Get lecture details for editing"""
    
#     schedule = session.get(Schedule, schedule_id)
    
#     if not schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule with ID {schedule_id} not found"
#         )
    
#     # ✅ REMOVED: schedule.teacher_id check (schedules are public!)
    
#     if schedule.lecture_id is None:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This schedule has no lecture assigned"
#         )
    
#     lecture = session.get(Lecture, schedule.lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Lecture not found"
#         )
    
#     # ✅ KEPT: Verify lecture ownership
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only edit your own lectures"
#         )
    
#     return LectureEditDetails(
#         lecture_id=lecture.lecture_id,
#         schedule_id=schedule.schedule_id,
#         title=lecture.title,
#         course_code=lecture.course_code,
#         current_file_url=lecture.final_content or "",
#         scheduled_date=schedule.date,
#         start_time=schedule.start_time,
#         end_time=schedule.end_time,
#         status=schedule.status
#     )


# # ============================================
# # 4: Edit Lecture and Schedule
# # ============================================

# @router.put("/schedule/{schedule_id}/edit", response_model=EditLectureResponse)
# async def edit_lecture_by_schedule(
#     schedule_id: int,
#     request_data: EditLectureRequest,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """
#     Edit lecture title, course code, and/or schedule
    
#     ✅ UPDATED: No schedule ownership checks - schedules are public!
#     """
    
#     current_schedule = session.get(Schedule, schedule_id)
    
#     if not current_schedule:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule with ID {schedule_id} not found"
#         )
    
#     # ✅ REMOVED: schedule.teacher_id check
    
#     if current_schedule.lecture_id is None:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This schedule has no lecture assigned"
#         )
    
#     lecture = session.get(Lecture, current_schedule.lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Lecture not found"
#         )
    
#     # ✅ KEPT: Verify lecture ownership
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only edit your own lectures"
#         )
    
#     try:
#         # Update title
#         if request_data.title is not None:
#             lecture.title = request_data.title
        
#         # Update course code
#         if request_data.course_code is not None and request_data.course_code != lecture.course_code:
#             course = session.get(Course, request_data.course_code)
            
#             if not course:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail=f"Course '{request_data.course_code}' not found"
#                 )
            
#             if course.teacher_id != current_user.user_id:
#                 raise HTTPException(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     detail="You can only assign lectures to your own courses"
#                 )
            
#             lecture.course_code = request_data.course_code
        
#         # Handle schedule change
#         schedule_changed = False
#         final_schedule = current_schedule
        
#         if request_data.new_schedule_id and request_data.new_schedule_id != schedule_id:
#             new_schedule = session.get(Schedule, request_data.new_schedule_id)
            
#             if not new_schedule:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail=f"New schedule with ID {request_data.new_schedule_id} not found"
#                 )
            
#             # ✅ REMOVED: new_schedule.teacher_id check (schedules are public!)
            
#             # Verify new schedule is available
#             if new_schedule.lecture_id is not None:
#                 raise HTTPException(
#                     status_code=status.HTTP_409_CONFLICT,
#                     detail="The new schedule slot is already reserved"
#                 )
            
#             if new_schedule.status != "available":
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"The new schedule slot is not available (status: {new_schedule.status})"
#                 )
            
#             # Free old schedule
#             current_schedule.lecture_id = None
#             current_schedule.status = "available"
#             session.add(current_schedule)
            
#             # Reserve new schedule
#             new_schedule.lecture_id = lecture.lecture_id
#             new_schedule.status = "scheduled"
#             session.add(new_schedule)
            
#             final_schedule = new_schedule
#             schedule_changed = True
        
#         # Save changes
#         session.add(lecture)
#         session.commit()
#         session.refresh(lecture)
#         session.refresh(final_schedule)
        
#         return EditLectureResponse(
#             message="Lecture updated successfully",
#             lecture_id=lecture.lecture_id,
#             schedule_id=final_schedule.schedule_id,
#             lecture_title=lecture.title,
#             course_code=lecture.course_code,
#             lecture_status=lecture.status.value,
#             scheduled_date=final_schedule.date,
#             start_time=final_schedule.start_time,
#             end_time=final_schedule.end_time,
#             schedule_status=final_schedule.status,
#             schedule_changed=schedule_changed
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         session.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update lecture: {str(e)}"
#         )


# # ============================================
# # 5: Get All My Lectures
# # ============================================

# @router.get("/all-my-lectures", response_model=List[FullTimeSlot2])
# def get_all_my_lectures(
#     current_user: User = Depends(get_current_teacher),
#     session: Session = Depends(get_session)
# ):
#     """Get ALL lectures created by teacher (scheduled + draft)"""
    
#     lectures = session.exec(
#         select(Lecture)
#         .where(Lecture.teacher_id == current_user.user_id)
#         .order_by(Lecture.lecture_id.desc())
#     ).all()
    
#     result = []
#     teacher_name = current_user.full_name or "Unknown"
    
#     for lecture in lectures:
#         schedules = session.exec(
#             select(Schedule)
#             .where(
#                 Schedule.lecture_id == lecture.lecture_id,
#                 Schedule.status == "scheduled"
#             )
#             .order_by(Schedule.date, Schedule.start_time)
#         ).all()
        
#         if schedules:
#             for schedule in schedules:
#                 start_datetime = datetime.combine(schedule.date, schedule.start_time)
#                 end_datetime = datetime.combine(schedule.date, schedule.end_time)
                
#                 result.append(
#                     FullTimeSlot2(
#                         schedule_id=schedule.schedule_id,
#                         lecture_id=lecture.lecture_id,
#                         course_code=lecture.course_code,
#                         lecture_title=lecture.title,
#                         teacher_name=teacher_name,
#                         start_time=start_datetime,
#                         end_time=end_datetime,
#                         status=schedule.status
#                     )
#                 )
#         else:
#             result.append(
#                 FullTimeSlot2(
#                     schedule_id=None,
#                     lecture_id=lecture.lecture_id,
#                     course_code=lecture.course_code,
#                     lecture_title=lecture.title,
#                     teacher_name=teacher_name,
#                     start_time=None,
#                     end_time=None,
#                     status=lecture.status.value
#                 )
#             )
    
#     return result


# # ============================================
# # 6: Delete Lecture
# # ============================================

# @router.delete("/{lecture_id}", response_model=DeleteLectureResponse)
# async def delete_lecture(
#     lecture_id: int,
#     session: Session = Depends(get_session),
#     current_user: User = Depends(get_current_teacher)
# ):
#     """Delete lecture and free all its schedules"""
    
#     lecture = session.get(Lecture, lecture_id)
    
#     if not lecture:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Lecture with ID {lecture_id} not found"
#         )
    
#     if lecture.teacher_id != current_user.user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only delete your own lectures"
#         )
    
#     # Free all schedules
#     schedules = session.exec(
#         select(Schedule).where(Schedule.lecture_id == lecture_id)
#     ).all()
    
#     for schedule in schedules:
#         schedule.lecture_id = None
#         schedule.status = "available"
#         session.add(schedule)
    
#     # Delete lecture
#     session.delete(lecture)
#     session.commit()
    
#     return DeleteLectureResponse(
#         message="Lecture deleted successfully"
#     )

# app/api/v1/endpoints/lecture.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, select
from typing import Optional, List
from datetime import time, date, datetime
from pathlib import Path
from arq import create_pool
from arq.connections import RedisSettings
import os

from app.core.config import settings
from app.core.database import get_session
from app.models.lecture import (
    Lecture, LectureType, LectureStatus, LecturePublic,
    LecturePipelineTriggerResponse
)
from app.models.teacher import Teacher
from app.models.schedule import Schedule, SchedulePublic, ScheduleCreate
from app.models.user import User, UserRole
from app.models.course import Course
from app.api.deps import get_current_user, get_current_teacher
from app.schemas.schedule_schemas import (
    ConfirmPublishResponse,
    ConfirmPublishRequest,
    LectureEditDetails,
    EditLectureResponse,
    FullTimeSlot2,
    EditLectureRequest,
    DeleteLectureResponse
)
from app.services.google_drive import drive_service

router = APIRouter()


# ============================================
# 0: Create GENERATED Lecture (pipeline flow)
# ============================================

class GeneratedLectureCreate(BaseModel):
    """Request body for creating a pipeline-generated lecture."""
    title: str
    course_code: str
    script_path: Optional[str] = None   # can be set now or later via set-script-path


@router.post(
    "/create-generated",
    response_model=LecturePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_generated_lecture(
    body: GeneratedLectureCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a GENERATED lecture draft for the avatar pipeline.

    No file upload, no Google Drive — just creates the DB row.
    Upstream module (or test client) can set script_path here or later via
    PATCH /{lecture_id}/set-script-path.

    Requires: logged-in teacher who owns the course.
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create lectures",
        )

    course = session.get(Course, body.course_code)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{body.course_code}' not found",
        )
    if course.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create lectures for your own courses",
        )

    lecture = Lecture(
        title=body.title,
        teacher_id=current_user.user_id,
        course_code=body.course_code,
        lecture_type=LectureType.GENERATED,
        status=LectureStatus.DRAFT,
        script_path=body.script_path,
    )
    session.add(lecture)
    session.commit()
    session.refresh(lecture)
    return lecture


# ── Set / update script_path ───────────────────────────────────────────────────

class SetScriptPathRequest(BaseModel):
    script_path: str


@router.patch(
    "/{lecture_id}/set-script-path",
    response_model=LecturePublic,
)
async def set_lecture_script_path(
    lecture_id: int,
    body: SetScriptPathRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Set (or update) the script_path on a GENERATED lecture.

    Called by the upstream extraction/LLM module after it writes the .txt
    script to disk.  Also useful for manual testing.
    """
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture not found")
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your lecture")

    if not Path(body.script_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Script file not found on disk: {body.script_path}",
        )

    lecture.script_path = body.script_path
    session.add(lecture)
    session.commit()
    session.refresh(lecture)
    return lecture


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

    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed: PDF, PPTX, TXT"
        )

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

    lecture = session.get(Lecture, lecture_id)

    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )

    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own lectures"
        )

    schedule = session.get(Schedule, request_data.schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule slot with ID {request_data.schedule_id} not found"
        )

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

    schedule.lecture_id = lecture_id
    schedule.status = "scheduled"
    session.add(schedule)

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

    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )

    return LectureEditDetails(
        lecture_id=lecture.lecture_id,
        title=lecture.title,
        course_code=lecture.course_code,
        schedule_id=schedule.schedule_id,
        scheduled_date=schedule.date,
        start_time=schedule.start_time,
        end_time=schedule.end_time
    )


# ============================================
# 4: Edit Lecture Details
# ============================================

@router.put("/schedule/{schedule_id}/edit-details", response_model=EditLectureResponse)
async def edit_lecture_details(
    schedule_id: int,
    request_data: EditLectureRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """Edit lecture title, course, or reschedule"""

    current_schedule = session.get(Schedule, schedule_id)

    if not current_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

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

    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own lectures"
        )

    try:
        if request_data.title is not None:
            lecture.title = request_data.title

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

        schedule_changed = False
        final_schedule = current_schedule

        if request_data.new_schedule_id and request_data.new_schedule_id != schedule_id:
            new_schedule = session.get(Schedule, request_data.new_schedule_id)

            if not new_schedule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"New schedule with ID {request_data.new_schedule_id} not found"
                )

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

            current_schedule.lecture_id = None
            current_schedule.status = "available"
            session.add(current_schedule)

            new_schedule.lecture_id = lecture.lecture_id
            new_schedule.status = "scheduled"
            session.add(new_schedule)

            final_schedule = new_schedule
            schedule_changed = True

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

    schedules = session.exec(
        select(Schedule).where(Schedule.lecture_id == lecture_id)
    ).all()

    for schedule in schedules:
        schedule.lecture_id = None
        schedule.status = "available"
        session.add(schedule)

    session.delete(lecture)
    session.commit()

    return DeleteLectureResponse(
        message="Lecture deleted successfully"
    )


# ============================================
# 7: Trigger Pipeline  ← NEW
# ============================================

@router.post(
    "/{lecture_id}/trigger-pipeline",
    response_model=LecturePipelineTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_lecture_pipeline(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger avatar video generation for a GENERATED lecture.

    Called by upstream extraction/LLM module after:
    - Lecture row exists in DB with lecture_type = GENERATED
    - Script .txt has been written to disk
    - lecture.script_path is set on the DB row

    This endpoint validates everything then enqueues the job.
    Returns 202 immediately — generation runs in the background (5–25 min).
    Poll GET /lecture/{id}/video or check lecture status to know when done.
    """

    # ── Check 1: Lecture exists ────────────────────────────────────
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture {lecture_id} not found"
        )

    # ── Check 2: Caller owns the lecture ──────────────────────────
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only trigger generation for your own lectures"
        )

    # ── Check 3: Must be GENERATED type ───────────────────────────
    # PREPARED lectures use Google Drive — they don't go through the pipeline
    if lecture.lecture_type != LectureType.GENERATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only GENERATED lectures can use the pipeline. "
                   f"This lecture is type: {lecture.lecture_type.value}"
        )

    # ── Check 4: Teacher onboarding must be ready ──────────────────
    # preprocess_image.py must have succeeded before generation can start
    teacher = session.get(Teacher, lecture.teacher_id)
    if not teacher or teacher.onboarding_status != "ready":
        current_status = teacher.onboarding_status if teacher else "no teacher record"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Teacher onboarding is not complete. "
                   f"Current onboarding_status: '{current_status}'. "
                   f"Must be 'ready' before triggering generation."
        )

    # ── Check 5: script_path must be set ──────────────────────────
    if not lecture.script_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lecture.script_path is not set. "
                   "Upstream module must write the script and set script_path before calling this endpoint."
        )

    # ── Check 6: Script file must exist on disk ────────────────────
    if not Path(lecture.script_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Script file not found on disk: {lecture.script_path}"
        )

    # ── Check 7: Not already running or completed ──────────────────
    if lecture.status in (LectureStatus.GENERATING, LectureStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot trigger pipeline. Lecture status is already '{lecture.status.value}'. "
                   f"Only DRAFT or FAILED lectures can be re-triggered."
        )

    # ── All checks passed — enqueue the job ───────────────────────
    # ARQ enqueues to Redis. The ARQ worker process picks it up
    # and runs run_generation(lecture_id). MAX_JOBS=1 ensures only
    # one generation runs at a time on the single GPU.
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await redis.enqueue_job("run_generation", lecture_id)
        await redis.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue generation job: {str(e)}. "
                   f"Is Redis running at {settings.REDIS_URL}?"
        )

    return LecturePipelineTriggerResponse(
        lecture_id=lecture_id,
        status="queued",
        message=f"Video generation job queued. "
                f"Poll GET /lecture/{lecture_id}/status or check lecture.status for progress."
    )


# ============================================
# 8: Stream Generated Video  ← NEW
# ============================================

@router.get("/{lecture_id}/video")
async def stream_lecture_video(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Stream the generated avatar MP4 for a completed lecture.

    Returns the video file directly — suitable for mobile playback.

    Status codes:
    - 200: Video streaming
    - 404: Lecture not found
    - 409: Video not ready yet (check lecture.status for current state)
    - 410: Video was completed but file no longer exists on disk
    """

    # Lecture must exist
    lecture = session.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture {lecture_id} not found"
        )

    # Generation must be finished
    if lecture.status != LectureStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Video not ready. Current status: '{lecture.status.value}'. "
                   f"Wait for status to become 'completed'."
        )

    # output_video_path must be recorded
    if not lecture.output_video_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lecture is marked completed but no output_video_path is recorded."
        )

    # File must exist on disk
    video_path = Path(lecture.output_video_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Video file no longer available on disk. It may have been deleted."
        )

    # Stream the MP4 — FastAPI handles range requests automatically
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"lecture_{lecture_id}.mp4"
    )