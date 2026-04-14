# app/models/generated_content.py

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class ContentType(str, Enum):
    SCRIPT          = "script"
    WORKSHEET       = "worksheet"
    QUIZ            = "quiz"
    SUMMARY         = "summary"
    FLOWCHART       = "flowchart"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class GeneratedContent(SQLModel, table=True):
    __tablename__ = "generated_content"

    id:           Optional[int] = Field(default=None, primary_key=True)
    lecture_id:   int = Field(foreign_key="lectures.lecture_id", index=True)
    content_type: ContentType

    file_path:    str                    # primary output — always present
    answers_path: Optional[str] = Field(default=None)  # worksheet + quiz answer keys
    extra_path:   Optional[str] = Field(default=None)  # summary .txt, flowchart .mmd

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    lecture: Optional["Lecture"] = Relationship(back_populates="generated_content")