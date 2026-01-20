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

