from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.user import User

class EnrollmentBase(SQLModel):
    pass

class Enrollment(EnrollmentBase, table=True):
    __tablename__ = "enrollments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    course_code: str = Field(foreign_key="courses.course_code", max_length=50)
    student_id: int = Field(foreign_key="users.user_id")  # ✅ Direct to users table
    
    # Relationships
    course: Optional["Course"] = Relationship(back_populates="enrollments")
    student: Optional["User"] = Relationship()  # No back_populates needed

class EnrollmentPublic(EnrollmentBase):
    """Public enrollment information"""
    id: int
    course_code: str
    student_id: int

class EnrollmentWithDetails(EnrollmentPublic):
    """Enrollment with student and course details"""
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    course_title: Optional[str] = None