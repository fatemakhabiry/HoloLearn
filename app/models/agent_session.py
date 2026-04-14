# app/models/agent_session.py

from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class AgentStatus(str, Enum):
    STARTING           = "starting"
    GENERATING_LECTURE = "generating_lecture"
    AWAITING_APPROVAL  = "awaiting_approval"
    REGENERATING       = "regenerating"
    GENERATING_CONTENT = "generating_content"
    DONE               = "done"
    FAILED             = "failed"


class AgentSession(SQLModel, table=True):
    __tablename__ = "agent_sessions"

    id:         Optional[int] = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lectures.lecture_id", unique=True, index=True)

    # LangGraph key — passed to graph.aget_state({"configurable": {"thread_id": ...}})
    thread_id: str = Field(unique=True, index=True)

    # Mirrors AgentState.current_step — for listing/filtering without hitting LangGraph
    status: AgentStatus = Field(default=AgentStatus.STARTING)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    lecture: Optional["Lecture"] = Relationship(back_populates="agent_session")