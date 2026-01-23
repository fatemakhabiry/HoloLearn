from pydantic import BaseModel
from typing import Optional,List
from datetime import date ,datetime ,time



class TimeSlot(BaseModel):
    """Represents a reserved time slot"""
    schedule_id: int
    start_time: time
    end_time: time


class FullTimeSlot(BaseModel):
    """Represents a reserved time slot"""
    start_time: time
    end_time: time
    date : date
    schedule_id: int
    teacher_name: str
    lecture_title: str
    status: str
    course_code: str

class FullTimeSlot2(BaseModel):
    schedule_id: Optional[int] = None      # Null if draft
    lecture_id: int                        # Always present
    course_code: str                       # Always present
    lecture_title: str                     # Always present
    teacher_name: str                      # Always present
    start_time: Optional[datetime] = None  # Null if draft
    end_time: Optional[datetime] = None    # Null if draft
    status: str                            # "scheduled" or "draft"


class CancelScheduleResponse(BaseModel):
    """Response after canceling a schedule"""
    message: str
    schedule_id: int
    status: str
    previous_lecture_id: int


class DateAvailability(BaseModel):
    """Date availability response"""
    date: date
    available_slots: List[TimeSlot]


# Request model for confirming and publishing
class ConfirmPublishRequest(BaseModel):
    """Request to confirm and publish lecture with existing schedule slot"""
    schedule_id: int  # ID of the pre-existing schedule slot to reserve


# Response model
class ConfirmPublishResponse(BaseModel):
    """Response after confirming and publishing lecture"""
    message: str
    lecture_id: int
    schedule_id: int
    lecture_title: str
    course_code: str
    lecture_status: str
    schedule_status: str
    scheduled_date: date
    start_time: time
    end_time: time

# ============================================
# Response Models
# ============================================

class LectureEditDetails(BaseModel):
    """Lecture details for the edit form"""
    lecture_id: int
    schedule_id: int
    title: str
    course_code: str
    current_file_url: str
    scheduled_date: date
    start_time: time
    end_time: time
    status: str


class EditLectureRequest(BaseModel):
    """Request to edit lecture (JSON body)"""
    title: Optional[str] = None
    course_code: Optional[str] = None
    new_schedule_id: Optional[int] = None

class EditLectureResponse(BaseModel):
    """Response after editing lecture"""
    message: str
    lecture_id: int
    schedule_id: int
    lecture_title: str
    course_code: str
    lecture_status: str
    scheduled_date: date
    start_time: time
    end_time: time
    schedule_status: str
    schedule_changed: bool 


class DeleteLectureResponse(BaseModel):
    """Response after deleting a lecture"""
    message: str
    # lecture_id: int
    # lecture_title: str
    # schedules_freed: int  # Number of schedules that were freed
    # freed_schedule_ids: List[int]  # IDs of schedules that were freed
