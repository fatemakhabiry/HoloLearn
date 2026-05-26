# app/tasks/session_tasks_arq.py

from datetime import datetime, timedelta
from sqlmodel import Session, select

from app.core.database import engine
from app.models.agent_session import AgentSession, AgentStatus
from app.models.lecture import Lecture, LectureStatus
from app.services.agent_client import get_agent_state


TERMINAL_STEPS = {"done", "failed"}

# FIX #3 — stop re-enqueuing after this long with no progress
_MAX_SESSION_AGE = timedelta(hours=2)


async def sync_agent_state(ctx: dict, session_id: int, thread_id: str) -> None:
    """
    ARQ background job — syncs LangGraph agent state to Postgres.

    Re-enqueues itself every 60 seconds until the session reaches a terminal
    state (done / failed) or has been running for more than 2 hours without
    progress (in which case detect_stuck_sessions will clean it up).

    Survives server restarts because the task lives in Redis, not process memory.
    """
    redis = ctx["redis"]

    try:
        state = await get_agent_state(thread_id)

        if not state:
            # AI service not ready yet — retry in 30 seconds
            # FIX #1 — use keyword args so signature changes don't break silently
            await redis.enqueue_job(
                "sync_agent_state",
                session_id=session_id,
                thread_id=thread_id,
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

            # FIX #3 — guard: stop re-enqueuing stale sessions and let the
            # cron detector handle marking them failed
            if datetime.utcnow() - agent_session.updated_at > _MAX_SESSION_AGE:
                print(
                    f"[arq] session {session_id} has not progressed in "
                    f"{_MAX_SESSION_AGE} — stopping re-enqueue, detector will clean up"
                )
                return

            lecture = db.get(Lecture, agent_session.lecture_id)
            if not lecture:
                print(f"[arq] lecture for session {session_id} not found — stopping")
                return

            # Import from service layer, not from the endpoint module
            from app.services.agent_service import sync_state_to_db
            await sync_state_to_db(agent_session, lecture, state, db)

        if current_step in TERMINAL_STEPS:
            print(f"[arq] session {session_id} reached {current_step} — done")
            return

        # Re-enqueue itself for 60 seconds later
        # FIX #1 — keyword args
        await redis.enqueue_job(
            "sync_agent_state",
            session_id=session_id,
            thread_id=thread_id,
            _defer_by=timedelta(seconds=60),
        )
        print(f"[arq] session {session_id} → {current_step} — re-queued in 60s")

    except Exception as exc:
        print(f"[arq] error syncing session {session_id}: {exc}")
        # Retry in 30 seconds on any unexpected error
        try:
            # FIX #1 — keyword args
            await redis.enqueue_job(
                "sync_agent_state",
                session_id=session_id,
                thread_id=thread_id,
                _defer_by=timedelta(seconds=30),
            )
        except Exception:
            pass


async def detect_stuck_sessions(ctx: dict) -> None:
    """
    ARQ cron job — runs every 10 minutes.

    Finds sessions stuck in a non-terminal state with no AI service activity
    and marks them as failed so the teacher can restart.

    FIX #2 — async HTTP calls (get_agent_state) are now made OUTSIDE the DB
    session so we don't hold a connection open during potentially slow/failing
    network requests.
    """
    STUCK_THRESHOLD_MINUTES = 15
    terminal = {AgentStatus.DONE, AgentStatus.FAILED}
    cutoff = datetime.utcnow() - timedelta(minutes=STUCK_THRESHOLD_MINUTES)

    # ── Phase 1: collect stuck session data, then close the DB session ─────────
    session_data: list[tuple[int, str, int]] = []  # (id, thread_id, lecture_id)

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

        # Snapshot what we need — don't hold the session open for HTTP calls
        session_data = [
            (s.id, s.thread_id, s.lecture_id)
            for s in stuck_sessions
        ]

    print(f"[arq detector] checking {len(session_data)} potentially stuck session(s)")

    # ── Phase 2: async HTTP calls with NO open DB connection ───────────────────
    # Each get_agent_state is an httpx call to the AI service.
    # If it times out or the service is down, no DB connection is blocked.
    still_active: set[int] = set()

    for sid, thread_id, _ in session_data:
        try:
            state = await get_agent_state(thread_id)
            if state and state.get("current_step") not in (None, ""):
                print(f"[arq detector] session {sid} still active — skipping")
                still_active.add(sid)
        except Exception as exc:
            # Can't reach AI service — treat as stuck (safe assumption)
            print(f"[arq detector] could not reach AI service for session {sid}: {exc}")

    # ── Phase 3: update DB for truly stuck sessions ────────────────────────────
    to_fail = [row for row in session_data if row[0] not in still_active]

    if not to_fail:
        print("[arq detector] all sessions are still active — nothing to fail")
        return

    with Session(engine) as db:
        for sid, _, lecture_id in to_fail:
            print(f"[arq detector] session {sid} is stuck — marking failed")

            agent_session = db.get(AgentSession, sid)
            if agent_session:
                agent_session.status = AgentStatus.FAILED
                agent_session.updated_at = datetime.utcnow()
                db.add(agent_session)

            lecture = db.get(Lecture, lecture_id)
            if lecture:
                lecture.status = LectureStatus.FAILED
                db.add(lecture)

        db.commit()
        print(f"[arq detector] marked {len(to_fail)} session(s) as failed")