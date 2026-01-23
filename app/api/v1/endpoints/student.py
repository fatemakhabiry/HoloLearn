# app/api/v1/endpoints/student.py
"""
Student endpoints - Dashboard and lecture access
"""
from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select
from datetime import datetime, date, timedelta, time as time_type
from app.core.database import get_session
from app.api.deps import get_current_student  
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.schedule import Schedule
from app.models.lecture import Lecture
from app.models.course import Course
from app.models.teacher import Teacher
from app.schemas.student_schemas import UpcomingLecturesResponse, UpcomingLectureItem 

router = APIRouter()


def calculate_lecture_status(schedule_date: date, start_time: time_type, end_time: time_type) -> str:
    """
    Calculate lecture status: ENDED, ONGOING, or UPCOMING
    
    Args:
        schedule_date: Date of the scheduled lecture
        start_time: Start time of the lecture
        end_time: End time of the lecture
        
    Returns:
        - "ENDED" if lecture finished today
        - "ONGOING" if currently happening
        - "UPCOMING" if in the future
    """
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Only check ENDED and ONGOING for today's lectures
    if schedule_date == current_date:
        # Lecture has ended today
        if current_time > end_time:
            return "ENDED"
        
        # Lecture is currently happening
        if start_time <= current_time <= end_time:
            return "ONGOING"
    
    # All other cases are UPCOMING (future lectures)
    return "UPCOMING"


@router.get(
    "/upcoming-lectures",
    response_model=UpcomingLecturesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lectures for student (ended today, ongoing, and upcoming)",
    description="Returns lectures: ended today, currently ongoing, and upcoming (next 7 days)"
)
async def get_upcoming_lectures(
    current_user: User = Depends(get_current_student),  
    session: Session = Depends(get_session)
):
    """
    Get lectures for the authenticated student.
    
    Returns three types of lectures:
    - ENDED: Lectures that finished today
    - ONGOING: Lectures currently happening
    - UPCOMING: Future lectures (next 7 days)
    
    Features:
    - Fetches lectures from courses the student is enrolled in
    - Includes today's ended lectures
    - Shows currently ongoing lectures
    - Shows upcoming lectures for the next 7 days
    - Returns start_time and end_time as datetime (combined date + time)
    - Sorted by date and time (earliest first)
    
    Requires: Student role authentication (handled by get_current_student dependency)
    """
    
    # No need to check role - get_current_student() already does it!
    
    # Date range: from today (to get ended lectures) to +7 days (for upcoming)
    today = date.today()
    end_date = today + timedelta(days=7)
    
    # Get all courses the student is enrolled in
    enrolled_courses_query = select(Enrollment.course_code).where(
        Enrollment.student_id == current_user.user_id
    )
    enrolled_courses = session.exec(enrolled_courses_query).all()
    
    if not enrolled_courses:
        # Student not enrolled in any courses
        return UpcomingLecturesResponse(lectures=[], total_count=0)
    
    # Get all schedules for enrolled courses within date range
    # Includes today's lectures (even if ended) and upcoming lectures
    # Join chain: Schedule -> Lecture -> Course -> Teacher (user_id) -> User
    schedules_query = (
        select(Schedule, Lecture, Course, User)
        .join(Lecture, Schedule.lecture_id == Lecture.lecture_id)
        .join(Course, Lecture.course_code == Course.course_code)
        .join(Teacher, Course.teacher_id == Teacher.user_id)  # Join to Teacher table
        .join(User, Teacher.user_id == User.user_id)          # Then to User for full_name
        .where(
            Schedule.date >= today,        # From today (includes ended lectures from today)
            Schedule.date <= end_date,     # Up to +7 days
            Course.course_code.in_(enrolled_courses)
        )
        .order_by(Schedule.date, Schedule.start_time)
    )
    
    results = session.exec(schedules_query).all()
    
    # Build response items
    upcoming_lectures = []
    for schedule, lecture, course, user in results:
        # Calculate status (ENDED, ONGOING, or UPCOMING)
        lecture_status = calculate_lecture_status(
            schedule.date,
            schedule.start_time,
            schedule.end_time
        )
        
        # Combine date with time to create datetime objects
        start_datetime = datetime.combine(schedule.date, schedule.start_time)
        end_datetime = datetime.combine(schedule.date, schedule.end_time)
        
        item = UpcomingLectureItem(
            schedule_id=schedule.schedule_id,
            status=lecture_status,  # ENDED, ONGOING, or UPCOMING
            teacher_name=user.full_name,  # From User table
            course_code=course.course_code,
            lecture_title=lecture.title,
            start_time=start_datetime,  # Combined datetime
            end_time=end_datetime,      # Combined datetime
            transcript_url=lecture.final_content,
            lecture_id=lecture.lecture_id
        )
        upcoming_lectures.append(item)
    
    return UpcomingLecturesResponse(
        lectures=upcoming_lectures,
        total_count=len(upcoming_lectures)
    )


