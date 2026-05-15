# app/rag_client/client.py

import httpx
import logging
from pathlib import Path

from app.core.config import settings
from app.rag_client.schemas import IngestResponse, QueryResponse, HealthResponse
from app.rag_client.exceptions import (
    RAGServiceUnavailableError,
    RAGTimeoutError,
    RAGIngestError,
    RAGQueryError,
    RAGSessionMismatchError,
)

logger = logging.getLogger(__name__)


# ── Ingest ────────────────────────────────────────────────────────────────────

async def ingest_lecture(file_path: str) -> IngestResponse:
    """
    Upload a lecture file to the RAG service for indexing.
    Sends the file as multipart/form-data to POST /ingest.
    Returns IngestResponse with lecture_session_id and stats.

    Args:
        file_path: absolute path to the lecture file on disk
                   (PDF/DOCX/PPTX for prepared, .txt for generated)
    """
    path = Path(file_path)

    if not path.exists():
        raise RAGIngestError(f"Lecture file not found on disk: {file_path}")

    logger.info(f"[RAGClient] Ingesting lecture file: {path.name}")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.RAG_TIMEOUT_INGEST)
        ) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    f"{settings.RAG_SERVICE_URL}/ingest",
                    files={"file": (path.name, f, _mime_type(path.suffix))},
                )
    except httpx.TimeoutException:
        raise RAGTimeoutError(
            f"RAG /ingest timed out after {settings.RAG_TIMEOUT_INGEST}s"
        )
    except httpx.ConnectError:
        raise RAGServiceUnavailableError(
            f"Cannot reach RAG service at {settings.RAG_SERVICE_URL}"
        )

    if response.status_code == 500:
        raise RAGIngestError(f"RAG ingest failed: {response.json().get('detail')}")

    if response.status_code == 422:
        raise RAGIngestError(f"RAG rejected the file: {response.json().get('detail')}")

    if response.status_code != 200:
        raise RAGIngestError(
            f"RAG /ingest returned unexpected status {response.status_code}"
        )

    logger.info(f"[RAGClient] Ingest successful")
    return IngestResponse(**response.json())


# ── Query ─────────────────────────────────────────────────────────────────────

async def query_lecture(
    lecture_session_id : str,
    student_session_id : str,
    query              : str,
) -> QueryResponse:
    """
    Send a student question to the RAG service.
    query can be plain text OR absolute path to an audio file.
    Returns QueryResponse with answer text and answer_file path.

    Args:
        lecture_session_id: rag_lecture_session_id from LectureIndex
        student_session_id: f"student_{user_id}_{lecture_id}"
        query:              question text or absolute audio file path
    """
    logger.info(
        f"[RAGClient] Query — lecture={lecture_session_id} "
        f"student={student_session_id}"
    )

    payload = {
        "lecture_session_id" : lecture_session_id,
        "student_session_id" : student_session_id,
        "query"              : query,
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.RAG_TIMEOUT_QUERY)
        ) as client:
            response = await client.post(
                f"{settings.RAG_SERVICE_URL}/query",
                json=payload,
            )
    except httpx.TimeoutException:
        raise RAGTimeoutError(
            f"RAG /query timed out after {settings.RAG_TIMEOUT_QUERY}s"
        )
    except httpx.ConnectError:
        raise RAGServiceUnavailableError(
            f"Cannot reach RAG service at {settings.RAG_SERVICE_URL}"
        )

    if response.status_code == 503:
        raise RAGServiceUnavailableError(
            "RAG service has no lecture ingested yet."
        )

    if response.status_code == 409:
        raise RAGSessionMismatchError(
            f"lecture_session_id mismatch: {response.json().get('detail')}"
        )

    if response.status_code == 500:
        raise RAGQueryError(
            f"RAG query failed: {response.json().get('detail')}"
        )

    if response.status_code != 200:
        raise RAGQueryError(
            f"RAG /query returned unexpected status {response.status_code}"
        )

    logger.info(f"[RAGClient] Query successful")
    return QueryResponse(**response.json())


# ── Health ────────────────────────────────────────────────────────────────────

async def check_health() -> HealthResponse:
    """
    Check if the RAG service is alive and has a lecture loaded.
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.get(f"{settings.RAG_SERVICE_URL}/health")
        return HealthResponse(**response.json())
    except Exception:
        raise RAGServiceUnavailableError(
            f"Cannot reach RAG service at {settings.RAG_SERVICE_URL}"
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _mime_type(suffix: str) -> str:
    """Return MIME type for common lecture file extensions."""
    return {
        ".pdf"  : "application/pdf",
        ".docx" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx" : "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt"  : "text/plain",
        ".md"   : "text/markdown",
    }.get(suffix.lower(), "application/octet-stream")