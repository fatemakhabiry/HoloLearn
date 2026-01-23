
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import time, date

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.lecture import Lecture


class ScheduleBase(SQLModel):
    start_time: time
    end_time: time
    date: date
    status: str = Field(default="available", max_length=50)


class Schedule(ScheduleBase, table=True):
    __tablename__ = "schedules"
    
    schedule_id: Optional[int] = Field(default=None, primary_key=True)
    created_by_user_id: int = Field(foreign_key="users.user_id")  # Admin who created it
    lecture_id: Optional[int] = Field(default=None, foreign_key="lectures.lecture_id", nullable=True)
    
    # Relationships
    # ✅ User who created this schedule (admin)
    created_by: Optional["User"] = Relationship(
        back_populates="created_schedules",
        sa_relationship_kwargs={"foreign_keys": "[Schedule.created_by_user_id]"}
    )
    
    # ✅ Lecture assigned to this schedule (if any)
    lecture: Optional["Lecture"] = Relationship(back_populates="schedules")


class ScheduleCreate(ScheduleBase):
    """For creating a schedule (Admin only)"""
    lecture_id: Optional[int] = None


class SchedulePublic(ScheduleBase):
    """Public schedule information"""
    schedule_id: int
    created_by_user_id: int
    lecture_id: Optional[int] = None


class ScheduleUpdate(SQLModel):
    """For updating a schedule"""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    date: Optional[date] = None
    status: Optional[str] = None
    lecture_id: Optional[int] = None


class ScheduleWithDetails(SchedulePublic):
    """Schedule with admin and lecture info"""
    admin_name: Optional[str] = None  # Name of admin who created it
    course_code: Optional[str] = None
    lecture_title: Optional[str] = None