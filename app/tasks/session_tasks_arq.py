# app/tasks/session_tasks_arq.py

from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.core.database import engine
from app.models.agent_session import AgentSession, AgentStatus
from app.models.lecture import Lecture, LectureStatus
from app.services.agent_client import get_agent_state


TERMINAL_STEPS = {"done", "failed"}


async def sync_agent_state(ctx: dict, session_id: int, thread_id: str) -> None:
    """
    ARQ background job — syncs LangGraph agent state to Postgres.
    Re-enqueues itself every 60 seconds until session reaches terminal state.
    Survives server restarts because the task lives in Redis, not process memory.
    """
    redis = ctx["redis"]

    try:
        state = await get_agent_state(thread_id)

        if not state:
            # AI service not ready yet — retry in 30 seconds
            await redis.enqueue_job(
                "sync_agent_state",
                session_id,
                thread_id,
                _defer_by=timedelta(seconds=30),
            )
            print(f"[arq] session {session_id} — no state yet, retry in 30s")
            return

        current_step = state.get("current_step")

        with Session(engine) as db:
            agent_session = db.exec(
                select(AgentSession).where(AgentSession.id == session_id)
            ).first()

            if not agent_session:
                print(f"[arq] session {session_id} not found in DB — stopping")
                return

            # Do not overwrite a terminal status that was manually set
            if agent_session.status in (AgentStatus.DONE, AgentStatus.FAILED):
                print(f"[arq] session {session_id} already terminal ({agent_session.status}) — stopping")
                return

            lecture = db.get(Lecture, agent_session.lecture_id)
            if not lecture:
                print(f"[arq] lecture for session {session_id} not found — stopping")
                return

            from app.api.v1.endpoints.sessions import _sync_state_to_db
            await _sync_state_to_db(agent_session, lecture, state, db)

        if current_step in TERMINAL_STEPS:
            print(f"[arq] session {session_id} reached {current_step} — done")
            return

        # Re-enqueue itself for 60 seconds later
        await redis.enqueue_job(
            "sync_agent_state",
            session_id,
            thread_id,
            _defer_by=timedelta(seconds=60),
        )
        print(f"[arq] session {session_id} → {current_step} — re-queued in 60s")

    except Exception as exc:
        print(f"[arq] error syncing session {session_id}: {exc}")
        # Retry in 30 seconds on any unexpected error
        try:
            await redis.enqueue_job(
                "sync_agent_state",
                session_id,
                thread_id,
                _defer_by=timedelta(seconds=30),
            )
        except Exception:
            pass


async def detect_stuck_sessions(ctx: dict) -> None:
    """
    ARQ cron job — runs every 10 minutes.
    Finds sessions stuck in a non-terminal state with no AI service activity
    and marks them as failed so the teacher can restart.
    """
    STUCK_THRESHOLD_MINUTES = 15
    terminal = {AgentStatus.DONE, AgentStatus.FAILED}
    cutoff = datetime.utcnow() - timedelta(minutes=STUCK_THRESHOLD_MINUTES)

    with Session(engine) as db:
        stuck_sessions = db.exec(
            select(AgentSession).where(
                AgentSession.status.notin_(terminal),
                AgentSession.updated_at < cutoff,
            )
        ).all()

        if not stuck_sessions:
            print("[arq detector] no stuck sessions found")
            return

        for agent_session in stuck_sessions:
            state = await get_agent_state(agent_session.thread_id)

            if state and state.get("current_step") not in (None, ""):
                print(f"[arq detector] session {agent_session.id} still active — skipping")
                continue

            print(f"[arq detector] session {agent_session.id} is stuck — marking failed")

            agent_session.status = AgentStatus.FAILED
            agent_session.updated_at = datetime.utcnow()
            db.add(agent_session)

            lecture = db.get(Lecture, agent_session.lecture_id)
            if lecture:
                lecture.status = LectureStatus.FAILED
                db.add(lecture)

        db.commit()
        print(f"[arq detector] processed {len(stuck_sessions)} stuck session(s)")