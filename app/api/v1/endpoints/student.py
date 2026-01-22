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
    Calculate if lecture is ONGOING or UPCOMING based on current time
    
    Args:
        schedule_date: Date of the scheduled lecture
        start_time: Start time of the lecture
        end_time: End time of the lecture
        
    Returns:
        "ONGOING" if currently happening, "UPCOMING" if in the future
    """
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Only check ONGOING if schedule is today
    if schedule_date == current_date:
        # Check if current time is between start and end
        if start_time <= current_time <= end_time:
            return "ONGOING"
    
    # All other cases are UPCOMING
    return "UPCOMING"


@router.get(
    "/upcoming-lectures",
    response_model=UpcomingLecturesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get upcoming lectures for student",
    description="Returns all upcoming lectures (next 7 days) for courses the student is enrolled in"
)
async def get_upcoming_lectures(
    current_user: User = Depends(get_current_student),  
    session: Session = Depends(get_session)
):
    """
    Get upcoming lectures for the authenticated student.
    
    - Fetches lectures from courses the student is enrolled in
    - Shows lectures scheduled for the next 7 days
    - Calculates ONGOING vs UPCOMING status
    - Includes teacher name, course details, and transcript URLs
    - Sorted by date and time (earliest first)
    
    Requires: Student role authentication (handled by get_current_student dependency)
    """
    
    #  No need to check role - get_current_student() already does it!
    
    # Calculate date range (today + next 7 days)
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
    # Join: Schedule -> Lecture -> Course -> Teacher -> User
    schedules_query = (
        select(Schedule, Lecture, Course, Teacher, User)
        .join(Lecture, Schedule.lecture_id == Lecture.lecture_id)
        .join(Course, Lecture.course_code == Course.course_code)
        .join(Teacher, Course.teacher_id == Teacher.user_id)
        .join(User, Teacher.user_id == User.user_id)
        .where(
            Schedule.date >= today,
            Schedule.date <= end_date,
            Course.course_code.in_(enrolled_courses)
        )
        .order_by(Schedule.date, Schedule.start_time)
    )
    
    results = session.exec(schedules_query).all()
    
    # Build response items
    upcoming_lectures = []
    for schedule, lecture, course, teacher, user in results:
        # Calculate status
        lecture_status = calculate_lecture_status(
            schedule.date,
            schedule.start_time,
            schedule.end_time
        )
        
        item = UpcomingLectureItem(
            schedule_id=schedule.schedule_id,
            status=lecture_status,
            teacher_name=user.full_name,
            course_code=course.course_code,
            course_title=course.title,
            lecture_title=lecture.title,
            date=schedule.date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            transcript_url=lecture.final_content,
            lecture_id=lecture.lecture_id
        )
        upcoming_lectures.append(item)
    
    return UpcomingLecturesResponse(
        lectures=upcoming_lectures,
        total_count=len(upcoming_lectures)
    )












