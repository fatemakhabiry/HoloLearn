from fastapi import FastAPI
from app.core.init_db import create_db_and_tables



create_db_and_tables()

app = FastAPI(
    title="Hologram Tutor Backend",
    version="0.1.0"
)


@app.get("/")
def read_root():
    return {"message": "Hologram backend is running 🎉"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
