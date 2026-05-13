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
    # ── Create required directories on startup ─────────────────────
    dirs_to_create = []

    if settings.UPLOADS_DIR:
        dirs_to_create.append(Path(settings.UPLOADS_DIR) / "instructors")
    else:
        dirs_to_create.append(Path("uploads") / "instructors")

    if settings.OUTPUTS_DIR:
        dirs_to_create.append(Path(settings.OUTPUTS_DIR) / "jobs")
    else:
        dirs_to_create.append(Path("outputs") / "jobs")

    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Directory ready: {directory}")

    logger.info("HoloLearn startup complete — all directories ready")

    # ── Recover stuck sessions from before last restart ────────────
    try:
        from sqlmodel import Session, select
        from app.core.database import engine
        from app.models.agent_session import AgentSession, AgentStatus
        from app.tasks.session_tasks import sync_agent_state

        in_progress = {
            AgentStatus.GENERATING_LECTURE,
            AgentStatus.GENERATING_CONTENT,
            AgentStatus.REGENERATING,
        }

        with Session(engine) as db:
            stuck = db.exec(
                select(AgentSession).where(
                    AgentSession.status.in_(in_progress)
                )
            ).all()

        for s in stuck:
            logger.info(f"Recovering stuck session {s.id} (status={s.status})")
            sync_agent_state.apply_async(
                args=[s.id, s.thread_id],
                countdown=5,
            )

        if stuck:
            logger.info(f"Re-queued {len(stuck)} stuck session(s)")
        else:
            logger.info("No stuck sessions found")

    except Exception as e:
        logger.warning(f"Session recovery failed (non-fatal): {e}")

    yield  # ← server runs here, handling requests

    # ── Shutdown ───────────────────────────────────────────────────
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