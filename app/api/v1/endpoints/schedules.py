from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, time, date
from app.schemas.schedule_schemas import TimeSlot , DateAvailability,FullTimeSlot,CancelScheduleResponse,FullTimeSlot2
from app.models.user import User, UserRole
from app.models.lecture import Lecture


from app.core.database import get_session
from app.api.deps import (
    get_current_teacher,
    get_current_user

)

from app.models.user import User
from app.models.schedule import (
    Schedule,
    ScheduleCreate,
    SchedulePublic
)
from app.models.teacher import Teacher

router = APIRouter()


# =============== Helper Functions ===============

def check_schedule_conflict(
    session: Session,
    teacher_id: int,
    target_date: date,
    start_time: time,
    end_time: time,
    exclude_schedule_id: Optional[int] = None
) -> bool:
    """
    Check if teacher has conflicting schedules on the same date.
    Returns True if conflict exists.
    """
    query = select(Schedule).where(
        Schedule.teacher_id == teacher_id,
        Schedule.date == target_date,  # Same date
        Schedule.status != "cancelled",
        # Time overlap check
        Schedule.start_time < end_time,
        Schedule.end_time > start_time
    )
    
    if exclude_schedule_id:
        query = query.where(Schedule.schedule_id != exclude_schedule_id)
    
    conflicts = session.exec(query).all()
    return len(conflicts) > 0


def validate_schedule_times(target_date: date, start_time: time, end_time: time):
    """Validate schedule date and times"""
    
    if target_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule in the past"
        )
    
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    duration_minutes = end_minutes - start_minutes
    
    if duration_minutes > 240:  # 4 hours
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration cannot exceed 4 hours"
        )
    
    if duration_minutes < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration must be at least 30 minutes"
        )

  
# =============== Endpoints ===============

@router.post("/", response_model=SchedulePublic, status_code=status.HTTP_201_CREATED)
def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new schedule slot (Admin only)
    
    ✅ UPDATED: Uses UserRole.ADMIN check instead of separate admin dependency
    
    Admins create public schedule slots that any teacher can use.
    
    Request Body:
    {
        "start_time": "10:00:00",
        "end_time": "11:30:00",
        "date": "2025-01-20",
        "status": "available"
    }
    """
    
    # ✅ Check user role
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create schedules"
        )
    
    # Validate times
    validate_schedule_times(
        schedule_data.date,
        schedule_data.start_time,
        schedule_data.end_time
    )
    
    # Create schedule
    schedule = Schedule(
        created_by_user_id=current_user.user_id,  # ✅ Admin who created it
        lecture_id=None,  # Empty slot
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        date=schedule_data.date,
        status="available"  # Always start as available
    )
    
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    
    return schedule


@router.get("/available-slots/{target_date}", response_model=DateAvailability)
def get_date_availability(
    target_date: date,
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Get available time slots for a specific date (PUBLIC)
    
    ✅ UPDATED: No created_by_user_id filter - shows ALL available slots
    
    Returns ALL available slots for any teacher to use.
    
    Response:
    {
        "date": "2025-01-20",
        "available_slots": [
            {
                "schedule_id": 100,
                "start_time": "10:00:00",
                "end_time": "11:30:00",
                "status": "available"
            }
        ]
    }
    """
    
    if target_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check availability for past dates"
        )
    
    # ✅ No created_by_user_id filter - public slots!
    schedules = session.exec(
        select(Schedule).where(
            Schedule.date == target_date,
            Schedule.lecture_id.is_(None),  # Not reserved
            Schedule.status == "available"
        ).order_by(Schedule.start_time)
    ).all()
    
    available_slots = []
    for schedule in schedules:
        available_slots.append(
            TimeSlot(
                schedule_id=schedule.schedule_id,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                status=schedule.status
            )
        )
    
    return DateAvailability(
        date=target_date,
        available_slots=available_slots
    )


@router.get("/my-scheduled-lectures", response_model=List[FullTimeSlot])
def get_my_scheduled_lectures(
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Get all scheduled lectures for the current teacher (from today forward)
    
    ✅ FIXED:
    1. Removed admin_id filter (doesn't exist anymore)
    2. Query by lecture.teacher_id instead
    3. Fixed teacher name retrieval
    
    Returns lectures with:
    - Course code (from lecture table)
    - Lecture title (from lecture table)
    - Teacher name (from user table)
    - Date and time
    - Schedule ID for edit/cancel
    
    Response:
    [
        {
            "schedule_id": 1,
            "lecture_id": 5,
            "course_code": "CS101",
            "lecture_title": "Intro to Computing",
            "teacher_name": "Dr. Ahmed",
            "date": "2025-01-20",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "status": "scheduled"
        }
    ]
    """
    
    today = date.today()
    
    # ✅ FIXED: Query schedules by lecture ownership, not schedule ownership
    schedules = session.exec(
        select(Schedule)
        .join(Lecture, Schedule.lecture_id == Lecture.lecture_id)  # ✅ Join with lectures
        .where(
            Lecture.teacher_id == current_user.user_id,  # ✅ Filter by lecture owner
            Schedule.date >= today,
            Schedule.lecture_id.isnot(None),
            Schedule.status == "scheduled"
        )
        .order_by(Schedule.date, Schedule.start_time)
    ).all()
    
    result = []
    
    for schedule in schedules:
        # Get lecture via relationship
        lecture = schedule.lecture
        
        if not lecture:
            continue  # Skip if lecture deleted
        
        # ✅ FIXED: Get teacher name from current_user (they're the teacher!)
        teacher_name = current_user.full_name or "Unknown"
        
        result.append(
            FullTimeSlot(
                schedule_id=schedule.schedule_id,
                lecture_id=lecture.lecture_id,  # ✅ Added lecture_id
                course_code=lecture.course_code,
                lecture_title=lecture.title,
                teacher_name=teacher_name,
                date=schedule.date,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                status=schedule.status
            )
        )
    
    return result

@router.patch("/{schedule_id}/cancel", response_model=CancelScheduleResponse)
def cancel_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Cancel a schedule (free the slot)
    
    ✅ UPDATED: Checks lecture ownership, not schedule ownership
    
    Teacher can cancel any schedule that has their lecture assigned.
    """
    
    schedule = session.get(Schedule, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )
    
    if schedule.lecture_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule has no lecture to cancel"
        )
    
    # ✅ Check lecture ownership, not schedule ownership
    from app.models.lecture import Lecture
    lecture = session.get(Lecture, schedule.lecture_id)
    
    if lecture and lecture.teacher_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel schedules with your own lectures"
        )
    
    previous_lecture_id = schedule.lecture_id
    
    # Free the slot
    schedule.lecture_id = None
    schedule.status = "available"
    
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    
    return CancelScheduleResponse(
        message="Schedule cancelled successfully",
        schedule_id=schedule.schedule_id,
        status=schedule.status,
        previous_lecture_id=previous_lecture_id
    )


