# from sqlmodel import Field, SQLModel, Relationship
# from typing import Optional, List, TYPE_CHECKING

# if TYPE_CHECKING:
#     from app.models.user import User
#     from app.models.schedule import Schedule
#     from app.models.course import Course
#     from app.models.lecture import Lecture

# class TeacherBase(SQLModel):
#     photo: Optional[str] = None  # Path to uploaded photo
#     voice_sample: Optional[str] = None  # Path to uploaded voice sample

# class Teacher(TeacherBase, table=True):
#     __tablename__ = "teachers"
    
#     user_id: int = Field(foreign_key="users.user_id", primary_key=True)
    
#     user: Optional["User"] = Relationship(back_populates="teacher")
#     courses: List["Course"] = Relationship(back_populates="teacher")
#     lectures: List["Lecture"] = Relationship(back_populates="teacher")



# class TeacherCreate(TeacherBase):
#     pass

# class TeacherPublic(TeacherBase):
#     user_id: int

# class TeacherUpdate(SQLModel):
#     photo: Optional[str] = None
#     voice_sample: Optional[str] = None

# class TeacherProfileStatus(SQLModel):
#     needs_profile_setup: bool
#     has_photo: bool
#     has_voice_sample: bool

# app/models/teacher.py
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.schedule import Schedule
    from app.models.course import Course
    from app.models.lecture import Lecture


class TeacherBase(SQLModel):
    photo: Optional[str] = None         # Path to uploaded raw photo
    voice_sample: Optional[str] = None  # Path to uploaded voice sample


class Teacher(TeacherBase, table=True):
    __tablename__ = "teachers"

    user_id: int = Field(foreign_key="users.user_id", primary_key=True)

    # ── Onboarding / Preprocessing ─────────────────────────────────
    # Set to 'processing' when photo is uploaded and preprocess_image.py starts.
    # Set to 'ready' by the onboarding worker on success.
    # Set to 'failed' by the onboarding worker on failure.
    onboarding_status: str = Field(default="pending")

    # Written by onboarding worker after preprocess_image.py succeeds.
    # Passed to the avatar pipeline via --preprocessed-image flag.
    preprocessed_image_path: Optional[str] = Field(default=None)

    # Optional speedup: pre-baked .pt voice file from a previous TTS run.
    # If present, skips ~30s voice cloning on subsequent generation jobs.
    cached_voice_path: Optional[str] = Field(default=None)
    reference_embedding: Optional[str] = Field(default=None)

    # ── Relationships ──────────────────────────────────────────────
    user: Optional["User"] = Relationship(back_populates="teacher")
    courses: List["Course"] = Relationship(back_populates="teacher")
    lectures: List["Lecture"] = Relationship(back_populates="teacher")


class TeacherCreate(TeacherBase):
    pass


class TeacherPublic(TeacherBase):
    user_id: int
    onboarding_status: str  # frontend needs this to show preprocessing state


class TeacherUpdate(SQLModel):
    photo: Optional[str] = None
    voice_sample: Optional[str] = None


class TeacherProfileStatus(SQLModel):
    needs_profile_setup: bool
    has_photo: bool
    has_voice_sample: bool
    onboarding_status: str  # pending | processing | ready | failed