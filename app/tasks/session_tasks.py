import asyncio
from datetime import datetime

from sqlmodel import Session, select

from app.celery_app import celery_app
from app.core.database import engine
from app.models.agent_session import AgentSession, AgentStatus
from app.models.lecture import Lecture
from app.services.agent_client import get_agent_state


TERMINAL_STEPS = {"done", "failed"}


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="session_tasks.sync_agent_state",
    max_retries=None,
    default_retry_delay=30,
)
def sync_agent_state(self, session_id: int, thread_id: str):
    """
    Sync agent state from LangGraph into Postgres.
    Re-queues itself every 60 seconds until session reaches terminal state.
    Survives server restarts because the task lives in Redis, not in process memory.
    """
    try:
        state = _run_async(get_agent_state(thread_id))

        if not state:
            # AI service not ready yet — retry in 30s
            raise self.retry(countdown=30)

        current_step = state.get("current_step")

        with Session(engine) as db:
            agent_session = db.exec(
                select(AgentSession).where(AgentSession.id == session_id)
            ).first()

            if not agent_session:
                print(f"[celery] session {session_id} not found — stopping")
                return

            lecture = db.get(Lecture, agent_session.lecture_id)
            if not lecture:
                print(f"[celery] lecture for session {session_id} not found — stopping")
                return

            # Import here to avoid circular import at module load time
            from app.api.v1.endpoints.sessions import _sync_state_to_db
            _run_async(_sync_state_to_db(agent_session, lecture, state, db))

        if current_step in TERMINAL_STEPS:
            print(f"[celery] session {session_id} reached {current_step} — done")
            return

        # Re-queue itself for 60 seconds later
        sync_agent_state.apply_async(
            args=[session_id, thread_id],
            countdown=60,
        )

    except self.MaxRetriesExceededError:
        print(f"[celery] session {session_id} max retries exceeded")
    except Exception as exc:
        print(f"[celery] error syncing session {session_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)