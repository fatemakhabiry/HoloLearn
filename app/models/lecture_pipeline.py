# app/models/lecture_pipeline.py
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from app.models.lecture import Lecture


class PipelineStatus(str, Enum):
    QUEUED     = "queued"      # Job accepted, waiting in Redis queue
    GENERATING = "generating"  # Subprocess is running
    COMPLETED  = "completed"   # avatar_*.mp4 produced successfully
    FAILED     = "failed"      # Subprocess crashed or no output found


class LecturePipeline(SQLModel, table=True):
    """
    Pipeline job record for a GENERATED lecture.

    Created when trigger-pipeline is called.
    Updated by the generation worker as the job progresses.
    One-to-one with Lecture — each lecture has at most one pipeline record.
    """
    __tablename__ = "lecture_pipelines"

    # One-to-one with Lecture
    lecture_id: int = Field(foreign_key="lectures.lecture_id", primary_key=True)

    # ── Status ─────────────────────────────────────────────────────
    status: PipelineStatus = Field(default=PipelineStatus.QUEUED)

    # ── Pipeline inputs ────────────────────────────────────────────
    # Set by upstream extraction/LLM module before trigger-pipeline is called.
    script_path:    Optional[str] = Field(default=None)  # abs path to .txt script
    num_steps:      int           = Field(default=20)
    audio_cfg:      float         = Field(default=4.0)
    text_cfg:       float         = Field(default=4.0)
    seed:           int           = Field(default=42)
    preset:         str           = Field(default="engaging_narration")
    avatar_backend: str           = Field(default="local")

    # ── Pipeline outputs ───────────────────────────────────────────
    # Written by generation worker after subprocess finishes.
    output_video_path: Optional[str] = Field(default=None)  # abs path to avatar_*.mp4
    error_message:     Optional[str] = Field(default=None)  # last 2000 chars of stderr

    # Written by run_tts job as soon as TTS finishes — independent of
    # output_video_path, which is only set later once LongCAT completes.
    # Presence of this field (not pipeline.status) is what tells the
    # student app "transcript is ready", since TTS finishes well before
    # avatar generation does.
    transcript_path: Optional[str] = Field(default=None)    # abs path to transcript.txt

    # Written by run_tts at the same time as transcript_path, BEFORE
    # enqueueing run_generation. Without this persisted, audio_path only
    # exists as an in-memory ARQ job argument — if run_generation fails
    # (GPU unreachable, ngrok drop, timeout) there would be no way to find
    # the already-generated audio again to retry sending it. This field is
    # what makes that retry possible without re-running TTS.
    audio_path: Optional[str] = Field(default=None)         # abs path to audio.wav

    # ── Timing ─────────────────────────────────────────────────────
    created_at:   datetime           = Field(default_factory=datetime.utcnow)
    started_at:   Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # ── Relationship ───────────────────────────────────────────────
    lecture: Optional["Lecture"] = Relationship(back_populates="pipeline")


class LecturePipelinePublic(SQLModel):
    """What the frontend sees when checking pipeline state."""
    lecture_id:        int
    status:            PipelineStatus
    script_path:       Optional[str]      = None
    audio_path:        Optional[str]      = None
    output_video_path: Optional[str]      = None
    transcript_path:   Optional[str]      = None
    error_message:     Optional[str]      = None
    avatar_backend:    str
    preset:            str
    created_at:        datetime
    started_at:        Optional[datetime] = None
    completed_at:      Optional[datetime] = None


class LecturePipelineCreate(SQLModel):
    """Used by upstream module to create the pipeline record."""
    lecture_id:     int
    script_path:    Optional[str] = None
    num_steps:      int           = 20
    audio_cfg:      float         = 4.0
    text_cfg:       float         = 4.0
    seed:           int           = 42
    preset:         str           = "engaging_narration"
    avatar_backend: str           = "local"


class LecturePipelineUpdate(SQLModel):
    """Used by upstream module to set/update script_path and params."""
    script_path:    Optional[str]   = None
    num_steps:      Optional[int]   = None
    audio_cfg:      Optional[float] = None
    text_cfg:       Optional[float] = None
    seed:           Optional[int]   = None
    preset:         Optional[str]   = None
    avatar_backend: Optional[str]   = None