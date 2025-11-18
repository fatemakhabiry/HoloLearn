from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

class StudentBase(SQLModel):
    student_number: Optional[str] = None
    major: Optional[str] = None

class Student(StudentBase, table=True):
    __tablename__ = "students"
    
    user_id: int = Field(foreign_key="users.user_id", primary_key=True)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="student")
    # enrollments: Will add later when we create Enrollment model

class StudentCreate(StudentBase):
    pass

class StudentPublic(StudentBase):
    user_id: int

class StudentUpdate(SQLModel):
    student_number: Optional[str] = None
    major: Optional[str] = None
