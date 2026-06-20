# app/models/qa_export.py

from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum
from datetime import datetime


class ExportStatus(str, Enum):
    READY   = "ready"
    EXPIRED = "expired"


class QAExport(SQLModel, table=True):
    __tablename__ = "qa_exports"

    id         : Optional[int] = Field(default=None, primary_key=True)
    student_id : int           = Field(foreign_key="users.user_id", index=True)
    lecture_id : int           = Field(foreign_key="lectures.lecture_id", index=True)

    status        : ExportStatus = Field(default=ExportStatus.READY)
    file_path     : Optional[str] = Field(default=None)
    message_count : Optional[int] = Field(default=None)

    created_at : datetime = Field(default_factory=datetime.utcnow)
    expires_at : datetime