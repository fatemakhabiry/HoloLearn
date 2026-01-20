from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import time ,date

if TYPE_CHECKING:
    from app.models.teacher import Teacher
    from app.models.lecture import Lecture

class ScheduleBase(SQLModel):
    start_time: time
    end_time: time
    date: date
    status: str = Field(default="scheduled", max_length=50)

class Schedule(ScheduleBase, table=True):
    __tablename__ = "schedules"
    
    schedule_id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: int = Field(foreign_key="teachers.user_id")
    lecture_id: Optional[int] = Field(default=None, nullable=True)
    
    # Relationships
    teacher: Optional["Teacher"] = Relationship(back_populates="schedules")
    lecture_id: Optional[int] = Field(default=None, foreign_key="lectures.lecture_id", nullable=True)
    lecture: Optional["Lecture"] = Relationship(back_populates="schedules")


class ScheduleCreate(ScheduleBase):
    """For creating a schedule"""
    lecture_id: Optional[int] = None




class SchedulePublic(ScheduleBase):
    """Public schedule information"""
    schedule_id: int
    teacher_id: int
    lecture_id: Optional[int] = None

class ScheduleUpdate(SQLModel):
    """For updating a schedule"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    date: date
    status: Optional[str] = None
    lecture_id: Optional[int] = None

class ScheduleWithDetails(SchedulePublic):
    """Schedule with teacher and lecture info"""
    teacher_name: Optional[str] = None
    course_code: Optional[str] = None