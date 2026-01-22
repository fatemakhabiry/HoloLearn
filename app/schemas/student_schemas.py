# app/schemas/student_schemas.py
"""
Student-related response schemas for API endpoints
"""
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime


class UpcomingLectureItem(SQLModel):
    """Individual lecture item for student dashboard"""
    schedule_id: int
    status: str  # "ENDED" (finished today), "ONGOING" (happening now), or "UPCOMING" (future)
    teacher_name: str
    course_code: str
    lecture_title: str
    start_time: datetime  # Combined date + time
    end_time: datetime    # Combined date + time
    transcript_url: Optional[str] = None  # from lecture.final_content
    lecture_id: Optional[int] = None


class UpcomingLecturesResponse(SQLModel):
    """Response containing list of lectures (ended today, ongoing, and upcoming)"""
    lectures: List[UpcomingLectureItem]
    total_count: int