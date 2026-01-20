from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.teacher import Teacher
    from app.models.enrollment import Enrollment
    from app.models.lecture import Lecture

class CourseBase(SQLModel):
    title: str = Field(max_length=200)

class Course(CourseBase, table=True):
    __tablename__ = "courses"
    
    course_code: str = Field(primary_key=True, max_length=50)
    teacher_id: int = Field(foreign_key="teachers.user_id")
    
    # Relationships
    teacher: Optional["Teacher"] = Relationship(back_populates="courses")
    enrollments: List["Enrollment"] = Relationship(back_populates="course")
    lectures: List["Lecture"] = Relationship(back_populates="course")


class CoursePublic(CourseBase):
    """Public course information"""
    course_code: str
    teacher_id: int

class CourseWithDetails(CoursePublic):
    """Course with teacher and enrollment info"""
    teacher_name: Optional[str] = None
    enrolled_students: int = 0