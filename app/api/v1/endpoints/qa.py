# app/api/v1/endpoints/qa.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlmodel import Session
from typing import Optional
from pathlib import Path

from app.core.database import get_session
from app.models.user import User
from app.api.deps import get_current_user
from app.services import qa_service

router = APIRouter()


# ============================================
# 1: Ask a Question
# ============================================

@router.post("/{lecture_id}/ask", status_code=status.HTTP_200_OK)
async def ask_question(
    lecture_id  : int,
    text        : Optional[str]        = Form(default=None),
    voice_file  : Optional[UploadFile] = File(default=None),
    session     : Session              = Depends(get_session),
    current_user: User                 = Depends(get_current_user),
):
    """
    Student asks a question about a lecture.

    Accepts either:
      - text  — plain text question (Form field)
      - voice_file — audio file (Flutter records and sends)

    Returns answer text + audio URL (Stage 1).
    """
    if not text and not voice_file:
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail      = "Either text or voice_file must be provided.",
        )

    return await qa_service.ask(
        lecture_id  = lecture_id,
        student_id  = current_user.user_id,
        text        = text,
        voice_file  = voice_file,
        db          = session,
    )


# ============================================
# 2: Get Chat History
# ============================================

@router.get("/{lecture_id}/history", status_code=status.HTTP_200_OK)
async def get_history(
    lecture_id  : int,
    page        : int     = 1,
    page_size   : int     = 20,
    session     : Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """
    Load paginated chat history for this student in this lecture.
    Messages returned oldest first.
    """
    return qa_service.get_history(
        lecture_id = lecture_id,
        student_id = current_user.user_id,
        db         = session,
        page       = page,
        page_size  = page_size,
    )


# ============================================
# 3: Check Index Status
# ============================================

@router.get("/{lecture_id}/status", status_code=status.HTTP_200_OK)
async def get_index_status(
    lecture_id  : int,
    session     : Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """
    Check if a lecture is indexed and ready for Q&A.
    Mobile app polls this before showing the Q&A chat UI.

    Returns:
      is_indexed    — bool
      status        — pending / ingesting / ready / failed
      ingested_at   — timestamp or null
      chunks_indexed — int or null
    """
    return qa_service.get_index_status(
        lecture_id = lecture_id,
        db         = session,
    )


# ============================================
# 4: Stream Answer Audio
# ============================================

@router.get("/audio/{message_id}", status_code=status.HTTP_200_OK)
async def stream_answer_audio(
    message_id  : int,
    session     : Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """
    Stream the TTS audio file for a specific answer message.
    Called by Flutter to play the answer audio.
    """
    from sqlmodel import select
    from app.models.qa_message import QAMessage, MessageRole
    from app.models.qa_session import QASession

    message = session.get(QAMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Verify ownership — student can only access their own messages
    qa_session = session.get(QASession, message.session_id)
    if not qa_session or qa_session.student_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your message")

    if message.role != MessageRole.ASSISTANT:
        raise HTTPException(status_code=400, detail="Audio only available for assistant messages")

    if not message.audio_output_path:
        raise HTTPException(
            status_code=404,
            detail="Audio not available for this message."
        )

    audio_path = Path(message.audio_output_path)
    if not audio_path.exists():
        raise HTTPException(
            status_code=410,
            detail="Audio file no longer available on disk."
        )

    return FileResponse(
        path      = str(audio_path),
        media_type = "audio/wav",
        filename  = f"answer_{message_id}.wav",
    )


# ============================================
# 5: Clear Session
# ============================================

@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def clear_session(
    session_id  : int,
    session     : Session = Depends(get_session),
    current_user: User    = Depends(get_current_user),
):
    """
    Clear a student's chat session for a lecture.
    Deletes all messages in the session.
    """
    return qa_service.clear_session(
        session_id = session_id,
        student_id = current_user.user_id,
        db         = session,
    )