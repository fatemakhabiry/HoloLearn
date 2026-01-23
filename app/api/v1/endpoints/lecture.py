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
    # if lecture.status != LectureStatus.DRAFT:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Lecture is already {lecture.status}. Can only publish draft lectures."
    #     )
    
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
# Get Lecture Details by Schedule ID
# ============================================

@router.get("/schedule/{schedule_id}/edit-details", response_model=LectureEditDetails)
async def get_lecture_edit_details_by_schedule(
    schedule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Get lecture details for editing using schedule_id
    
    Returns all current values to pre-fill the edit form
    """
    
    schedule = session.get(Schedule, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    if schedule.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own schedules"
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
            detail=f"Lecture not found"
        )
    
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
# Update Lecture and Schedule
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
    
    This is a SIMPLIFIED version that accepts JSON (not multipart/form-data)
    and only updates: title, course_code, and schedule
    
    Request (JSON):
    PUT /api/lectures/schedule/{schedule_id}/edit
    
    Body:
    {
        "title": "Updated Title",
        "course_code": "CS102",
        "new_schedule_id": 10
    }
    
    All fields are optional - only send what you want to update.
    
    Response:
    {
        "message": "Lecture updated successfully",
        "lecture_id": 3,
        "schedule_id": 10,
        "lecture_title": "Updated Title",
        "course_code": "CS102",
        "lecture_status": "completed",
        "scheduled_date": "2026-01-23",
        "start_time": "18:00:00",
        "end_time": "19:30:00",
        "schedule_status": "scheduled",
        "schedule_changed": true
    }
    """
    
    # ============================================
    # PART 1: Validate Current Schedule
    # ============================================
    
    current_schedule = session.get(Schedule, schedule_id)
    
    if not current_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    if current_schedule.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own schedules"
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
    
    # ============================================
    # PART 2: Update Lecture Details
    # ============================================
    
    try:
        # Update title
        if request_data.title is not None:
            lecture.title = request_data.title
            print(f"✅ Updated title: {lecture.title}")
        
        # Update course code
        if request_data.course_code is not None and request_data.course_code != lecture.course_code:
            # Verify new course exists
            course = session.get(Course, request_data.course_code)
            
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Course '{request_data.course_code}' not found"
                )
            
            # Verify course belongs to teacher
            if course.teacher_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only assign lectures to your own courses"
                )
            
            lecture.course_code = request_data.course_code
            print(f"✅ Updated course code: {lecture.course_code}")
        
        # ============================================
        # PART 3: Handle Schedule Change
        # ============================================
        
        schedule_changed = False
        final_schedule = current_schedule
        
        if request_data.new_schedule_id and request_data.new_schedule_id != schedule_id:
            # Teacher wants to change schedule
            
            # Get new schedule
            new_schedule = session.get(Schedule, request_data.new_schedule_id)
            
            if not new_schedule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"New schedule with ID {request_data.new_schedule_id} not found"
                )
            
            # Verify new schedule belongs to teacher
            if new_schedule.teacher_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The new schedule slot does not belong to you"
                )
            
            # Verify new schedule is available
            if new_schedule.lecture_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The new schedule slot is already reserved for another lecture"
                )
            
            # Verify new schedule status
            if new_schedule.status != "available":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The new schedule slot is not available (status: {new_schedule.status})"
                )
            
            # FREE old schedule
            current_schedule.lecture_id = None
            current_schedule.status = "available"
            session.add(current_schedule)
            
            print(f"✅ Freed old schedule {schedule_id}: lecture_id=NULL, status=available")
            
            # RESERVE new schedule
            new_schedule.lecture_id = lecture.lecture_id
            new_schedule.status = "scheduled"
            session.add(new_schedule)
            
            print(f"✅ Reserved new schedule {request_data.new_schedule_id}: lecture_id={lecture.lecture_id}, status=scheduled")
            
            # Update which schedule to return
            final_schedule = new_schedule
            schedule_changed = True
        
        # ============================================
        # PART 4: Save All Changes
        # ============================================
        
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        session.refresh(final_schedule)
        
        print(f"✅ Lecture {lecture.lecture_id} updated successfully")
        print(f"   - Title: {lecture.title}")
        print(f"   - Course Code: {lecture.course_code}")
        print(f"   - Schedule changed: {schedule_changed}")
        print(f"   - Final schedule ID: {final_schedule.schedule_id}")
        
        # ============================================
        # PART 5: Return Response
        # ============================================
        
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

@router.get("/all-my-lectures", response_model=List[FullTimeSlot2])
def get_all_my_lectures(
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Get ALL lectures created by the current teacher
    
    Returns TWO types of lectures:
    
    1. SCHEDULED LECTURES (status = "completed"):
       - Has schedule_id, date, start_time, end_time
       - status = "scheduled" (from schedule.status)
    
    2. DRAFT LECTURES (status = "draft"):
       - schedule_id = None
       - date = None
       - start_time = None
       - end_time = None
       - status = "draft" (from lecture.status)
    
    Logic:
    - Query all lectures by teacher_id
    - For each lecture, try to find its schedule
    - If schedule exists → populate schedule fields
    - If no schedule → set schedule fields to None
    
    Response Example:
    [
        {
            "schedule_id": 3,
            "lecture_id": 5,
            "course_code": "AI201",
            "lecture_title": "knn",
            "teacher_name": "Dr. Ahmed",
            "date": "2026-01-20",
            "start_time": "2026-01-20T14:00:00",
            "end_time": "2026-01-20T15:30:00",
            "status": "scheduled"
        },
        {
            "schedule_id": null,
            "lecture_id": 8,
            "course_code": "AI201",
            "lecture_title": "neural networks",
            "teacher_name": "Dr. Ahmed",
            "date": null,
            "start_time": null,
            "end_time": null,
            "status": "draft"
        }
    ]
    """
    
    # ============================================
    # STEP 1: Get ALL lectures by teacher
    # ============================================
    
    lectures = session.exec(
        select(Lecture)
        .where(Lecture.teacher_id == current_user.user_id)
        .order_by(Lecture.lecture_id.desc())  # Newest first
    ).all()
    
    result = []
    
    # ============================================
    # STEP 2: Get teacher name (once)
    # ============================================
    
    teacher_name = current_user.full_name or "Unknown"
    
    # ============================================
    # STEP 3: Process each lecture
    # ============================================
    
    for lecture in lectures:
        
        # Try to find schedule(s) for this lecture
        schedules = session.exec(
            select(Schedule)
            .where(
                Schedule.lecture_id == lecture.lecture_id,
                Schedule.status == "scheduled"
            )
            .order_by(Schedule.date, Schedule.start_time)
        ).all()
        
        # ============================================
        # Case A: Lecture HAS schedule(s)
        # ============================================
        
        if schedules:
            # Return one entry for EACH schedule
            # (same lecture can be scheduled multiple times)
            
            for schedule in schedules:
                # Convert time to datetime
                start_datetime = datetime.combine(
                    schedule.date,
                    schedule.start_time
                )
                
                end_datetime = datetime.combine(
                    schedule.date,
                    schedule.end_time
                )
                
                result.append(
                    FullTimeSlot2(
                        schedule_id=schedule.schedule_id,
                        lecture_id=lecture.lecture_id,
                        course_code=lecture.course_code,
                        lecture_title=lecture.title,
                        teacher_name=teacher_name,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        status=schedule.status  # "scheduled"
                    )
                )
        
        # ============================================
        # Case B: Lecture has NO schedule (DRAFT)
        # ============================================
        
        else:
            # Return lecture with null schedule fields
            
            result.append(
                FullTimeSlot2(
                    schedule_id=None,              # ← Null
                    lecture_id=lecture.lecture_id,
                    course_code=lecture.course_code,
                    lecture_title=lecture.title,
                    teacher_name=teacher_name,
                    start_time=None,               # ← Null
                    end_time=None,                 # ← Null
                    status=lecture.status.value    # "draft" or "completed"
                )
            )
    
    return result

# ============================================
# Delete Lecture Endpoint
# ============================================

@router.delete("/{lecture_id}", response_model=DeleteLectureResponse)
async def delete_lecture(
    lecture_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher)
):
    """
    Delete a lecture and free all its schedules
    
    This endpoint:
    1. Finds the lecture by ID
    2. Verifies the teacher owns the lecture
    3. Finds all schedules associated with this lecture
    4. Frees all schedules (sets lecture_id=NULL, status="available")
    5. Deletes the lecture record
    
    Important:
    - Schedules are NOT deleted (they're reusable resources)
    - Schedules are just freed for future use
    - The lecture is permanently deleted
    
    Request:
    DELETE /api/lectures/{lecture_id}
    
    Response:
    {
        "message": "Lecture deleted successfully"
    }
    """
    
    # ============================================
    # STEP 1: Get and Validate Lecture
    # ============================================
    
    lecture = session.get(Lecture, lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with ID {lecture_id} not found"
        )
    
    # Verify ownership
    if lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own lectures"
        )
    
    
    # ============================================
    # STEP 2: Find All Schedules for This Lecture
    # ============================================
    
    schedules = session.exec(
        select(Schedule)
        .where(Schedule.lecture_id == lecture_id)
    ).all()
        
    # ============================================
    # STEP 3: Free All Schedules
    # ============================================
    
    for schedule in schedules:        
        # Free the schedule
        schedule.lecture_id = None
        schedule.status = "available"
        session.add(schedule)
        
        print(f"✅ Freed schedule {schedule.schedule_id}: lecture_id=NULL, status=available")
    
    # ============================================
    # STEP 4: Delete the Lecture
    # ============================================
    
    session.delete(lecture)
    session.commit()
    

    # ============================================
    # STEP 5: Return Response
    # ============================================
    
    return DeleteLectureResponse(
        message="Lecture deleted successfully",
        # lecture_id=lecture_id,
        # lecture_title=lecture_title,
        # schedules_freed=len(freed_schedule_ids),
        # freed_schedule_ids=freed_schedule_ids
    )