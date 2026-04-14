# app/models/resource.py  — UPDATED

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class ResourceType(str, Enum):
    PDF     = "pdf"
    PPTX    = "pptx"
    DOCX    = "docx"       # ← ADD
    VIDEO   = "video"
    AUDIO   = "audio"      # ← ADD
    WEBSITE = "website"    # ← ADD
    IMAGE   = "image"      # ← ADD (for lecture generator images)
    DOCUMENT = "document"
    OTHER   = "other"


class Resource(SQLModel, table=True):
    __tablename__ = "resources"

    resource_id:   Optional[int] = Field(default=None, primary_key=True)
    lecture_id:    int            = Field(foreign_key="lectures.lecture_id", index=True)
    resource_type: ResourceType
    file_path:     str            # local path to uploaded file
    query:         str            = Field(default="")   # ← ADD — relevance query for generator

    created_at: datetime = Field(default_factory=datetime.utcnow)  # ← ADD

    # Relationship
    lecture: Optional["Lecture"] = Relationship(back_populates="resources")