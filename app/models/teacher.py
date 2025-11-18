from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    # from app.models.avatar import Avatar
    # from app.models.schedule import Schedule
    # from app.models.course import Course

class TeacherBase(SQLModel):
    department: Optional[str] = None
    phone: Optional[int] = None
    status: str = "pending"

class Teacher(TeacherBase, table=True):
    __tablename__ = "teachers"
    
    user_id: int = Field(foreign_key="users.user_id", primary_key=True)
    
    user: Optional["User"] = Relationship(back_populates="teacher")
    # avatar: Optional["Avatar"] = Relationship(back_populates="teacher")
    # schedules: List["Schedule"] = Relationship(back_populates="teacher")
    # courses: List["Course"] = Relationship(back_populates="teacher")

class TeacherCreate(TeacherBase):
    pass

class TeacherPublic(TeacherBase):
    user_id: int

class TeacherUpdate(SQLModel):
    department: Optional[str] = None
    phone: Optional[int] = None
    status: Optional[str] = None