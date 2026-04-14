# app/models/lecture_version.py

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class VersionStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LectureVersion(SQLModel, table=True):
    __tablename__ = "lecture_versions"

    id:             Optional[int] = Field(default=None, primary_key=True)
    lecture_id:     int = Field(foreign_key="lectures.lecture_id", index=True)
    version_number: int  # 1 = first attempt, 2 = first regen, etc.

    # Local file paths written by the agent
    pdf_path:  Optional[str] = Field(default=None)
    txt_path:  Optional[str] = Field(default=None)  # read by content generators
    json_path: Optional[str] = Field(default=None)

    status:           VersionStatus = Field(default=VersionStatus.PENDING)
    teacher_feedback: Optional[str] = Field(default=None)  # filled on rejection

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    lecture: Optional["Lecture"] = Relationship(back_populates="versions")