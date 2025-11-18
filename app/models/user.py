from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole

class User(UserBase, table=True):
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    teacher: Optional["Teacher"] = Relationship(back_populates="user")
    student: Optional["Student"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    user_id: int

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None