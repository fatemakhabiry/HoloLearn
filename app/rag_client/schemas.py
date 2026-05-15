# app/rag_client/schemas.py

from pydantic import BaseModel
from typing import Optional


class IngestResponse(BaseModel):
    lecture_session_id    : str
    chunks_indexed        : int
    nodes_written         : int
    relationships_written : int
    message               : str


class QueryResponse(BaseModel):
    lecture_session_id : str
    student_session_id : str
    query              : str
    answer             : str
    answer_file        : str   # absolute path to saved .txt on RAG machine
    timestamp          : str   # ISO-8601 UTC


class HealthResponse(BaseModel):
    status              : str
    lecture_session_id  : Optional[str] = None
    pipeline_ready      : bool
    active_students     : int