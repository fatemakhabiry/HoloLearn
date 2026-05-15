# app/models/qa_message.py

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.qa_session import QASession


class MessageRole(str, Enum):
    STUDENT   = "student"
    ASSISTANT = "assistant"


class QAMessage(SQLModel, table=True):
    __tablename__ = "qa_messages"

    id          : Optional[int] = Field(default=None, primary_key=True)
    session_id  : int           = Field(foreign_key="qa_sessions.id", index=True)
    role        : MessageRole

    # The question text (student) or answer text (assistant)
    content_text : str

    # Student voice input file path (nullable)
    voice_input_path     : Optional[str] = Field(default=None)

    # RAG saved .txt file path — input to TTS pipeline
    rag_answer_file_path : Optional[str] = Field(default=None)

    # Your TTS audio output — sent to mobile
    audio_output_path    : Optional[str] = Field(default=None)

    # Future — hologram video
    video_output_path    : Optional[str] = Field(default=None)

    created_at  : datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    session : Optional["QASession"] = Relationship(back_populates="messages")