from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, time, date
from app.schemas.schedule_schemas import TimeSlot , DateAvailability,FullTimeSlot,CancelScheduleResponse,FullTimeSlot2


from app.core.database import get_session
from app.api.deps import (
    get_current_teacher,

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


def validate_schedule_times(
    target_date: date,
    start_time: time,
    end_time: time
):
    """Validate schedule date and times"""
    
    # Date must not be in the past
    if target_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule in the past"
        )
    
    # End time must be after start time
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    # Calculate duration in hours
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    duration_minutes = end_minutes - start_minutes
    
    # Maximum 4 hours
    if duration_minutes > 240:  # 4 hours = 240 minutes
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration cannot exceed 4 hours"
        )
    
    # Minimum 30 minutes
    if duration_minutes < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule duration must be at least 30 minutes"
        )

  
# =============== Endpoints ===============

@router.post("/", response_model=SchedulePublic, status_code=status.HTTP_201_CREATED)
def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Create a new schedule (Teacher only)
    
    Request Body:
    {
        "start_time": "10:00:00",
        "end_time": "11:30:00",
        "date": "2025-01-20",
        "status": "scheduled",
        "lecture_id": null
    }
    """
    
    # Validate times
    validate_schedule_times(
        schedule_data.date,
        schedule_data.start_time,
        schedule_data.end_time
    )
    
    # Check for conflicts
    if check_schedule_conflict(
        session,
        current_user.user_id,
        schedule_data.date,
        schedule_data.start_time,
        schedule_data.end_time
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have a conflicting schedule at this time"
        )
    
    # Create schedule
    schedule = Schedule(
        teacher_id=current_user.user_id,
        lecture_id=schedule_data.lecture_id,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        date=schedule_data.date,
        status=schedule_data.status
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
    Get available time slots for a specific date
    
    Returns slots that:
    - Belong to current teacher
    - Are on the specified date
    - Have lecture_id = NULL (not reserved)
    - Status = "available"
    
    Query Parameter:
    - target_date: Date to check (format: YYYY-MM-DD)
    
    Example:
    GET /api/v1/schedules/available-slots/2025-01-20
    
    Response:
    {
        "date": "2025-01-20",
        "available_slots": [
            {
                "schedule_id": 100,
                "start_time": "10:00:00",
                "end_time": "11:30:00",
            },
            {
                "schedule_id": 101,
                "start_time": "14:00:00",
                "end_time": "15:30:00",
            }
        ]
    }
    """
    
    # Validate date is not in the past
    if target_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot check availability for past dates"
        )
    
    # Query current teacher's schedules for this date
    # ✅ UPDATED: Check lecture_id is NULL (not reserved)
    schedules = session.exec(
        select(Schedule).where(
            Schedule.teacher_id == current_user.user_id,
            Schedule.date == target_date,
            Schedule.lecture_id.is_(None),  # ← IMPORTANT: Not reserved yet
            Schedule.status == "available"
        ).order_by(Schedule.start_time)
    ).all()
    
    # Build available slots
    available_slots = []
    for schedule in schedules:
        available_slots.append(
            TimeSlot(
                schedule_id=schedule.schedule_id,  # ← ADDED
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
    
    # Query schedules (only those with lectures)
    schedules = session.exec(
        select(Schedule)
        .where(
            Schedule.teacher_id == current_user.user_id,
            Schedule.date >= today,
            Schedule.lecture_id.isnot(None),  # Must have a lecture
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
        
        # Get teacher name from user table
        teacher_name = "Unknown"
        if schedule.teacher and schedule.teacher.user:
            teacher_name = schedule.teacher.user.full_name
        
        result.append(
            FullTimeSlot(
                schedule_id=schedule.schedule_id,
                course_code=lecture.course_code,      # From lecture table
                lecture_title=lecture.title,           # From lecture table
                teacher_name=teacher_name,             # From user table
                date=schedule.date,                    # date type
                start_time=schedule.start_time,        # time type
                end_time=schedule.end_time,            # time type
                status=schedule.status
            )
        )
    
    return result

@router.patch("/{schedule_id}/cancel", response_model=CancelScheduleResponse)
def cancel_schedule_patch(
    schedule_id: int,
    current_user: User = Depends(get_current_teacher),
    session: Session = Depends(get_session)
):
    """
    Cancel a schedule (PATCH version)
    
    Same as DELETE but uses PATCH method which is more semantically correct
    since we're updating the schedule, not deleting it.
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
            detail="You can only cancel your own schedules"
        )
    
    if schedule.lecture_id is None and schedule.status == "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This schedule is already available"
        )
    
    previous_lecture_id = schedule.lecture_id
    
    # Free up the slot
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


