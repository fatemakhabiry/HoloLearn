# app/workers/arq_worker.py

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.workers.generation_worker import run_generation
from app.workers.qa_export_worker import cleanup_expired_qa_exports
from app.workers.rag_ingest_worker import run_rag_ingest
from app.tasks.session_tasks_arq import sync_agent_state, detect_stuck_sessions


class WorkerSettings:
    """
    Single ARQ worker that handles everything:
        1. Hologram video pipeline     (run_generation)
        2. RAG document indexing       (run_rag_ingest)
        3. Session state sync          (sync_agent_state)
        4. Stuck session detection     (detect_stuck_sessions — every 10 min)

    Start with:
        python -m arq app.workers.arq_worker.WorkerSettings

    MAX_JOBS = 1 is critical — single GPU cannot handle two pipeline jobs
    simultaneously. Session sync tasks are lightweight so this is fine.
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.MAX_GENERATION_WORKERS  # MUST stay 1

    functions = [
        run_generation,
        run_rag_ingest,
        sync_agent_state,
        detect_stuck_sessions,
    ]

    cron_jobs = [
        cron(detect_stuck_sessions, minute={0, 10, 20, 30, 40, 50}),
        cron(cleanup_expired_qa_exports, hour=set(range(24)), minute=0),  # every hour
    ]