# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    APP_NAME: str = "HoloLearn"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # THIS IS THE NEW 2025 WAY (replace the old class Config)
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

# Keep this at the bottom
settings = Settings()


# Test block — keep it!
if __name__ == "__main__":
    print(f"Config loaded!")
    print(f"App Name: {settings.APP_NAME}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Secret Key Length: {len(settings.SECRET_KEY)} chars")
    print(f"Algorithm: {settings.ALGORITHM}")