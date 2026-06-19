# app/workers/rag_ingest_worker.py

import logging
from datetime import datetime
from sqlmodel import Session, select  # FIX #1 — added select here, no more __import__ hack

from app.core.database import engine
from app.models.lecture import Lecture
from app.models.lecture_index import LectureIndex, IndexStatus
from app.rag_client.client import ingest_lecture
from app.rag_client.exceptions import (
    RAGServiceUnavailableError,
    RAGTimeoutError,
    RAGIngestError,
)

logger = logging.getLogger(__name__)


async def run_rag_ingest(ctx: dict, lecture_id: int, file_path: str) -> None:
    """
    ARQ background job — calls RAG /ingest for a single lecture.

    Creates or updates LectureIndex row to track the indexing state.
    Updates Lecture.is_indexed on success.

    Args:
        ctx:        ARQ worker context (unused but required by ARQ)
        lecture_id: your DB lecture ID
        file_path:  absolute path to the lecture file on disk
                    (original PDF/DOCX/PPTX for prepared lectures)
                    (generated .txt file for generated lectures)
    """

    # ── Phase 1: read lecture + set status to INGESTING, then close DB ────────
    # FIX #2 — DB session is closed BEFORE the async HTTP call so we don't
    # hold a connection open while waiting on the RAG service (could be 30s+)
    with Session(engine) as session:
        lecture = session.get(Lecture, lecture_id)
        if not lecture:
            logger.error(f"[RAGIngest:{lecture_id}] Lecture not found in DB")
            return

        # FIX #1 — use properly imported select, not __import__ hack
        lecture_index = session.exec(
            select(LectureIndex).where(LectureIndex.lecture_id == lecture_id)
        ).first()

        if not lecture_index:
            lecture_index = LectureIndex(lecture_id=lecture_id)
            session.add(lecture_index)

        lecture_index.status        = IndexStatus.INGESTING
        lecture_index.error_message = None
        session.commit()
        # session closes here — DB connection returned to pool

    logger.info(f"[RAGIngest:{lecture_id}] Starting ingest → {file_path}")

    # ── Phase 2: async HTTP call with NO open DB connection ───────────────────
    try:
        result = await ingest_lecture(file_path=file_path)

    except RAGServiceUnavailableError as e:
        logger.error(f"[RAGIngest:{lecture_id}] RAG service unavailable: {e}")
        _fail(lecture_id, str(e))
        return

    except RAGTimeoutError as e:
        logger.error(f"[RAGIngest:{lecture_id}] RAG ingest timed out: {e}")
        _fail(lecture_id, str(e))
        return

    except RAGIngestError as e:
        logger.error(f"[RAGIngest:{lecture_id}] RAG ingest failed: {e}")
        _fail(lecture_id, str(e))
        return

    except Exception as e:
        logger.error(f"[RAGIngest:{lecture_id}] Unexpected error: {e}")
        _fail(lecture_id, f"Unexpected error: {e}")
        return

    # ── Phase 3: open fresh session to write results ──────────────────────────
    with Session(engine) as session:
        lecture_index = session.exec(
            select(LectureIndex).where(LectureIndex.lecture_id == lecture_id)
        ).first()

        lecture = session.get(Lecture, lecture_id)

        if lecture_index:
            lecture_index.status                 = IndexStatus.READY
            lecture_index.rag_lecture_session_id = result.lecture_session_id
            lecture_index.chunks_indexed         = result.chunks_indexed
            lecture_index.nodes_written          = result.nodes_written
            lecture_index.relationships_written  = result.relationships_written
            lecture_index.ingested_at            = datetime.utcnow()
            lecture_index.error_message          = None
            session.add(lecture_index)

        if lecture:
            lecture.is_indexed = True
            session.add(lecture)

        session.commit()

    logger.info(
        f"[RAGIngest:{lecture_id}] ✓ Done — "
        f"session={result.lecture_session_id} "
        f"chunks={result.chunks_indexed} "
        f"nodes={result.nodes_written} "
        f"rels={result.relationships_written}"
    )


def _fail(lecture_id: int, message: str) -> None:
    """
    Open a fresh DB session and mark LectureIndex as FAILED.

    Takes lecture_id instead of a live session/object because this is
    called after the original session is already closed (Phase 2 failure).
    """
    with Session(engine) as session:
        lecture_index = session.exec(
            select(LectureIndex).where(LectureIndex.lecture_id == lecture_id)
        ).first()

        if lecture_index:
            lecture_index.status        = IndexStatus.FAILED
            lecture_index.error_message = message
            session.add(lecture_index)
            session.commit()

    logger.error(f"[RAGIngest:{lecture_id}] FAILED: {message}")