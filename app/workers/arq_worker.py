# app/workers/arq_worker.py
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.generation_worker import run_generation
from app.workers.rag_ingest_worker import run_rag_ingest      # ← ADD


class WorkerSettings:
    """
    ARQ worker configuration.

    Start the worker with:
        python -m arq app.workers.arq_worker.WorkerSettings

    MAX_JOBS = 1 is critical — single GPU cannot handle two pipeline jobs
    simultaneously. The second job waits in Redis queue until the first finishes.
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)  # e.g. redis://localhost:6379/0
    max_jobs = settings.MAX_GENERATION_WORKERS  # MUST be 1

    # Functions this worker knows how to run
    functions = [run_generation,run_rag_ingest,]    
    