# app/schemas/student.py
"""
Student-related response schemas for API endpoints
"""
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import date, time


class UpcomingLectureItem(SQLModel):
    """Individual upcoming lecture item for student dashboard"""
    schedule_id: int
    status: str  # "ONGOING" or "UPCOMING"
    teacher_name: str
    course_code: str
    course_title: str
    lecture_title: str
    date: date
    start_time: time
    end_time: time
    # transcript_url: Optional[str] = None  # from lecture.final_content
    # lecture_id: Optional[int] = None


class UpcomingLecturesResponse(SQLModel):
    """Response containing list of upcoming lectures"""
    lectures: List[UpcomingLectureItem]
    total_count: int