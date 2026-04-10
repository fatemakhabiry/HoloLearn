# Lecture_Agent/api_server.py

import sys
from pathlib import Path

# ── Path setup — same as test scripts ────────────────────────────────────────
_AI_DIR      = Path(__file__).parent
_PROJECT_ROOT = _AI_DIR.parent
_GEN_ROOT    = _PROJECT_ROOT / "generators"

for _p in [str(_PROJECT_ROOT), str(_AI_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _sub in _GEN_ROOT.rglob("*.py"):
    _d = str(_sub.parent)
    if _d not in sys.path:
        sys.path.insert(0, _d)
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from graph import build_graph


_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph

    postgres_url = os.environ.get("POSTGRES_URL")
    if not postgres_url:
        raise RuntimeError("POSTGRES_URL not set in environment")

    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()
        _graph = build_graph(checkpointer=saver)
        print("[api_server] ✅ AI service ready on port 8001")
        yield
        print("[api_server] AI service shutting down")


app = FastAPI(lifespan=lifespan)


# ── Request models ─────────────────────────────────────────────────────────────

class InvokeRequest(BaseModel):
    thread_id:     str
    initial_state: Optional[dict] = None


class ResumeRequest(BaseModel):
    thread_id: str
    status:    str        # "approved" | "rejected"
    feedback:  str = ""


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/invoke")
async def invoke(body: InvokeRequest):
    """
    Start a new agent run (initial_state provided)
    or resume a paused one (initial_state is None).
    Returns immediately — graph runs in background.
    """
    config = {"configurable": {"thread_id": body.thread_id}}

    if body.initial_state:
        asyncio.create_task(_graph.ainvoke(body.initial_state, config))
    else:
        asyncio.create_task(
            _graph.ainvoke(
                Command(resume={"status": "approved", "feedback": ""}),
                config,
            )
        )
    return {"status": "started"}


@app.post("/resume")
async def resume(body: ResumeRequest):
    """
    Resume a paused graph after teacher approve or reject.
    Returns immediately — graph runs in background.
    """
    config = {"configurable": {"thread_id": body.thread_id}}
    asyncio.create_task(
        _graph.ainvoke(
            Command(resume={"status": body.status, "feedback": body.feedback}),
            config,
        )
    )
    return {"status": "resumed"}


@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    """
    Read the current agent state from the LangGraph checkpoint.
    Called by the backend to serve /status and /stream endpoints.
    """
    config   = {"configurable": {"thread_id": thread_id}}
    snapshot = await _graph.aget_state(config)

    if not snapshot or not snapshot.values:
        return {}

    s        = snapshot.values
    approval = s.get("lecture_approval") or {}

    return {
        "current_step":      s.get("current_step"),
        "approval_status":   approval.get("status"),
        "iteration":         approval.get("iteration", 0),
        "max_iterations":    approval.get("max_iterations", 3),
        "final_lecture":     s.get("final_lecture"),
        "lecture_paths":     s.get("lecture_paths"),
        "generated_content": s.get("generated_content"),
        "error":             s.get("error"),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "graph_ready": _graph is not None}