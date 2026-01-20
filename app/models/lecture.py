from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.models.teacher import Teacher
    from app.models.course import Course
    from app.models.resource import Resource
    from app.models.schedule import Schedule


class LectureType(str, Enum):
    PREPARED = "prepared"  # Teacher uploaded ready lecture
    GENERATED = "generated"  # LLM generated from resources


class LectureStatus(str, Enum):
    DRAFT = "draft"  # Being created
    GENERATING = "generating"  # LLM is generating
    COMPLETED = "completed"  # Ready to use
    FAILED = "failed"  # Generation failed


class LectureBase(SQLModel):
    """Base lecture schema - shared fields"""
    title: str = Field(max_length=200)
    lecture_type: LectureType = Field(default=LectureType.PREPARED)
    status: LectureStatus = Field(default=LectureStatus.DRAFT)
    final_content: Optional[str] = None  # URL to final lecture (Drive link)


class Lecture(LectureBase, table=True):
    """Database model"""
    __tablename__ = "lectures"
    
    lecture_id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: int = Field(foreign_key="teachers.user_id")
    course_code: str = Field(foreign_key="courses.course_code", max_length=50)
    
    # Relationships
    teacher: Optional["Teacher"] = Relationship(back_populates="lectures")
    course: Optional["Course"] = Relationship(back_populates="lectures")
    resources: List["Resource"] = Relationship(back_populates="lecture")
    schedules: List["Schedule"] = Relationship(back_populates="lecture")


class LectureCreate(SQLModel):
    """For creating a new lecture"""
    title: str
    course_code: str
    lecture_type: LectureType = LectureType.PREPARED
    final_content: Optional[str] = None  # For prepared lectures (Drive URL)


class LecturePublic(LectureBase):
    """Public lecture information"""
    lecture_id: int
    teacher_id: int
    course_code: str


class LectureUpdate(SQLModel):
    """For updating a lecture"""
    title: Optional[str] = None
    status: Optional[LectureStatus] = None
    final_content: Optional[str] = None
    lecture_type: Optional[LectureType] = None


class LectureWithDetails(LecturePublic):
    """Lecture with teacher, course and resources info"""
    teacher_name: Optional[str] = None
    course_title: Optional[str] = None
    resource_count: int = 0