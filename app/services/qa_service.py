# # app/services/qa_service.py

# import logging
# from datetime import datetime
# from typing import Optional
# from sqlmodel import Session, select

# from app.core.database import engine
# from app.models.lecture import Lecture
# from app.models.lecture_index import LectureIndex, IndexStatus
# from app.models.qa_session import QASession
# from app.models.qa_message import QAMessage, MessageRole
# from app.rag_client import client as rag_client
# from app.rag_client.exceptions import (
#     RAGServiceUnavailableError,
#     RAGTimeoutError,
#     RAGQueryError,
#     RAGSessionMismatchError,
# )
# from app.services.voice_service import save_voice_file
# from app.services.tts_service import generate_audio
# from fastapi import UploadFile, HTTPException

# logger = logging.getLogger(__name__)


# # ── Ask ───────────────────────────────────────────────────────────────────────

# async def ask(
#     lecture_id : int,
#     student_id : int,
#     text       : Optional[str]       = None,
#     voice_file : Optional[UploadFile] = None,
#     db         : Session              = None,
# ) -> dict:
#     """
#     Main Q&A orchestrator.

#     Accepts either text or voice input from the student.
#     Returns answer text + audio URL for Stage 1.

#     Flow:
#       1. Verify lecture is indexed
#       2. Load or create QASession
#       3. Handle voice → save file → get path
#       4. Call RAG /query
#       5. Save QAMessage rows (student + assistant)
#       6. Generate TTS audio
#       7. Return response to router
#     """

#     # ── 1. Verify lecture exists and is indexed ────────────────────
#     lecture = db.get(Lecture, lecture_id)
#     if not lecture:
#         raise HTTPException(status_code=404, detail="Lecture not found")

#     if not lecture.is_indexed:
#         raise HTTPException(
#             status_code=503,
#             detail="Lecture is not indexed yet. Please try again shortly.",
#         )

#     # ── 2. Get LectureIndex for rag_lecture_session_id ─────────────
#     lecture_index = db.exec(
#         select(LectureIndex).where(LectureIndex.lecture_id == lecture_id)
#     ).first()

#     if not lecture_index or lecture_index.status != IndexStatus.READY:
#         raise HTTPException(
#             status_code=503,
#             detail="Lecture index is not ready. Please try again shortly.",
#         )

#     # ── 3. Load or create QASession ────────────────────────────────
#     session = _get_or_create_session(
#         db         = db,
#         student_id = student_id,
#         lecture_id = lecture_id,
#     )

#     # ── 4. Prepare the query ───────────────────────────────────────
#     voice_input_path: Optional[str] = None

#     if voice_file:
#         # Save voice file → pass absolute path to RAG
#         voice_input_path = await save_voice_file(
#             file       = voice_file,
#             student_id = student_id,
#             lecture_id = lecture_id,
#         )
#         query = voice_input_path   # RAG detects it's a path and transcribes

#     elif text:
#         query = text

#     else:
#         raise HTTPException(
#             status_code=422,
#             detail="Either text or voice_file must be provided.",
#         )

#     # ── 5. Save student QAMessage ──────────────────────────────────
#     # Save question first so it appears in history even if RAG fails
#     student_message = QAMessage(
#         session_id       = session.id,
#         role             = MessageRole.STUDENT,
#         content_text     = text if text else "[voice message]",
#         voice_input_path = voice_input_path,
#     )
#     db.add(student_message)
#     db.commit()
#     db.refresh(student_message)

#     # ── 6. Call RAG /query ─────────────────────────────────────────
#     try:
#         rag_response = await rag_client.query_lecture(
#             lecture_session_id = lecture_index.rag_lecture_session_id,
#             student_session_id = session.rag_student_session_id,
#             query              = query,
#         )
#     except RAGServiceUnavailableError as e:
#         logger.error(f"[QAService] RAG unavailable: {e}")
#         raise HTTPException(status_code=503, detail="RAG service unavailable.")
#     except RAGTimeoutError as e:
#         logger.error(f"[QAService] RAG timeout: {e}")
#         raise HTTPException(status_code=504, detail="RAG service timed out.")
#     except RAGSessionMismatchError as e:
#         logger.error(f"[QAService] Session mismatch: {e}")
#         raise HTTPException(status_code=409, detail=str(e))
#     except RAGQueryError as e:
#         logger.error(f"[QAService] RAG query error: {e}")
#         raise HTTPException(status_code=500, detail="RAG failed to generate an answer.")

#     # ── 7. Generate TTS audio ──────────────────────────────────────
#     audio_output_path: Optional[str] = None
#     try:
#         audio_output_path = await generate_audio(
#             text       = rag_response.answer,
#             student_id = student_id,
#             lecture_id = lecture_id,
#         )
#     except NotImplementedError:
#         # TTS not plugged in yet — skip audio, return text only
#         logger.warning("[QAService] TTS not implemented — skipping audio generation")
#     except Exception as e:
#         # TTS failure is non-fatal — student still gets text answer
#         logger.error(f"[QAService] TTS failed: {e}")

#     # ── 8. Save assistant QAMessage ────────────────────────────────
#     assistant_message = QAMessage(
#         session_id           = session.id,
#         role                 = MessageRole.ASSISTANT,
#         content_text         = rag_response.answer,
#         rag_answer_file_path = rag_response.answer_file,
#         audio_output_path    = audio_output_path,
#     )
#     db.add(assistant_message)

#     # ── 9. Update session last_active_at ───────────────────────────
#     session.last_active_at = datetime.utcnow()
#     db.add(session)
#     db.commit()
#     db.refresh(assistant_message)

#     logger.info(
#         f"[QAService] ✓ answered — "
#         f"student={student_id} lecture={lecture_id} "
#         f"session={session.id}"
#     )

#     # ── 10. Build response ─────────────────────────────────────────
#     return {
#         "message_id"  : assistant_message.id,
#         "session_id"  : session.id,
#         "answer_text" : rag_response.answer,
#         "audio_url"   : _build_audio_url(audio_output_path),
#         "timestamp"   : rag_response.timestamp,
#     }


# # ── History ───────────────────────────────────────────────────────────────────

# def get_history(
#     lecture_id : int,
#     student_id : int,
#     db         : Session,
#     page       : int = 1,
#     page_size  : int = 20,
# ) -> dict:
#     """
#     Load paginated chat history for a student in a lecture.
#     Returns messages in ascending order (oldest first).
#     """
#     session = db.exec(
#         select(QASession)
#         .where(
#             QASession.student_id == student_id,
#             QASession.lecture_id == lecture_id,
#         )
#     ).first()

#     if not session:
#         return {"messages": [], "total": 0, "page": page, "page_size": page_size}

#     # Total count
#     total = db.exec(
#         select(QAMessage)
#         .where(QAMessage.session_id == session.id)
#     ).all()

#     # Paginated
#     offset   = (page - 1) * page_size
#     messages = db.exec(
#         select(QAMessage)
#         .where(QAMessage.session_id == session.id)
#         .order_by(QAMessage.created_at.asc())
#         .offset(offset)
#         .limit(page_size)
#     ).all()

#     return {
#         "session_id" : session.id,
#         "messages"   : [
#             {
#                 "message_id"   : m.id,
#                 "role"         : m.role,
#                 "content_text" : m.content_text,
#                 "audio_url"    : _build_audio_url(m.audio_output_path),
#                 "timestamp"    : m.created_at.isoformat(),
#             }
#             for m in messages
#         ],
#         "total"     : len(total),
#         "page"      : page,
#         "page_size" : page_size,
#     }


# # ── Index Status ──────────────────────────────────────────────────────────────

# def get_index_status(lecture_id: int, db: Session) -> dict:
#     """
#     Return the RAG indexing status for a lecture.
#     Called by GET /qa/{lecture_id}/status
#     """
#     lecture_index = db.exec(
#         select(LectureIndex)
#         .where(LectureIndex.lecture_id == lecture_id)
#     ).first()

#     if not lecture_index:
#         return {
#             "is_indexed"   : False,
#             "status"       : "pending",
#             "ingested_at"  : None,
#             "chunks_indexed": None,
#         }

#     return {
#         "is_indexed"    : lecture_index.status == IndexStatus.READY,
#         "status"        : lecture_index.status,
#         "ingested_at"   : lecture_index.ingested_at.isoformat()
#                           if lecture_index.ingested_at else None,
#         "chunks_indexed": lecture_index.chunks_indexed,
#         "nodes_written" : lecture_index.nodes_written,
#     }


# # ── Clear Session ─────────────────────────────────────────────────────────────

# def clear_session(session_id: int, student_id: int, db: Session) -> dict:
#     """
#     Delete all messages in a student's chat session.
#     Student can only clear their own sessions.
#     """
#     session = db.get(QASession, session_id)

#     if not session:
#         raise HTTPException(status_code=404, detail="Session not found")

#     if session.student_id != student_id:
#         raise HTTPException(status_code=403, detail="Not your session")

#     # Delete all messages
#     messages = db.exec(
#         select(QAMessage).where(QAMessage.session_id == session_id)
#     ).all()

#     for message in messages:
#         db.delete(message)

#     db.delete(session)
#     db.commit()

#     return {"success": True, "session_id": session_id}


# # ── Helpers ───────────────────────────────────────────────────────────────────

# def _get_or_create_session(
#     db         : Session,
#     student_id : int,
#     lecture_id : int,
# ) -> QASession:
#     """
#     Load existing QASession or create a new one.
#     Generates rag_student_session_id as f"student_{student_id}_{lecture_id}".
#     """
#     existing = db.exec(
#         select(QASession)
#         .where(
#             QASession.student_id == student_id,
#             QASession.lecture_id == lecture_id,
#         )
#     ).first()

#     if existing:
#         return existing

#     new_session = QASession(
#         student_id             = student_id,
#         lecture_id             = lecture_id,
#         rag_student_session_id = f"student_{student_id}_{lecture_id}",
#     )
#     db.add(new_session)
#     db.commit()
#     db.refresh(new_session)

#     logger.info(
#         f"[QAService] Created new session — "
#         f"student={student_id} lecture={lecture_id} "
#         f"rag_id=student_{student_id}_{lecture_id}"
#     )

#     return new_session


# def _build_audio_url(audio_path: Optional[str]) -> Optional[str]:
#     """
#     Convert local audio file path to a URL the mobile app can call.
#     Returns None if TTS is not yet implemented or failed.
#     """
#     if not audio_path:
#         return None
#     # e.g. /static/tts_audio/student_1/lecture_5/abc123.wav
#     # Adjust this to match how you serve static files in your FastAPI app
#     from pathlib import Path
#     from app.core.config import settings
#     try:
#         rel = Path(audio_path).relative_to(Path(settings.TTS_AUDIO_DIR).resolve())
#         return f"/static/tts_audio/{rel.as_posix()}"
#     except ValueError:
#         return None



# app/services/qa_service.py

import logging
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from app.core.database import engine
from app.models.lecture import Lecture
from app.models.lecture_index import LectureIndex, IndexStatus
from app.models.qa_session import QASession
from app.models.qa_message import QAMessage, MessageRole
from app.rag_client import client as rag_client
from app.rag_client.exceptions import (
    RAGServiceUnavailableError,
    RAGTimeoutError,
    RAGQueryError,
    RAGSessionMismatchError,
)
from app.services.voice_service import save_voice_file
from app.services.tts_service import generate_audio
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)


# ── Ask ───────────────────────────────────────────────────────────────────────

async def ask(
    lecture_id : int,
    student_id : int,
    text       : Optional[str]       = None,
    voice_file : Optional[UploadFile] = None,
    db         : Session              = None,
) -> dict:
    """
    Main Q&A orchestrator.

    Accepts either text or voice input from the student.
    Returns answer text + audio URL for Stage 1.

    Flow:
      1. Verify lecture is indexed
      2. Load or create QASession
      3. Handle voice → save file → get path
      4. Call RAG /query
      5. Save QAMessage rows (student + assistant)
      6. Generate TTS audio
      7. Return response to router
    """

    # ── 1. Verify lecture exists and is indexed ────────────────────
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    if not lecture.is_indexed:
        raise HTTPException(
            status_code=503,
            detail="Lecture is not indexed yet. Please try again shortly.",
        )

    # ── 2. Get LectureIndex for rag_lecture_session_id ─────────────
    lecture_index = db.exec(
        select(LectureIndex).where(LectureIndex.lecture_id == lecture_id)
    ).first()

    if not lecture_index or lecture_index.status != IndexStatus.READY:
        raise HTTPException(
            status_code=503,
            detail="Lecture index is not ready. Please try again shortly.",
        )

    # ── 3. Load or create QASession ────────────────────────────────
    session = _get_or_create_session(
        db         = db,
        student_id = student_id,
        lecture_id = lecture_id,
    )

    # ── 4. Prepare the query ───────────────────────────────────────
    voice_input_path: Optional[str] = None

    if voice_file:
        # Save voice file → pass absolute path to RAG
        voice_input_path = await save_voice_file(
            file       = voice_file,
            student_id = student_id,
            lecture_id = lecture_id,
        )
        query = voice_input_path   # RAG detects it's a path and transcribes

    elif text:
        query = text

    else:
        raise HTTPException(
            status_code=422,
            detail="Either text or voice_file must be provided.",
        )

    # ── 5. Save student QAMessage ──────────────────────────────────
    # Save question first so it appears in history even if RAG fails
    student_message = QAMessage(
        session_id       = session.id,
        role             = MessageRole.STUDENT,
        content_text     = text if text else "[voice message]",
        voice_input_path = voice_input_path,
    )
    db.add(student_message)
    db.commit()
    db.refresh(student_message)

    # ── 6. Call RAG /query ─────────────────────────────────────────
    try:
        rag_response = await rag_client.query_lecture(
            lecture_session_id = lecture_index.rag_lecture_session_id,
            student_session_id = session.rag_student_session_id,
            query              = query,
        )
    except RAGServiceUnavailableError as e:
        logger.error(f"[QAService] RAG unavailable: {e}")
        raise HTTPException(status_code=503, detail="RAG service unavailable.")
    except RAGTimeoutError as e:
        logger.error(f"[QAService] RAG timeout: {e}")
        raise HTTPException(status_code=504, detail="RAG service timed out.")
    except RAGSessionMismatchError as e:
        logger.error(f"[QAService] Session mismatch: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except RAGQueryError as e:
        logger.error(f"[QAService] RAG query error: {e}")
        raise HTTPException(status_code=500, detail="RAG failed to generate an answer.")

    # ── 7. Generate TTS audio ──────────────────────────────────────
    audio_output_path: Optional[str] = None
    try:
        # Load teacher's voice reference
        from app.models.teacher import Teacher
        teacher = db.get(Teacher, lecture.teacher_id)

        audio_output_path = await generate_audio(
            text       = rag_response.answer,
            student_id = student_id,
            lecture_id = lecture_id,
            teacher_id = lecture.teacher_id,
            voice_ref  = teacher.voice_sample if teacher else None,
        )
    except Exception as e:
        # Non-fatal — student still gets text answer
        logger.error(f"[QAService] TTS failed: {e}")

    # ── 8. Save assistant QAMessage ────────────────────────────────
    assistant_message = QAMessage(
        session_id           = session.id,
        role                 = MessageRole.ASSISTANT,
        content_text         = rag_response.answer,
        rag_answer_file_path = rag_response.answer_file,
        audio_output_path    = audio_output_path,
    )
    db.add(assistant_message)

    # ── 9. Update session last_active_at ───────────────────────────
    session.last_active_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(assistant_message)

    logger.info(
        f"[QAService] ✓ answered — "
        f"student={student_id} lecture={lecture_id} "
        f"session={session.id}"
    )

    # ── 10. Build response ─────────────────────────────────────────
    return {
        "message_id"  : assistant_message.id,
        "session_id"  : session.id,
        "answer_text" : rag_response.answer,
        "audio_url"   : _build_audio_url(audio_output_path),
        "timestamp"   : rag_response.timestamp,
    }


# ── History ───────────────────────────────────────────────────────────────────

def get_history(
    lecture_id : int,
    student_id : int,
    db         : Session,
    page       : int = 1,
    page_size  : int = 20,
) -> dict:
    """
    Load paginated chat history for a student in a lecture.
    Returns messages in ascending order (oldest first).
    """
    session = db.exec(
        select(QASession)
        .where(
            QASession.student_id == student_id,
            QASession.lecture_id == lecture_id,
        )
    ).first()

    if not session:
        return {"messages": [], "total": 0, "page": page, "page_size": page_size}

    # Total count
    total = db.exec(
        select(QAMessage)
        .where(QAMessage.session_id == session.id)
    ).all()

    # Paginated
    offset   = (page - 1) * page_size
    messages = db.exec(
        select(QAMessage)
        .where(QAMessage.session_id == session.id)
        .order_by(QAMessage.created_at.asc())
        .offset(offset)
        .limit(page_size)
    ).all()

    return {
        "session_id" : session.id,
        "messages"   : [
            {
                "message_id"   : m.id,
                "role"         : m.role,
                "content_text" : m.content_text,
                "audio_url"    : _build_audio_url(m.audio_output_path),
                "timestamp"    : m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total"     : len(total),
        "page"      : page,
        "page_size" : page_size,
    }


# ── Index Status ──────────────────────────────────────────────────────────────

def get_index_status(lecture_id: int, db: Session) -> dict:
    """
    Return the RAG indexing status for a lecture.
    Called by GET /qa/{lecture_id}/status
    """
    lecture_index = db.exec(
        select(LectureIndex)
        .where(LectureIndex.lecture_id == lecture_id)
    ).first()

    if not lecture_index:
        return {
            "is_indexed"   : False,
            "status"       : "pending",
            "ingested_at"  : None,
            "chunks_indexed": None,
        }

    return {
        "is_indexed"    : lecture_index.status == IndexStatus.READY,
        "status"        : lecture_index.status,
        "ingested_at"   : lecture_index.ingested_at.isoformat()
                          if lecture_index.ingested_at else None,
        "chunks_indexed": lecture_index.chunks_indexed,
        "nodes_written" : lecture_index.nodes_written,
    }


# ── Clear Session ─────────────────────────────────────────────────────────────

def clear_session(session_id: int, student_id: int, db: Session) -> dict:
    """
    Delete all messages in a student's chat session.
    Student can only clear their own sessions.
    """
    session = db.get(QASession, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.student_id != student_id:
        raise HTTPException(status_code=403, detail="Not your session")

    # Delete all messages
    messages = db.exec(
        select(QAMessage).where(QAMessage.session_id == session_id)
    ).all()

    for message in messages:
        db.delete(message)

    db.delete(session)
    db.commit()

    return {"success": True, "session_id": session_id}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_session(
    db         : Session,
    student_id : int,
    lecture_id : int,
) -> QASession:
    """
    Load existing QASession or create a new one.
    Generates rag_student_session_id as f"student_{student_id}_{lecture_id}".
    """
    existing = db.exec(
        select(QASession)
        .where(
            QASession.student_id == student_id,
            QASession.lecture_id == lecture_id,
        )
    ).first()

    if existing:
        return existing

    new_session = QASession(
        student_id             = student_id,
        lecture_id             = lecture_id,
        rag_student_session_id = f"student_{student_id}_{lecture_id}",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(
        f"[QAService] Created new session — "
        f"student={student_id} lecture={lecture_id} "
        f"rag_id=student_{student_id}_{lecture_id}"
    )

    return new_session


def _build_audio_url(audio_path: Optional[str]) -> Optional[str]:
    """
    Convert local audio file path to a URL the mobile app can call.
    Returns None if TTS is not yet implemented or failed.
    """
    if not audio_path:
        return None
    # e.g. /static/tts_audio/student_1/lecture_5/abc123.wav
    # Adjust this to match how you serve static files in your FastAPI app
    from pathlib import Path
    from app.core.config import settings
    try:
        rel = Path(audio_path).relative_to(Path(settings.TTS_AUDIO_DIR).resolve())
        return f"/static/tts_audio/{rel.as_posix()}"
    except ValueError:
        return None