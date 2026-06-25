# # app/workers/arq_worker.py

# from arq.connections import RedisSettings
# from arq.cron import cron

# from app.core.config import settings
# from app.workers.generation_worker import run_generation
# from app.workers.qa_export_worker import cleanup_expired_qa_exports
# from app.workers.rag_ingest_worker import run_rag_ingest
# from app.tasks.session_tasks_arq import sync_agent_state, detect_stuck_sessions


# class WorkerSettings:
#     """
#     Single ARQ worker that handles everything:
#         1. Hologram video pipeline     (run_generation)
#         2. RAG document indexing       (run_rag_ingest)
#         3. Session state sync          (sync_agent_state)
#         4. Stuck session detection     (detect_stuck_sessions — every 10 min)

#     Start with:
#         python -m arq app.workers.arq_worker.WorkerSettings

#     MAX_JOBS = 1 is critical — single GPU cannot handle two pipeline jobs
#     simultaneously. Session sync tasks are lightweight so this is fine.
#     """
#     redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
#     max_jobs = settings.MAX_GENERATION_WORKERS  # MUST stay 1

#     functions = [
#         run_generation,
#         run_rag_ingest,
#         sync_agent_state,
#         detect_stuck_sessions,
#     ]

#     cron_jobs = [
#         cron(detect_stuck_sessions, minute={0, 10, 20, 30, 40, 50}),
#         cron(cleanup_expired_qa_exports, hour=set(range(24)), minute=0),  # every hour
#     ]

# app/workers/arq_worker.py

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.workers.tts_worker import run_tts
from app.workers.generation_worker import run_generation
from app.workers.qa_export_worker import cleanup_expired_qa_exports
from app.workers.rag_ingest_worker import run_rag_ingest
from app.tasks.session_tasks_arq import sync_agent_state, detect_stuck_sessions


class WorkerSettings:
    """
    Single ARQ worker that handles everything:
        0. Lecture TTS + transcript    (run_tts — chains into run_generation)
        1. Hologram video pipeline     (run_generation)
        2. RAG document indexing       (run_rag_ingest)
        3. Session state sync          (sync_agent_state)
        4. Stuck session detection     (detect_stuck_sessions — every 10 min)

    Start with:
        python -m arq app.workers.arq_worker.WorkerSettings

    MAX_JOBS = 1 is critical — single GPU cannot handle two pipeline jobs
    simultaneously. Session sync tasks are lightweight so this is fine.
    run_tts runs locally (this machine) and is also kept serialized under
    the same MAX_JOBS=1, since it's the first stage of the same chain that
    ends with the GPU-bound run_generation.

    job_timeout is set explicitly because ARQ's default is only 300s —
    too short for run_tts (full-lecture Chatterbox synthesis can take
    well over 5 minutes) and far too short for run_generation (avatar
    generation, up to ~1 hour). This is a single ceiling for ALL jobs on
    this worker, including run_rag_ingest/sync_agent_state/
    detect_stuck_sessions — it does not need to be tight for those, it
    just needs to be high enough for the slowest job (run_generation).
    """
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs     = settings.MAX_GENERATION_WORKERS  # MUST stay 1
    job_timeout  = 3700   # seconds — just above run_generation's internal 3600s ceiling

    functions = [
        run_tts,
        run_generation,
        run_rag_ingest,
        sync_agent_state,
        detect_stuck_sessions,
    ]

    cron_jobs = [
        cron(detect_stuck_sessions, minute={0, 10, 20, 30, 40, 50}),
        cron(cleanup_expired_qa_exports, hour=set(range(24)), minute=0),  # every hour
    ]