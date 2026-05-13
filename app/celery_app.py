from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "hololearn",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.session_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)