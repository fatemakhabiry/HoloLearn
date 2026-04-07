# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# import os

# from app.core.init_db import create_db_and_tables
# from app.core.config import settings
# from app.api.v1.router import api_router


# create_db_and_tables()

# app = FastAPI(
#     title=settings.APP_NAME,
#     debug=settings.DEBUG,
#     description="HoloLearn API - Holographic Education Platform",
#     version="1.0.0"
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure for production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Create uploads directory if it doesn't exist
# os.makedirs("uploads/teachers", exist_ok=True)

# # Mount static files to serve uploaded files
# # This allows accessing files at: http://localhost:8000/uploads/teachers/123/photo.jpg
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# app.include_router(api_router, prefix="/api/v1")

# @app.get("/")
# def read_root():
#     return {"message": "Hologram backend is running 🎉"}


# @app.get("/health")
# def health_check():
#     return {"status": "ok"}

# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging
import os

from app.core.config import settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on server startup (before) and shutdown (after the yield).
    Use this for anything that must be ready before the first request.
    """
    # ── Create required directories on startup ─────────────────────
    # These must exist before any upload or generation job runs.
    # parents=True  → creates intermediate dirs automatically
    # exist_ok=True → no error if they already exist

    dirs_to_create = []

    # Upload directories
    if settings.UPLOADS_DIR:
        # Teacher assets: uploads/instructors/{teacher_id}/raw.jpg + voice_ref.wav
        dirs_to_create.append(Path(settings.UPLOADS_DIR) / "instructors")
    else:
        # Fallback if UPLOADS_DIR not set in .env (local dev without pipeline)
        dirs_to_create.append(Path("uploads") / "instructors")

    # Output directories
    if settings.OUTPUTS_DIR:
        # Generated videos: outputs/jobs/{lecture_id}/avatar_NNN.mp4
        dirs_to_create.append(Path(settings.OUTPUTS_DIR) / "jobs")
    else:
        dirs_to_create.append(Path("outputs") / "jobs")

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Directory ready: {directory}")

    logger.info("HoloLearn startup complete — all directories ready")

    yield  # ← server runs here, handling requests

    # Anything after yield runs on shutdown (cleanup)
    logger.info("HoloLearn shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="HoloLearn API - Holographic Education Platform",
    version="1.0.0",
    lifespan=lifespan,       # ← register the startup/shutdown handler
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ───────────────────────────────────────────────────────────────
# Serves uploaded files at /uploads/instructors/{id}/raw.jpg etc.
# The directory must exist before mounting — lifespan creates it above.
uploads_root = Path(settings.UPLOADS_DIR) if settings.UPLOADS_DIR else Path("uploads")
uploads_root.mkdir(parents=True, exist_ok=True)   # safety: ensure exists before mount
app.mount("/uploads", StaticFiles(directory=str(uploads_root)), name="uploads")

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Hologram backend is running 🎉"}


@app.get("/health")
def health_check():
    return {"status": "ok"}