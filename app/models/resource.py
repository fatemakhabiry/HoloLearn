from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class ResourceType(str, Enum):
    PDF = "pdf"
    PPTX = "pptx"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class Resource(SQLModel, table=True):
    __tablename__ = "resources"
    
    resource_id: Optional[int] = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lectures.lecture_id")
    resource_type: ResourceType
    file_path: str  # URL to Google Drive
        
    # Relationships
    lecture: Optional["Lecture"] = Relationship(back_populates="resources")