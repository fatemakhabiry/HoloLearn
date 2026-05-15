# app/models/lecture_index.py

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class IndexStatus(str, Enum):
    PENDING   = "pending"
    INGESTING = "ingesting"
    READY     = "ready"
    FAILED    = "failed"


class LectureIndex(SQLModel, table=True):
    __tablename__ = "lecture_indexes"

    id                      : Optional[int] = Field(default=None, primary_key=True)
    lecture_id              : int           = Field(foreign_key="lectures.lecture_id", unique=True, index=True)

    # Returned by RAG /ingest — used in every /query call
    rag_lecture_session_id  : Optional[str] = Field(default=None)

    status                  : IndexStatus   = Field(default=IndexStatus.PENDING)

    # Stats returned by RAG /ingest
    chunks_indexed          : Optional[int] = Field(default=None)
    nodes_written           : Optional[int] = Field(default=None)
    relationships_written   : Optional[int] = Field(default=None)

    ingested_at             : Optional[datetime] = Field(default=None)
    error_message           : Optional[str]      = Field(default=None)

    created_at              : datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    lecture: Optional["Lecture"] = Relationship(back_populates="lecture_index")