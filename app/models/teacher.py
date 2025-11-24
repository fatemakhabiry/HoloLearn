from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

class TeacherBase(SQLModel):
    photo: Optional[str] = None  # Path to uploaded photo
    voice_sample: Optional[str] = None  # Path to uploaded voice sample

class Teacher(TeacherBase, table=True):
    __tablename__ = "teachers"
    
    user_id: int = Field(foreign_key="users.user_id", primary_key=True)
    
    user: Optional["User"] = Relationship(back_populates="teacher")


class TeacherCreate(TeacherBase):
    pass

class TeacherPublic(TeacherBase):
    user_id: int

class TeacherUpdate(SQLModel):
    photo: Optional[str] = None
    voice_sample: Optional[str] = None