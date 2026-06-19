# app/api/v1/endpoints/identity.py
"""
Live-capture identity verification, called by Flutter right before a
teacher taps "Generate" — and re-checked independently by trigger-pipeline
(Phase 5) before any ARQ job is actually enqueued.

This endpoint only answers "did this check pass" for the UI. It does not
gate generation by itself — that enforcement lives in trigger-pipeline,
which re-queries IdentityVerification rather than trusting the client to
have called this first.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

from app.core.database import get_session
from app.api.deps import get_current_teacher   # returns a User with role == TEACHER

from app.core.config import settings
from app.models.user import User
from app.models.teacher import Teacher
from app.models.lecture import Lecture
from app.models.identity_verification import IdentityVerification, IdentityVerificationPublic
from app.services.face_verification import (
    extract_embedding,
    embedding_from_json,
    verify,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    FaceVerificationError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/lecture/{lecture_id}/verify-identity", response_model=IdentityVerificationPublic)
async def verify_identity(
    lecture_id: int,
    capture: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_teacher),
) -> IdentityVerificationPublic:

    # ── Ownership check: this lecture must belong to this teacher ──
    # current_user.user_id and Lecture.teacher_id share the same id space
    # as Teacher.user_id, so this check works directly off the User —
    # no need to load the Teacher row just for this part.
    lecture = session.get(Lecture, lecture_id)
    if not lecture or lecture.teacher_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    # ── Load the Teacher row ────────────────────────────────────────
    # get_current_teacher returns a User, but reference_embedding lives
    # on Teacher — same primary key value, separate table.
    teacher = session.get(Teacher, current_user.user_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher profile not found.")

    if not teacher.reference_embedding:
        raise HTTPException(
            status_code=400,
            detail="No reference photo on file. Please complete onboarding first.",
        )

    # ── Save the live capture with a unique filename ───────────────
    # Same concurrency lesson as audio extraction — never reuse a fixed
    # name, two teachers verifying at once would otherwise collide.
    capture_dir = Path(settings.UPLOADS_DIR) / "identity_checks" / str(teacher.user_id)
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / f"{uuid.uuid4().hex}.jpg"

    contents = await capture.read()
    capture_path.write_bytes(contents)

    # ── Extract the live capture's embedding ────────────────────────
    # No-face / multiple-face cases are input-quality problems, not
    # identity verdicts — deliberately NOT logged to IdentityVerification.
    # That table only records actual comparisons (see below).
    try:
        live_embedding = extract_embedding(str(capture_path))
    except NoFaceDetectedError:
        logger.warning(f"[VerifyIdentity:{teacher.user_id}] No face detected in live capture")
        raise HTTPException(
            status_code=422,
            detail="No face detected. Please retake with your face clearly visible.",
        )
    except MultipleFacesDetectedError as e:
        logger.warning(f"[VerifyIdentity:{teacher.user_id}] {e}")
        raise HTTPException(
            status_code=422,
            detail="More than one face detected. Make sure only you are in frame.",
        )
    except FaceVerificationError as e:
        logger.error(f"[VerifyIdentity:{teacher.user_id}] Extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Could not process the photo. Please try again.")

    # ── Compare against the stored reference ────────────────────────
    reference_embedding = embedding_from_json(teacher.reference_embedding)
    result = verify(reference_embedding, live_embedding)

    # ── Log the attempt — every real comparison, pass or fail ───────
    record = IdentityVerification(
        teacher_id=teacher.user_id,
        lecture_id=lecture_id,
        distance=result.distance,
        passed=result.passed,
        captured_image_path=str(capture_path),
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    logger.info(
        f"[VerifyIdentity:{teacher.user_id}] lecture={lecture_id} "
        f"distance={result.distance:.4f} passed={result.passed}"
    )

    return IdentityVerificationPublic(
        passed=result.passed,
        distance=result.distance,
        created_at=record.created_at,
    )