from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.init_db import create_db_and_tables
from app.core.config import settings
from app.api.v1.router import api_router


# create_db_and_tables()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="HoloLearn API - Holographic Education Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads/teachers", exist_ok=True)

# Mount static files to serve uploaded files
# This allows accessing files at: http://localhost:8000/uploads/teachers/123/photo.jpg
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Hologram backend is running 🎉"}


@app.get("/health")
def health_check():
    return {"status": "ok"}