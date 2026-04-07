# from sqlmodel import Field, SQLModel, Relationship
# from typing import Optional, List, TYPE_CHECKING
# from enum import Enum

# if TYPE_CHECKING:
#     from app.models.teacher import Teacher
#     from app.models.course import Course
#     from app.models.resource import Resource
#     from app.models.schedule import Schedule


# class LectureType(str, Enum):
#     PREPARED = "prepared"  # Teacher uploaded ready lecture
#     GENERATED = "generated"  # LLM generated from resources


# class LectureStatus(str, Enum):
#     DRAFT = "draft"  # Being created
#     GENERATING = "generating"  # LLM is generating
#     COMPLETED = "completed"  # Ready to use
#     FAILED = "failed"  # Generation failed


# class LectureBase(SQLModel):
#     """Base lecture schema - shared fields"""
#     title: str = Field(max_length=200)
#     lecture_type: LectureType = Field(default=LectureType.PREPARED)
#     status: LectureStatus = Field(default=LectureStatus.DRAFT)
#     final_content: Optional[str] = None  # URL to final lecture (Drive link)


# class Lecture(LectureBase, table=True):
#     """Database model"""
#     __tablename__ = "lectures"
    
#     lecture_id: Optional[int] = Field(default=None, primary_key=True)
#     teacher_id: int = Field(foreign_key="teachers.user_id")
#     course_code: str = Field(foreign_key="courses.course_code", max_length=50)
    
#     # Relationships
#     teacher: Optional["Teacher"] = Relationship(back_populates="lectures")
#     course: Optional["Course"] = Relationship(back_populates="lectures")
#     resources: List["Resource"] = Relationship(back_populates="lecture")
#     schedules: List["Schedule"] = Relationship(back_populates="lecture")


# class LectureCreate(SQLModel):
#     """For creating a new lecture"""
#     title: str
#     course_code: str
#     lecture_type: LectureType = LectureType.PREPARED
#     final_content: Optional[str] = None  # For prepared lectures (Drive URL)


# class LecturePublic(LectureBase):
#     """Public lecture information"""
#     lecture_id: int
#     teacher_id: int
#     course_code: str


# class LectureUpdate(SQLModel):
#     """For updating a lecture"""
#     title: Optional[str] = None
#     status: Optional[LectureStatus] = None
#     final_content: Optional[str] = None
#     lecture_type: Optional[LectureType] = None


# class LectureWithDetails(LecturePublic):
#     """Lecture with teacher, course and resources info"""
#     teacher_name: Optional[str] = None
#     course_title: Optional[str] = None
#     resource_count: int = 0

# app/models/lecture.py
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from app.models.teacher import Teacher
    from app.models.course import Course
    from app.models.resource import Resource
    from app.models.schedule import Schedule


class LectureType(str, Enum):
    PREPARED  = "prepared"   # Teacher uploaded a ready-made lecture (Drive)
    GENERATED = "generated"  # Avatar pipeline generates from script


class LectureStatus(str, Enum):
    DRAFT      = "draft"       # Being created / script not ready yet
    GENERATING = "generating"  # Pipeline is running (TTS + avatar)
    COMPLETED  = "completed"   # Avatar MP4 is ready
    FAILED     = "failed"      # Pipeline crashed — see error_message


class LectureBase(SQLModel):
    """Shared fields used across request/response schemas."""
    title: str = Field(max_length=200)
    lecture_type: LectureType   = Field(default=LectureType.PREPARED)
    status:       LectureStatus = Field(default=LectureStatus.DRAFT)
    final_content: Optional[str] = None  # Google Drive URL — PREPARED lectures only


class Lecture(LectureBase, table=True):
    """Database table — includes all pipeline fields."""
    __tablename__ = "lectures"

    lecture_id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: int            = Field(foreign_key="teachers.user_id")
    course_code: str           = Field(foreign_key="courses.course_code", max_length=50)

    # ── Pipeline inputs ────────────────────────────────────────────
    # Set by the upstream extraction/LLM module before trigger-pipeline is called.

    # Absolute path to the .txt script on disk.
    # This is the handoff point — upstream writes it, worker reads it.
    script_path: Optional[str] = Field(default=None)

    # Avatar generation quality parameters.
    # Defaults are sensible — upstream module only needs to set these
    # if it wants non-default quality/style.
    num_steps:  int   = Field(default=20)           # denoising steps (more = slower but better)
    audio_cfg:  float = Field(default=4.0)          # audio guidance scale
    text_cfg:   float = Field(default=4.0)          # text guidance scale
    seed:       int   = Field(default=42)           # reproducibility seed
    preset:     str   = Field(default="engaging_narration")  # speaking style preset
    # Backend override — overrides settings.AVATAR_BACKEND for this specific lecture.
    # "local" = GPU on this machine | "fal" = fal.ai cloud API
    avatar_backend: str = Field(default="local")
    # ── Pipeline outputs ───────────────────────────────────────────
    # Written by the generation worker after the subprocess finishes.

    # Absolute path to the generated avatar_*.mp4.
    # Populated on COMPLETED. Read by GET /lecture/{id}/video to serve the file.
    output_video_path: Optional[str] = Field(default=None)

    # Last 2000 chars of subprocess stderr on FAILED.
    # Stored here so failures are debuggable without digging through server logs.
    error_message: Optional[str] = Field(default=None)

    # ── Timing ─────────────────────────────────────────────────────
    # Written by worker. Useful for progress display and performance tracking.
    started_at:   Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # ── Relationships ──────────────────────────────────────────────
    teacher:   Optional["Teacher"]  = Relationship(back_populates="lectures")
    course:    Optional["Course"]   = Relationship(back_populates="lectures")
    resources: List["Resource"]     = Relationship(back_populates="lecture")
    schedules: List["Schedule"]     = Relationship(back_populates="lecture")


# ── Request Schemas ────────────────────────────────────────────────────────────

class LectureCreate(SQLModel):
    """For creating a new lecture draft."""
    title: str
    course_code: str
    lecture_type: LectureType   = LectureType.PREPARED
    final_content: Optional[str] = None  # Drive URL — for PREPARED lectures


class LectureUpdate(SQLModel):
    """For updating basic lecture metadata."""
    title:         Optional[str]           = None
    status:        Optional[LectureStatus] = None
    final_content: Optional[str]           = None
    lecture_type:  Optional[LectureType]   = None


# ── Response Schemas ───────────────────────────────────────────────────────────

class LecturePublic(LectureBase):
    """
    Full lecture info returned to the frontend.
    Includes pipeline state so the UI can show generation progress.
    """
    lecture_id:   int
    teacher_id:   int
    course_code:  str

    # Pipeline state — frontend polls these to track generation progress
    script_path:       Optional[str]      = None
    output_video_path: Optional[str]      = None
    error_message:     Optional[str]      = None
    started_at:        Optional[datetime] = None
    completed_at:      Optional[datetime] = None
    avatar_backend: str = "local"

class LectureWithDetails(LecturePublic):
    """Lecture with denormalized teacher/course info for list views."""
    teacher_name:   Optional[str] = None
    course_title:   Optional[str] = None
    resource_count: int           = 0


class LecturePipelineTriggerResponse(SQLModel):
    """
    Response from POST /lecture/{id}/trigger-pipeline.
    Confirms the generation job was accepted and queued.
    """
    lecture_id: int
    status:     str   # always "queued" on success
    message:    str   # human-readable confirmation