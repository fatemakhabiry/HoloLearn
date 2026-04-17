# # app/core/config.py
# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     DATABASE_URL: str
#     APP_NAME: str = "HoloLearn"
#     DEBUG: bool = True
    
#     # Security
#     SECRET_KEY: str
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
#     DRIVE_FOLDER_ID : str


#     # Email Configuration (for OTP Password Reset) ← ADD THESE 4 LINES
#     SMTP_SERVER: str = "smtp.gmail.com"
#     SMTP_PORT: int = 587
#     SENDER_EMAIL: str
#     SENDER_PASSWORD: str

#     # THIS IS THE NEW 2025 WAY (replace the old class Config)
#     model_config = {
#         "env_file": ".env",
#         "env_file_encoding": "utf-8",
#     }

# # Keep this at the bottom
# settings = Settings()


# # Test block — keep it!
# if __name__ == "__main__":
#     print(f"Config loaded!")
#     print(f"App Name: {settings.APP_NAME}")
#     print(f"Database: {settings.DATABASE_URL}")
#     print(f"Secret Key Length: {len(settings.SECRET_KEY)} chars")
#     print(f"Algorithm: {settings.ALGORITHM}")

# app/core/config.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    POSTGRES_URL : str
    APP_NAME: str = "HoloLearn"
    DEBUG: bool = True
    AI_SERVICE_URL : str
    OUTPUTS_DIR_AGENT : str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google Drive
    DRIVE_FOLDER_ID: str

    # Email (OTP Password Reset)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: str
    SENDER_PASSWORD: str

    # Groq API Keys
    GROQ_API_KEY_LECTURE: Optional[str] = None
    GROQ_API_KEY_SCRIPT: Optional[str] = None
    GROQ_API_KEY_SUMMARY: Optional[str] = None
    GROQ_API_KEY_QUIZ: Optional[str] = None
    GROQ_API_KEY_WORKSHEET: Optional[str] = None
    GROQ_API_KEY_FLOWCHART: Optional[str] = None
    GROQ_API_KEY_VIDEO: Optional[str] = None
    GROQ_API_KEY_AUDIO: Optional[str] = None

    # ── Pipeline Paths ─────────────────────────────────────────────
    # Absolute paths on the machine running the pipeline (Windows)
    # Optional so the app starts even without pipeline configured
    LONGCAT_ENV_PYTHON: Optional[str] = None   # conda env python for LongCat
    PIPELINE_SCRIPT: Optional[str] = None      # hololearn_pipeline.py
    PREPROCESS_SCRIPT: Optional[str] = None    # preprocess_image.py
    LONGCAT_SCRIPT_DIR: Optional[str] = None   # cwd for LongCat subprocess
    HOLOLEARN_DIR: Optional[str] = None        # root HoloLearn project dir

    # Avatar backend selector
    # "local" = run_chunked_avatar.py on local GPU (requires ~198 GB weights + 16–24 GB VRAM)
    # "fal"   = fal.ai cloud API (avatar runs in cloud; TTS still runs locally ~6 GB VRAM)
    AVATAR_BACKEND: str = "local"
    FAL_KEY: Optional[str] = None   # Required only when AVATAR_BACKEND = "fal"

    # ── Storage Directories ────────────────────────────────────────
    UPLOADS_DIR: Optional[str] = None          # teacher photos + voice files
    OUTPUTS_DIR: Optional[str] = None          # generated MP4 output files

    # ── Distributed Pipeline (internet-separated machines) ────────
    # Your laptop (this machine) public HTTPS URL via ngrok
    BACKEND_PUBLIC_URL: Optional[str] = None     # e.g. https://abc123.ngrok-free.app
    # AI server public HTTPS URL via ngrok (friend's PC)
    AI_SERVER_URL: Optional[str] = None          # e.g. https://xyz456.ngrok-free.app
    # Shared secret — both machines must have the same value in .env
    INTERNAL_API_TOKEN: Optional[str] = None     # e.g. a long random hex string

    # ── Redis / ARQ ──────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Worker Concurrency ─────────────────────────────────────────
    MAX_GENERATION_WORKERS: int = 1            # MUST stay 1 — single GPU
    MAX_ONBOARDING_WORKERS: int = 2            # CPU task, safe to parallelize

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

settings = Settings()


if __name__ == "__main__":
    print(f"Config loaded!")
    print(f"App Name:          {settings.APP_NAME}")
    print(f"Database:          {settings.DATABASE_URL}")
    print(f"Secret Key Length: {len(settings.SECRET_KEY)} chars")
    print(f"Pipeline Script:   {settings.PIPELINE_SCRIPT}")
    print(f"Uploads Dir:       {settings.UPLOADS_DIR}")
    print(f"Outputs Dir:       {settings.OUTPUTS_DIR}")
    print(f"Max Gen Workers:   {settings.MAX_GENERATION_WORKERS}")