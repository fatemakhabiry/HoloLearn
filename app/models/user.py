"""
Updated User Model
Aligned with public schedules (created_by_user_id)
"""

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.teacher import Teacher
    from app.models.schedule import Schedule


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class OTPVerification(SQLModel, table=True):
    """Model to store OTP codes for password reset"""
    __tablename__ = "otp_verifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    otp_code: str = Field(max_length=6)  # 6-digit OTP
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # OTP valid for 10 minutes
    is_used: bool = Field(default=False)


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: str
    role: UserRole


class User(UserBase, table=True):
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    # Relationships
    teacher: Optional["Teacher"] = Relationship(back_populates="user")
    
    # ✅ UPDATED: Schedules created by this user (if admin)
    created_schedules: List["Schedule"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"foreign_keys": "[Schedule.created_by_user_id]"}
    )


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    user_id: int


class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None