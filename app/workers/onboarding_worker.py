# app/workers/onboarding_worker.py
import subprocess
import logging
from pathlib import Path
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.models.teacher import Teacher
from app.services.face_verification import (
    extract_embedding,
    embedding_to_json,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    FaceVerificationError,
)

logger = logging.getLogger(__name__)


def run_onboarding(teacher_id: int, raw_image_path: str) -> None:
    """
    Background task — runs after a teacher uploads their photo.

    Does two independent things with the raw photo:
      1. Extracts an ArcFace reference embedding for identity verification
         at generation time (Phase 3 of the face-recognition feature).
      2. Calls preprocess_image.py (in the longcat-video conda env) to
         produce a face-aligned image the avatar pipeline can use.

    These are deliberately independent — embedding extraction doesn't need
    LONGCAT_ENV_PYTHON or the GPU machine, so identity verification keeps
    working even before the avatar pipeline is configured on this machine.

    On success → teacher.onboarding_status = 'ready'
                 teacher.preprocessed_image_path = absolute path to *_preprocessed.png
                 teacher.reference_embedding = JSON-encoded 512-dim ArcFace embedding

    On failure → teacher.onboarding_status = 'failed'
                 Teacher must re-upload their photo to retry.

    Args:
        teacher_id:      Teacher's user_id (primary key in teachers table)
        raw_image_path:  Absolute path to the saved raw.jpg on disk
    """

    # ── Identity verification: extract reference embedding ─────────
    # Best-effort: a failure here doesn't block the rest of onboarding,
    # it just means verify-identity will reject this teacher until they
    # re-upload a clearer photo. Logged separately from onboarding_status
    # because this isn't part of the avatar-preprocessing pipeline below.
    try:
        embedding = extract_embedding(raw_image_path)
        _store_reference_embedding(teacher_id, embedding_to_json(embedding))
        logger.info(f"[Onboarding:{teacher_id}] Reference embedding stored ({len(embedding)} dims)")
    except NoFaceDetectedError:
        logger.warning(
            f"[Onboarding:{teacher_id}] No face detected in {raw_image_path} — "
            "reference_embedding not set. Teacher must re-upload a clearer photo."
        )
    except MultipleFacesDetectedError as e:
        logger.warning(f"[Onboarding:{teacher_id}] {e} — reference_embedding not set.")
    except FaceVerificationError as e:
        logger.error(f"[Onboarding:{teacher_id}] Embedding extraction failed: {e} — reference_embedding not set.")

    # ── Guard: pipeline must be configured ────────────────────────
    # If config paths are missing (dev machine without pipeline installed),
    # leave status as 'pending' — the photo is saved and can be preprocessed
    # once the pipeline is set up. This is NOT a teacher failure.
    if not settings.PREPROCESS_SCRIPT or not settings.LONGCAT_ENV_PYTHON:
        logger.warning(
            f"[Onboarding:{teacher_id}] Pipeline not configured — skipping preprocessing. "
            "Set PREPROCESS_SCRIPT and LONGCAT_ENV_PYTHON in .env to enable it. "
            "Photo has been saved successfully."
        )
        _set_status(teacher_id, "pending", preprocessed_path=None)
        return

    # ── Resolve output paths ──────────────────────────────────────
    # preprocess_image.py uses --output <file>, not --output-dir.
    # We write <stem>_preprocessed.png next to the raw image so the
    # glob("*_preprocessed.png") below can always find it.
    # e.g. uploads/instructors/12/raw.jpg  →  raw_preprocessed.png
    input_path = Path(raw_image_path)
    output_dir = input_path.parent
    output_file = output_dir / (input_path.stem + "_preprocessed.png")

    # ── Build subprocess command ───────────────────────────────────
    # We call the longcat-video venv Python directly so we get that
    # environment's dependencies (PyTorch, face detection models, etc.)
    cmd = [
        settings.LONGCAT_ENV_PYTHON,       # D:/Hololearn/long cat/LongCat-Video/venv/Scripts/python.exe
        settings.PREPROCESS_SCRIPT,        # D:/Hololearn/long cat/LongCat-Video/preprocess_image.py
        "--input",  raw_image_path,        # absolute path to raw.jpg
        "--output", str(output_file),      # absolute path for the output PNG
    ]

    logger.info(f"[Onboarding:{teacher_id}] Starting preprocessing → {raw_image_path}")

    # ── Run subprocess ─────────────────────────────────────────────
    # cwd = LongCat script directory so relative imports inside the script work
    # capture_output = True captures both stdout and stderr
    # text = True gives us strings instead of bytes
    try:
        result = subprocess.run(
            cmd,
            cwd=settings.LONGCAT_SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300,   # 5 minute hard limit — preprocessing shouldn't take longer
        )
    except subprocess.TimeoutExpired:
        logger.error(f"[Onboarding:{teacher_id}] Preprocessing timed out after 5 minutes")
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return
    except Exception as e:
        logger.error(f"[Onboarding:{teacher_id}] Subprocess launch failed: {e}")
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # ── Check exit code ────────────────────────────────────────────
    if result.returncode != 0:
        logger.error(
            f"[Onboarding:{teacher_id}] preprocess_image.py failed "
            f"(exit {result.returncode}):\n{result.stderr[-1000:]}"
        )
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # ── Find the output file ───────────────────────────────────────
    # preprocess_image.py names its output based on input filename,
    # typically raw_preprocessed.png — glob to find it safely.
    preprocessed_files = sorted(output_dir.glob("*_preprocessed.png"))

    if not preprocessed_files:
        # Script exited 0 but produced no output — treat as failure
        logger.error(
            f"[Onboarding:{teacher_id}] preprocess_image.py exited 0 "
            "but no *_preprocessed.png found in output dir"
        )
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # Take the most recently modified one (handles re-uploads correctly)
    preprocessed_path = str(preprocessed_files[-1].resolve())

    logger.info(f"[Onboarding:{teacher_id}] Preprocessing complete → {preprocessed_path}")
    _set_status(teacher_id, "ready", preprocessed_path=preprocessed_path)


def _set_status(
    teacher_id: int,
    status: str,
    preprocessed_path: str | None
) -> None:
    """
    Open a fresh DB session and update the teacher's onboarding fields.

    This runs outside the original HTTP request/session lifecycle,
    so we must create our own session directly from the engine.
    """
    with Session(engine) as session:
        teacher = session.get(Teacher, teacher_id)

        if not teacher:
            logger.error(
                f"[Onboarding:{teacher_id}] Teacher not found in DB "
                "when trying to update onboarding status"
            )
            return

        teacher.onboarding_status = status

        if preprocessed_path is not None:
            teacher.preprocessed_image_path = preprocessed_path

        session.add(teacher)
        session.commit()

        logger.info(f"[Onboarding:{teacher_id}] DB updated → onboarding_status='{status}'")


def _store_reference_embedding(teacher_id: int, embedding_json: str) -> None:
    """
    Open a fresh DB session and store the teacher's reference embedding.

    Deliberately separate from _set_status() — onboarding_status reflects
    the avatar-preprocessing pipeline, not identity verification. The two
    succeed or fail independently, so they shouldn't share a write path.
    """
    with Session(engine) as session:
        teacher = session.get(Teacher, teacher_id)

        if not teacher:
            logger.error(
                f"[Onboarding:{teacher_id}] Teacher not found in DB "
                "when trying to store reference embedding"
            )
            return

        teacher.reference_embedding = embedding_json
        session.add(teacher)
        session.commit()


# ### What each piece does — at a glance

# | Section | What it does |
# |---|---|
# | Reference embedding block | Extracts ArcFace embedding from the raw photo; independent of the pipeline guard below |
# | Guard at top of preprocessing | Fails fast if `.env` pipeline paths are missing — better than a confusing crash |
# | `output_dir` | Same folder as `raw.jpg` — that's where the preprocessed file lands |
# | `cmd` list | The exact terminal command assembled as a Python list |
# | `timeout=300` | Kills the subprocess if it hangs — prevents a frozen background task |
# | `returncode != 0` | Non-zero means the script crashed — store failure, teacher re-uploads |
# | `glob("*_preprocessed.png")` | Safely finds output without hardcoding the filename |
# | `_set_status()` | Separate helper for avatar-pipeline status — opens its own DB session |
# | `_store_reference_embedding()` | Separate helper for identity verification — opens its own DB session |

# ---

# ### Also create the `workers` folder
# Make sure the folder exists with an `__init__.py`:
# ```
# app/workers/__init__.py     ← empty file, just marks it as a package
# app/workers/onboarding_worker.py


# app/workers/onboarding_worker.py
import subprocess
import logging
from pathlib import Path
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.models.teacher import Teacher
from app.services.face_verification import (
    extract_embedding,
    embedding_to_json,
    NoFaceDetectedError,
    MultipleFacesDetectedError,
    FaceVerificationError,
)

logger = logging.getLogger(__name__)


def run_onboarding(teacher_id: int, raw_image_path: str) -> None:
    """
    Background task — runs after a teacher uploads their photo.

    Does two independent things with the raw photo:
      1. Extracts an ArcFace reference embedding for identity verification
         at generation time (Phase 3 of the face-recognition feature).
      2. Calls preprocess_image.py (in the longcat-video conda env) to
         produce a face-aligned image the avatar pipeline can use.

    These are deliberately independent — embedding extraction doesn't need
    LONGCAT_ENV_PYTHON or the GPU machine, so identity verification keeps
    working even before the avatar pipeline is configured on this machine.

    On success → teacher.onboarding_status = 'ready'
                 teacher.preprocessed_image_path = absolute path to *_preprocessed.png
                 teacher.reference_embedding = JSON-encoded 512-dim ArcFace embedding

    On failure → teacher.onboarding_status = 'failed'
                 Teacher must re-upload their photo to retry.

    Args:
        teacher_id:      Teacher's user_id (primary key in teachers table)
        raw_image_path:  Absolute path to the saved raw.jpg on disk
    """

    # ── Identity verification: extract reference embedding ─────────
    # Best-effort: a failure here doesn't block the rest of onboarding,
    # it just means verify-identity will reject this teacher until they
    # re-upload a clearer photo. Logged separately from onboarding_status
    # because this isn't part of the avatar-preprocessing pipeline below.
    try:
        embedding = extract_embedding(raw_image_path)
        _store_reference_embedding(teacher_id, embedding_to_json(embedding))
        logger.info(f"[Onboarding:{teacher_id}] Reference embedding stored ({len(embedding)} dims)")
    except NoFaceDetectedError:
        logger.warning(
            f"[Onboarding:{teacher_id}] No face detected in {raw_image_path} — "
            "reference_embedding not set. Teacher must re-upload a clearer photo."
        )
    except MultipleFacesDetectedError as e:
        logger.warning(f"[Onboarding:{teacher_id}] {e} — reference_embedding not set.")
    except FaceVerificationError as e:
        logger.error(f"[Onboarding:{teacher_id}] Embedding extraction failed: {e} — reference_embedding not set.")

    # ── Guard: pipeline must be configured ────────────────────────
    # If config paths are missing (dev machine without pipeline installed),
    # leave status as 'pending' — the photo is saved and can be preprocessed
    # once the pipeline is set up. This is NOT a teacher failure.
    if not settings.PREPROCESS_SCRIPT or not settings.LONGCAT_ENV_PYTHON:
        logger.warning(
            f"[Onboarding:{teacher_id}] Pipeline not configured — skipping preprocessing. "
            "Set PREPROCESS_SCRIPT and LONGCAT_ENV_PYTHON in .env to enable it. "
            "Photo has been saved successfully."
        )
        _set_status(teacher_id, "pending", preprocessed_path=None)
        return

    # ── Resolve output paths ──────────────────────────────────────
    # preprocess_image.py uses --output <file>, not --output-dir.
    # We write <stem>_preprocessed.png next to the raw image so the
    # glob("*_preprocessed.png") below can always find it.
    # e.g. uploads/instructors/12/raw.jpg  →  raw_preprocessed.png
    input_path = Path(raw_image_path)
    output_dir = input_path.parent
    output_file = output_dir / (input_path.stem + "_preprocessed.png")

    # ── Build subprocess command ───────────────────────────────────
    # We call the longcat-video venv Python directly so we get that
    # environment's dependencies (PyTorch, face detection models, etc.)
    cmd = [
        settings.LONGCAT_ENV_PYTHON,       # D:/Hololearn/long cat/LongCat-Video/venv/Scripts/python.exe
        settings.PREPROCESS_SCRIPT,        # D:/Hololearn/long cat/LongCat-Video/preprocess_image.py
        "--input",  raw_image_path,        # absolute path to raw.jpg
        "--output", str(output_file),      # absolute path for the output PNG
    ]

    logger.info(f"[Onboarding:{teacher_id}] Starting preprocessing → {raw_image_path}")

    # ── Run subprocess ─────────────────────────────────────────────
    # cwd = LongCat script directory so relative imports inside the script work
    # capture_output = True captures both stdout and stderr
    # text = True gives us strings instead of bytes
    try:
        result = subprocess.run(
            cmd,
            cwd=settings.LONGCAT_SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300,   # 5 minute hard limit — preprocessing shouldn't take longer
        )
    except subprocess.TimeoutExpired:
        logger.error(f"[Onboarding:{teacher_id}] Preprocessing timed out after 5 minutes")
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return
    except Exception as e:
        logger.error(f"[Onboarding:{teacher_id}] Subprocess launch failed: {e}")
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # ── Check exit code ────────────────────────────────────────────
    if result.returncode != 0:
        logger.error(
            f"[Onboarding:{teacher_id}] preprocess_image.py failed "
            f"(exit {result.returncode}):\n{result.stderr[-1000:]}"
        )
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # ── Find the output file ───────────────────────────────────────
    # preprocess_image.py names its output based on input filename,
    # typically raw_preprocessed.png — glob to find it safely.
    preprocessed_files = sorted(output_dir.glob("*_preprocessed.png"))

    if not preprocessed_files:
        # Script exited 0 but produced no output — treat as failure
        logger.error(
            f"[Onboarding:{teacher_id}] preprocess_image.py exited 0 "
            "but no *_preprocessed.png found in output dir"
        )
        _set_status(teacher_id, "failed", preprocessed_path=None)
        return

    # Take the most recently modified one (handles re-uploads correctly)
    preprocessed_path = str(preprocessed_files[-1].resolve())

    logger.info(f"[Onboarding:{teacher_id}] Preprocessing complete → {preprocessed_path}")
    _set_status(teacher_id, "ready", preprocessed_path=preprocessed_path)


def _set_status(
    teacher_id: int,
    status: str,
    preprocessed_path: str | None
) -> None:
    """
    Open a fresh DB session and update the teacher's onboarding fields.

    This runs outside the original HTTP request/session lifecycle,
    so we must create our own session directly from the engine.
    """
    with Session(engine) as session:
        teacher = session.get(Teacher, teacher_id)

        if not teacher:
            logger.error(
                f"[Onboarding:{teacher_id}] Teacher not found in DB "
                "when trying to update onboarding status"
            )
            return

        teacher.onboarding_status = status

        if preprocessed_path is not None:
            teacher.preprocessed_image_path = preprocessed_path

        session.add(teacher)
        session.commit()

        logger.info(f"[Onboarding:{teacher_id}] DB updated → onboarding_status='{status}'")


def _store_reference_embedding(teacher_id: int, embedding_json: str) -> None:
    """
    Open a fresh DB session and store the teacher's reference embedding.

    Deliberately separate from _set_status() — onboarding_status reflects
    the avatar-preprocessing pipeline, not identity verification. The two
    succeed or fail independently, so they shouldn't share a write path.
    """
    with Session(engine) as session:
        teacher = session.get(Teacher, teacher_id)

        if not teacher:
            logger.error(
                f"[Onboarding:{teacher_id}] Teacher not found in DB "
                "when trying to store reference embedding"
            )
            return

        teacher.reference_embedding = embedding_json
        session.add(teacher)
        session.commit()


# ### What each piece does — at a glance

# | Section | What it does |
# |---|---|
# | Reference embedding block | Extracts ArcFace embedding from the raw photo; independent of the pipeline guard below |
# | Guard at top of preprocessing | Fails fast if `.env` pipeline paths are missing — better than a confusing crash |
# | `output_dir` | Same folder as `raw.jpg` — that's where the preprocessed file lands |
# | `cmd` list | The exact terminal command assembled as a Python list |
# | `timeout=300` | Kills the subprocess if it hangs — prevents a frozen background task |
# | `returncode != 0` | Non-zero means the script crashed — store failure, teacher re-uploads |
# | `glob("*_preprocessed.png")` | Safely finds output without hardcoding the filename |
# | `_set_status()` | Separate helper for avatar-pipeline status — opens its own DB session |
# | `_store_reference_embedding()` | Separate helper for identity verification — opens its own DB session |

# ---

# ### Also create the `workers` folder
# Make sure the folder exists with an `__init__.py`:
# ```
# app/workers/__init__.py     ← empty file, just marks it as a package
# app/workers/onboarding_worker.py