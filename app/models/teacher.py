from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.schedule import Schedule
    from app.models.course import Course
    from app.models.lecture import Lecture

class TeacherBase(SQLModel):
    photo: Optional[str] = None  # Path to uploaded photo
    voice_sample: Optional[str] = None  # Path to uploaded voice sample

class Teacher(TeacherBase, table=True):
    __tablename__ = "teachers"
    
    user_id: int = Field(foreign_key="users.user_id", primary_key=True)
    
    user: Optional["User"] = Relationship(back_populates="teacher")
    courses: List["Course"] = Relationship(back_populates="teacher")
    lectures: List["Lecture"] = Relationship(back_populates="teacher")



class TeacherCreate(TeacherBase):
    pass

class TeacherPublic(TeacherBase):
    user_id: int

class TeacherUpdate(SQLModel):
    photo: Optional[str] = None
    voice_sample: Optional[str] = None

class TeacherProfileStatus(SQLModel):
    needs_profile_setup: bool
    has_photo: bool
    has_voice_sample: bool