# app/models/identity_verification.py
"""
Audit trail for ArcFace identity checks at hologram-generation time.

One row per verify-identity call, not per lecture — a teacher can retry
after a failed attempt, and every attempt should be logged, not just the
final outcome. trigger-pipeline's guard (Phase 5) queries the most recent
PASSED row for a given lecture_id within a TTL window before allowing a
job to be enqueued.

Deliberately has no relationship fields back to Teacher or Lecture — the
guard query is a direct filter on teacher_id + lecture_id, so an ORM
relationship would add coupling with no functional benefit.
"""

from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime


class IdentityVerification(SQLModel, table=True):
    __tablename__ = "identity_verifications"

    id: Optional[int] = Field(default=None, primary_key=True)

    teacher_id: int = Field(foreign_key="teachers.user_id", index=True)
    lecture_id: int = Field(foreign_key="lectures.lecture_id", index=True)

    # Cosine distance from face_verification.verify() — lower is better.
    # Kept even on failed attempts, useful for later threshold tuning.
    distance: float
    passed: bool

    # Path to the live-capture image used for this attempt. Must be saved
    # with a unique filename per request — same concurrency lesson as the
    # audio extraction fix, hardcoded names will collide under load.
    # Optional so a future cleanup job can null this out after a retention
    # window without breaking the audit row itself.
    captured_image_path: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class IdentityVerificationPublic(SQLModel):
    """What the verify-identity endpoint returns to Flutter."""
    passed: bool
    distance: float
    created_at: datetime