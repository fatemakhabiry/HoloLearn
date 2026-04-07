# import os
# import uuid
# from pathlib import Path
# from typing import Tuple
# from fastapi import UploadFile, HTTPException, status

# # Base upload directory
# UPLOAD_DIR = Path("uploads")
# TEACHER_UPLOAD_DIR = UPLOAD_DIR / "teachers"

# # Allowed file extensions
# ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
# ALLOWED_VOICE_EXTENSIONS = {".mp3", ".wav", ".m4a"}

# # File size limits (in bytes)
# MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
# MAX_VOICE_SIZE = 10 * 1024 * 1024  # 10MB


# def ensure_upload_dir_exists():
#     """Create upload directories if they don't exist"""
#     TEACHER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
#     """Check if file extension is allowed"""
#     extension = Path(filename).suffix.lower()
#     return extension in allowed_extensions


# def validate_file_size(file: UploadFile, max_size: int) -> bool:
#     """Check if file size is within limit"""
#     file.file.seek(0, 2)  # Move to end of file
#     file_size = file.file.tell()
#     file.file.seek(0)  # Reset to beginning
#     return file_size <= max_size


# async def save_teacher_file(
#     file: UploadFile,
#     user_id: int,
#     file_type: str  # "photo" or "voice"
# ) -> str:
#     """
#     Save uploaded file for teacher
    
#     Args:
#         file: Uploaded file
#         user_id: Teacher's user ID
#         file_type: Type of file ("photo" or "voice")
    
#     Returns:
#         Relative path to saved file
    
#     Raises:
#         HTTPException: If validation fails
#     """
#     # Validate file type
#     if file_type == "photo":
#         allowed_extensions = ALLOWED_PHOTO_EXTENSIONS
#         max_size = MAX_PHOTO_SIZE
#     elif file_type == "voice":
#         allowed_extensions = ALLOWED_VOICE_EXTENSIONS
#         max_size = MAX_VOICE_SIZE
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid file type"
#         )
    
#     # Validate extension
#     if not validate_file_extension(file.filename, allowed_extensions):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
#         )
    
#     # Validate size
#     if not validate_file_size(file, max_size):
#         max_size_mb = max_size / (1024 * 1024)
#         raise HTTPException(
#             status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
#             detail=f"File too large. Maximum size: {max_size_mb}MB"
#         )
    
#     # Create user directory
#     user_dir = TEACHER_UPLOAD_DIR / str(user_id)
#     user_dir.mkdir(parents=True, exist_ok=True)
    
#     # Generate unique filename
#     file_extension = Path(file.filename).suffix.lower()
#     unique_filename = f"{file_type}_{uuid.uuid4().hex}{file_extension}"
#     file_path = user_dir / unique_filename
    
#     # Save file
#     try:
#         with open(file_path, "wb") as f:
#             content = await file.read()
#             f.write(content)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to save file: {str(e)}"
#         )
    
#     # Return relative path (normalize to forward slashes for cross-platform compatibility)
#     # file_path is already relative (uploads/teachers/12/photo_xxx.jpg)
#     relative_path = str(file_path).replace("\\", "/")
#     return relative_path


# def delete_teacher_file(file_path: str) -> bool:
#     """
#     Delete a teacher's file
    
#     Args:
#         file_path: Relative path to file
    
#     Returns:
#         True if deleted successfully, False otherwise
#     """
#     try:
#         full_path = Path(file_path)
#         if full_path.exists():
#             full_path.unlink()
#             return True
#         return False
#     except Exception:
#         return False


# app/core/file_utils.py
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io

# ── Directory layout ───────────────────────────────────────────────────────────
# All teacher assets live under uploads/instructors/{user_id}/
# Filenames are fixed (not UUID) so the pipeline always knows where to look.
#
#   uploads/instructors/12/raw.jpg        ← teacher photo (always JPEG)
#   uploads/instructors/12/voice_ref.wav  ← teacher voice sample (always WAV)

UPLOAD_DIR = Path("uploads")
INSTRUCTOR_UPLOAD_DIR = UPLOAD_DIR / "instructors"

# ── Allowed extensions ─────────────────────────────────────────────────────────
# Photo: any common image format — converted to .jpg on save
# Voice: wav only — pipeline expects voice_ref.wav directly
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_VOICE_EXTENSIONS = {".wav"}

# ── Size limits ────────────────────────────────────────────────────────────────
MAX_PHOTO_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_VOICE_SIZE = 10 * 1024 * 1024  # 10 MB


def ensure_upload_dir_exists():
    """Create base upload directories if they don't exist."""
    INSTRUCTOR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """Return True if the file's extension is in the allowed set."""
    extension = Path(filename).suffix.lower()
    return extension in allowed_extensions


def validate_file_size(file: UploadFile, max_size: int) -> bool:
    """Return True if the file is within the size limit."""
    file.file.seek(0, 2)        # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)           # Reset to start
    return file_size <= max_size


async def save_teacher_file(
    file: UploadFile,
    user_id: int,
    file_type: str  # "photo" or "voice"
) -> str:
    """
    Validate and save a teacher's photo or voice file.

    Photo → saved as  uploads/instructors/{user_id}/raw.jpg  (always JPEG)
    Voice → saved as  uploads/instructors/{user_id}/voice_ref.wav

    Fixed filenames mean:
      - The pipeline CLI always knows the exact path to pass.
      - Re-uploading overwrites the previous file automatically.

    Returns:
        Absolute path string to the saved file.

    Raises:
        HTTPException 400  — wrong extension
        HTTPException 413  — file too large
        HTTPException 500  — disk write failure
    """
    # ── Choose rules based on file type ───────────────────────────
    if file_type == "photo":
        allowed_extensions = ALLOWED_PHOTO_EXTENSIONS
        max_size = MAX_PHOTO_SIZE
    elif file_type == "voice":
        allowed_extensions = ALLOWED_VOICE_EXTENSIONS
        max_size = MAX_VOICE_SIZE
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Must be 'photo' or 'voice'."
        )

    # ── Validate extension ─────────────────────────────────────────
    if not validate_file_extension(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
        )

    # ── Validate size ──────────────────────────────────────────────
    if not validate_file_size(file, max_size):
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_mb:.0f}MB"
        )

    # ── Create per-teacher directory ───────────────────────────────
    # e.g. uploads/instructors/12/
    instructor_dir = INSTRUCTOR_UPLOAD_DIR / str(user_id)
    instructor_dir.mkdir(parents=True, exist_ok=True)

    # ── Save with fixed filename ───────────────────────────────────
    try:
        content = await file.read()

        if file_type == "photo":
            # Convert any image format → JPEG using Pillow.
            # This guarantees the pipeline always receives raw.jpg.
            image = Image.open(io.BytesIO(content))

            # Convert RGBA or palette images to RGB before saving as JPEG
            if image.mode in ("RGBA", "P", "LA"):
                image = image.convert("RGB")

            file_path = instructor_dir / "raw.jpg"
            image.save(str(file_path), format="JPEG", quality=95)

        else:  # voice
            # Save WAV directly — no conversion needed.
            file_path = instructor_dir / "voice_ref.wav"
            with open(file_path, "wb") as f:
                f.write(content)

    except HTTPException:
        raise  # re-raise our own validation errors
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Return absolute path so the pipeline and workers always get a full path
    return str(file_path.resolve())


def delete_teacher_file(file_path: str) -> bool:
    """
    Delete a teacher's file from disk.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        True if deleted, False if file didn't exist or deletion failed.
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception:
        return False