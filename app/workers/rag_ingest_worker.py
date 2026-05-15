# app/workers/rag_ingest_worker.py

import logging
from datetime import datetime
from sqlmodel import Session

from app.core.database import engine
from app.models.lecture import Lecture, LectureStatus
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
    with Session(engine) as session:

        # ── Fetch lecture ──────────────────────────────────────────
        lecture = session.get(Lecture, lecture_id)
        if not lecture:
            logger.error(f"[RAGIngest:{lecture_id}] Lecture not found in DB")
            return

        # ── Create or reset LectureIndex row ──────────────────────
        lecture_index = session.exec(
            __import__("sqlmodel").select(LectureIndex)
            .where(LectureIndex.lecture_id == lecture_id)
        ).first()

        if not lecture_index:
            lecture_index = LectureIndex(lecture_id=lecture_id)
            session.add(lecture_index)

        lecture_index.status        = IndexStatus.INGESTING
        lecture_index.error_message = None
        session.commit()

        logger.info(f"[RAGIngest:{lecture_id}] Starting ingest → {file_path}")

        # ── Call RAG /ingest ───────────────────────────────────────
        try:
            result = await ingest_lecture(file_path=file_path)

        except RAGServiceUnavailableError as e:
            logger.error(f"[RAGIngest:{lecture_id}] RAG service unavailable: {e}")
            _fail(session, lecture_index, str(e))
            return

        except RAGTimeoutError as e:
            logger.error(f"[RAGIngest:{lecture_id}] RAG ingest timed out: {e}")
            _fail(session, lecture_index, str(e))
            return

        except RAGIngestError as e:
            logger.error(f"[RAGIngest:{lecture_id}] RAG ingest failed: {e}")
            _fail(session, lecture_index, str(e))
            return

        except Exception as e:
            logger.error(f"[RAGIngest:{lecture_id}] Unexpected error: {e}")
            _fail(session, lecture_index, f"Unexpected error: {e}")
            return

        # ── Update LectureIndex with results ───────────────────────
        lecture_index.status                 = IndexStatus.READY
        lecture_index.rag_lecture_session_id = result.lecture_session_id
        lecture_index.chunks_indexed         = result.chunks_indexed
        lecture_index.nodes_written          = result.nodes_written
        lecture_index.relationships_written  = result.relationships_written
        lecture_index.ingested_at            = datetime.utcnow()
        lecture_index.error_message          = None

        # ── Mark lecture as indexed ────────────────────────────────
        lecture.is_indexed = True

        session.add(lecture_index)
        session.add(lecture)
        session.commit()

        logger.info(
            f"[RAGIngest:{lecture_id}] ✓ Done — "
            f"session={result.lecture_session_id} "
            f"chunks={result.chunks_indexed} "
            f"nodes={result.nodes_written} "
            f"rels={result.relationships_written}"
        )


def _fail(
    session       : Session,
    lecture_index : LectureIndex,
    message       : str,
) -> None:
    """Mark LectureIndex as FAILED and commit."""
    lecture_index.status        = IndexStatus.FAILED
    lecture_index.error_message = message
    session.add(lecture_index)
    session.commit()
    logger.error(f"[RAGIngest] FAILED: {message}")