# # Lecture_Agent/api_server.py

# import sys
# from pathlib import Path
# import contextvars

# # ── Path setup — same as test scripts ────────────────────────────────────────
# _AI_DIR      = Path(__file__).parent
# _PROJECT_ROOT = _AI_DIR.parent
# _GEN_ROOT    = _PROJECT_ROOT / "generators"

# for _p in [str(_PROJECT_ROOT), str(_AI_DIR)]:
#     if _p not in sys.path:
#         sys.path.insert(0, _p)

# for _sub in _GEN_ROOT.rglob("*.py"):
#     _d = str(_sub.parent)
#     if _d not in sys.path:
#         sys.path.insert(0, _d)
# # ─────────────────────────────────────────────────────────────────────────────

# import asyncio
# import os
# from contextlib import asynccontextmanager
# from typing import Optional

# from fastapi import FastAPI
# from pydantic import BaseModel
# from langgraph.types import Command
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# from graph import build_graph


# _graph = None


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global _graph

#     postgres_url = os.environ.get("POSTGRES_URL")
#     if not postgres_url:
#         raise RuntimeError("POSTGRES_URL not set in environment")

#     async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
#         await saver.setup()
#         _graph = build_graph(checkpointer=saver)
#         print("[api_server] ✅ AI service ready on port 8001")
#         yield
#         print("[api_server] AI service shutting down")


# app = FastAPI(lifespan=lifespan)


# # ── Request models ─────────────────────────────────────────────────────────────

# class InvokeRequest(BaseModel):
#     thread_id:     str
#     initial_state: Optional[dict] = None


# class ResumeRequest(BaseModel):
#     thread_id: str
#     status:    str        # "approved" | "rejected"
#     feedback:  str = ""



# import contextvars
# import threading

# def _run_in_background(coro):
#     return asyncio.create_task(coro)

# # ── Endpoints ──────────────────────────────────────────────────────────────────

# @app.post("/invoke")
# async def invoke(body: InvokeRequest):
#     """
#     Start a new agent run (initial_state provided)
#     or resume a paused one (initial_state is None).
#     Returns immediately — graph runs in background.
#     """
#     config = {"configurable": {"thread_id": body.thread_id}}

#     if body.initial_state:
#         asyncio.create_task(_graph.ainvoke(body.initial_state, config))
#     else:
#         asyncio.create_task(
#             _graph.ainvoke(
#                 Command(resume={"status": "approved", "feedback": ""}),
#                 config,
#             )
#         )
#     return {"status": "started"}


# # @app.post("/resume")
# # async def resume(body: ResumeRequest):
# #     config = {"configurable": {"thread_id": body.thread_id}}

# #     # Read current state to get iteration
# #     snapshot = await _graph.aget_state(config)
# #     current_approval = {}
# #     if snapshot and snapshot.values:
# #         current_approval = snapshot.values.get("lecture_approval") or {}

# #     # Update state with teacher's decision
# #     await _graph.aupdate_state(
# #         config,
# #         {
# #             "lecture_approval": {
# #                 "status":           body.status,
# #                 "teacher_feedback": body.feedback if body.status == "rejected" else None,
# #                 "iteration":        current_approval.get("iteration", 0),
# #                 "max_iterations":   current_approval.get("max_iterations", 3),
# #             }
# #         },
# #     )

# #     # Resume graph
# #     asyncio.create_task(
# #         _graph.ainvoke(None, config)
# #     )

# #     return {"status": "resumed"}


# @app.post("/resume")
# async def resume(body: ResumeRequest):
#     config = {"configurable": {"thread_id": body.thread_id}}

#     # Read current state
#     snapshot = await _graph.aget_state(config)
#     print(f"[resume] next nodes: {snapshot.next}")

#     current_approval = {}
#     if snapshot and snapshot.values:
#         current_approval = snapshot.values.get("lecture_approval") or {}

#     iteration   = current_approval.get("iteration", 0)
#     max_iter    = current_approval.get("max_iterations", 3)

#     print(f"[resume] status={body.status} iteration={iteration} feedback={body.feedback}")

#     # Update state with teacher decision
#     await _graph.aupdate_state(
#         config,
#         {
#             "lecture_approval": {
#                 "status":           body.status,
#                 "teacher_feedback": body.feedback if body.status == "rejected" else None,
#                 "iteration":        iteration,
#                 "max_iterations":   max_iter,
#             }
#         },
#         as_node="interrupt_for_approval",   # ← tells LangGraph this IS the node result
#     )

#     snapshot_after = await _graph.aget_state(config)
#     print(f"[resume] next after update: {snapshot_after.next}")

#     # Resume — None means continue from current position
#     _run_in_background(_graph.ainvoke(None, config))

#     return {"status": "resumed"}


# @app.get("/state/{thread_id}")
# async def get_state(thread_id: str):
#     """
#     Read the current agent state from the LangGraph checkpoint.
#     Called by the backend to serve /status and /stream endpoints.
#     """
#     config   = {"configurable": {"thread_id": thread_id}}
#     snapshot = await _graph.aget_state(config)

#     if not snapshot or not snapshot.values:
#         return {}

#     s        = snapshot.values
#     approval = s.get("lecture_approval") or {}

#     return {
#         "current_step":      s.get("current_step"),
#         "approval_status":   approval.get("status"),
#         "iteration":         approval.get("iteration", 0),
#         "max_iterations":    approval.get("max_iterations", 3),
#         "final_lecture":     s.get("final_lecture"),
#         "lecture_paths":     s.get("lecture_paths"),
#         "generated_content": s.get("generated_content"),
#         "error":             s.get("error"),
#     }

# # api_server.py — add this endpoint

# class ExtractRequest(BaseModel):
#     file_path: str
#     resource_type: str  # pdf, docx, pptx, audio, video, website

# @app.post("/extract")
# async def extract(body: ExtractRequest):
#     """Extract text from a resource file using the extractor wrapper."""
#     from wrapper import SimpleExtractorWrapper
#     extractor = SimpleExtractorWrapper()
    
#     type_map = {
#         "pdf":     extractor.extract_pdf,
#         "docx":    extractor.extract_docx,
#         "pptx":    extractor.extract_pptx,
#         "audio":   extractor.extract_audio,
#         "video":   extractor.extract_video,
#         "website": extractor.extract_url,
#     }
    
#     handler = type_map.get(body.resource_type.lower())
#     if not handler:
#         # fallback for txt files — just read
#         text = Path(body.file_path).read_text(encoding="utf-8", errors="ignore")
#     else:
#         loop = asyncio.get_event_loop()
#         text = await loop.run_in_executor(None, handler, body.file_path)
    
#     return {"text": text, "chars": len(text)}


# @app.get("/health")
# async def health():
#     return {"status": "ok", "graph_ready": _graph is not None}






# Lecture_Agent/api_server.py
# """
# FastAPI server for HoloLearn AI.

# It exposes:
# 1) Lecture Agent endpoints:
#    - POST /invoke
#    - POST /resume
#    - GET  /state/{thread_id}
#    - POST /extract

# 2) Research Agent endpoints:
#    - POST /research/invoke      # start async research run
#    - POST /research/run         # run and return result in same request
#    - GET  /research/state/{thread_id}
#    - GET  /research/tools
#    - GET  /research/health
# """

# from __future__ import annotations

# import asyncio
# import os
# import sys
# import uuid
# from contextlib import asynccontextmanager
# from dataclasses import asdict, is_dataclass
# from pathlib import Path
# from typing import Any, Dict, Optional

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field
# from langgraph.types import Command
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


# # ── Path setup ────────────────────────────────────────────────────────────────
# _AI_DIR = Path(__file__).resolve().parent                 # HoloLearn-AI/Lecture_Agent
# _PROJECT_ROOT = _AI_DIR.parent                            # HoloLearn-AI
# _GEN_ROOT = _PROJECT_ROOT / "generators"
# _RESEARCH_DIR = _PROJECT_ROOT / "Research_Agent"

# # Add project paths for Lecture Agent imports.
# for _p in [str(_PROJECT_ROOT), str(_AI_DIR)]:
#     if _p not in sys.path:
#         sys.path.insert(0, _p)

# for _sub in _GEN_ROOT.rglob("*.py"):
#     _d = str(_sub.parent)
#     if _d not in sys.path:
#         sys.path.insert(0, _d)

# # IMPORTANT:
# # Import the Lecture graph first and alias it.
# # This avoids confusion later because Research_Agent also has a package named "graph".
# from graph import build_graph as build_lecture_graph


# # ── Globals ───────────────────────────────────────────────────────────────────
# _graph = None                     # Lecture Agent LangGraph
# _research_graph = None            # Research Agent LangGraph
# _research_runs: Dict[str, dict] = {}   # In-memory status/results for research runs


# # ── Helpers ───────────────────────────────────────────────────────────────────

# def _load_research_graph():
#     """
#     Load Research_Agent/graph/research_graph.py safely.

#     The Lecture Agent has a local file named graph.py, while the Research Agent
#     has a package named graph/. Because Python caches imports in sys.modules,
#     we remove the old 'graph' module after importing the lecture graph, then
#     temporarily put Research_Agent first in sys.path.
#     """
#     global _research_graph

#     if not _RESEARCH_DIR.exists():
#         print("[api_server] ⚠️ Research_Agent folder not found; research endpoints disabled.")
#         return None

#     # Load Research_Agent/.env if it exists.
#     try:
#         from dotenv import load_dotenv
#         load_dotenv(dotenv_path=_RESEARCH_DIR / ".env", override=False)
#     except Exception:
#         pass

#     # Make Research_Agent imports resolve first.
#     research_path = str(_RESEARCH_DIR)
#     if research_path in sys.path:
#         sys.path.remove(research_path)
#     sys.path.insert(0, research_path)

#     # Remove conflicting cached modules from Lecture_Agent imports.
#     # Do NOT remove build_lecture_graph; it is already safely aliased above.
#     for module_name in [
#         "graph",
#         "graph.state",
#         "graph.research_graph",
#         "agent",
#         "agent.planner",
#         "agent.executor",
#         "schemas",
#         "tools",
#         "llm",
#         "prompts",
#         "utils",
#     ]:
#         sys.modules.pop(module_name, None)

#     try:
#         from graph.research_graph import build_graph as build_research_graph
#         _research_graph = build_research_graph()
#         print("[api_server] ✅ Research Agent graph ready")
#         return _research_graph
#     except Exception as exc:
#         print(f"[api_server] ⚠️ Failed to load Research Agent: {exc}")
#         _research_graph = None
#         return None


# def _run_in_background(coro):
#     return asyncio.create_task(coro)


# def _jsonable(obj: Any) -> Any:
#     """Convert Pydantic models/dataclasses/LangGraph state into JSON-safe data."""
#     if obj is None or isinstance(obj, (str, int, float, bool)):
#         return obj

#     if hasattr(obj, "model_dump"):
#         return _jsonable(obj.model_dump())

#     if is_dataclass(obj):
#         return _jsonable(asdict(obj))

#     if isinstance(obj, dict):
#         return {str(k): _jsonable(v) for k, v in obj.items()}

#     if isinstance(obj, (list, tuple, set)):
#         return [_jsonable(v) for v in obj]

#     return str(obj)


# def _summarize_research_state(final_state: dict) -> dict:
#     """Return a clean response for the backend/frontend."""
#     findings = final_state.get("findings", {}) or {}
#     completed = final_state.get("completed_step_ids", []) or []
#     plan = final_state.get("plan")

#     return {
#         "question": final_state.get("question"),
#         "domain": final_state.get("domain", "general"),
#         "next_action": final_state.get("next_action"),
#         "error_message": final_state.get("error_message"),
#         "steps_completed": len(completed),
#         "completed_step_ids": _jsonable(completed),
#         "plan": _jsonable(plan),
#         "findings": _jsonable(findings),
#     }


# async def _run_research_job(thread_id: str, question: str, domain: str = "general"):
#     """Background research runner used by /research/invoke."""
#     if _research_graph is None:
#         _research_runs[thread_id] = {
#             "status": "error",
#             "error": "Research Agent is not loaded.",
#         }
#         return

#     _research_runs[thread_id] = {
#         "status": "running",
#         "thread_id": thread_id,
#         "question": question,
#         "domain": domain,
#     }

#     initial_state = {
#         "question": question,
#         "domain": domain,
#         "plan": None,
#         "plan_revision": 0,
#         "findings": {},
#         "completed_step_ids": [],
#         "next_action": "execute",
#         "error_message": None,
#     }

#     try:
#         # Research graph is synchronous, so run it in a worker thread.
#         final_state = await asyncio.to_thread(_research_graph.invoke, initial_state)
#         _research_runs[thread_id] = {
#             "status": "completed",
#             "thread_id": thread_id,
#             "result": _summarize_research_state(final_state),
#         }
#     except Exception as exc:
#         _research_runs[thread_id] = {
#             "status": "error",
#             "thread_id": thread_id,
#             "question": question,
#             "domain": domain,
#             "error": str(exc),
#         }


# # ── App lifespan ──────────────────────────────────────────────────────────────

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global _graph

#     postgres_url = os.environ.get("POSTGRES_URL")
#     if not postgres_url:
#         raise RuntimeError("POSTGRES_URL not set in environment")

#     async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
#         await saver.setup()

#         # Lecture Agent graph with PostgreSQL checkpointing.
#         _graph = build_lecture_graph(checkpointer=saver)

#         # Research Agent graph. It does not currently use PostgreSQL checkpointing.
#         _load_research_graph()

#         print("[api_server] ✅ AI service ready on port 8001")
#         yield
#         print("[api_server] AI service shutting down")


# app = FastAPI(title="HoloLearn AI API", lifespan=lifespan)


# # ── Request models: Lecture Agent ─────────────────────────────────────────────

# class InvokeRequest(BaseModel):
#     thread_id: str
#     initial_state: Optional[dict] = None


# class ResumeRequest(BaseModel):
#     thread_id: str
#     status: str        # "approved" | "rejected"
#     feedback: str = ""


# class ExtractRequest(BaseModel):
#     file_path: str
#     resource_type: str  # pdf, docx, pptx, audio, video, website


# # ── Request models: Research Agent ────────────────────────────────────────────

# class ResearchInvokeRequest(BaseModel):
#     thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
#     question: str
#     domain: str = "general"


# class ResearchRunRequest(BaseModel):
#     question: str
#     domain: str = "general"


# # ── Lecture Agent endpoints ──────────────────────────────────────────────────

# @app.post("/invoke")
# async def invoke(body: InvokeRequest):
#     """
#     Start a new Lecture Agent run or resume a paused one.
#     Returns immediately; graph continues in background.
#     """
#     if _graph is None:
#         raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

#     config = {"configurable": {"thread_id": body.thread_id}}

#     if body.initial_state:
#         _run_in_background(_graph.ainvoke(body.initial_state, config))
#     else:
#         _run_in_background(
#             _graph.ainvoke(
#                 Command(resume={"status": "approved", "feedback": ""}),
#                 config,
#             )
#         )

#     return {"status": "started", "thread_id": body.thread_id}


# @app.post("/resume")
# async def resume(body: ResumeRequest):
#     if _graph is None:
#         raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

#     config = {"configurable": {"thread_id": body.thread_id}}

#     snapshot = await _graph.aget_state(config)
#     print(f"[resume] next nodes: {snapshot.next if snapshot else None}")

#     current_approval = {}
#     if snapshot and snapshot.values:
#         current_approval = snapshot.values.get("lecture_approval") or {}

#     iteration = current_approval.get("iteration", 0)
#     max_iter = current_approval.get("max_iterations", 3)

#     print(f"[resume] status={body.status} iteration={iteration} feedback={body.feedback}")

#     await _graph.aupdate_state(
#         config,
#         {
#             "lecture_approval": {
#                 "status": body.status,
#                 "teacher_feedback": body.feedback if body.status == "rejected" else None,
#                 "iteration": iteration,
#                 "max_iterations": max_iter,
#             }
#         },
#         as_node="interrupt_for_approval",
#     )

#     snapshot_after = await _graph.aget_state(config)
#     print(f"[resume] next after update: {snapshot_after.next if snapshot_after else None}")

#     _run_in_background(_graph.ainvoke(None, config))

#     return {"status": "resumed", "thread_id": body.thread_id}


# @app.get("/state/{thread_id}")
# async def get_state(thread_id: str):
#     """
#     Read Lecture Agent state from LangGraph checkpoint.
#     """
#     if _graph is None:
#         raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

#     config = {"configurable": {"thread_id": thread_id}}
#     snapshot = await _graph.aget_state(config)

#     if not snapshot or not snapshot.values:
#         return {}

#     s = snapshot.values
#     approval = s.get("lecture_approval") or {}

#     return {
#         "current_step": s.get("current_step"),
#         "approval_status": approval.get("status"),
#         "iteration": approval.get("iteration", 0),
#         "max_iterations": approval.get("max_iterations", 3),
#         "final_lecture": s.get("final_lecture"),
#         "lecture_paths": s.get("lecture_paths"),
#         "generated_content": s.get("generated_content"),
#         "error": s.get("error"),
#     }


# @app.post("/extract")
# async def extract(body: ExtractRequest):
#     """Extract text from a resource file using the extractor wrapper."""
#     from wrapper import SimpleExtractorWrapper

#     extractor = SimpleExtractorWrapper()

#     type_map = {
#         "pdf": extractor.extract_pdf,
#         "docx": extractor.extract_docx,
#         "pptx": extractor.extract_pptx,
#         "audio": extractor.extract_audio,
#         "video": extractor.extract_video,
#         "website": extractor.extract_url,
#     }

#     handler = type_map.get(body.resource_type.lower())
#     if not handler:
#         text = Path(body.file_path).read_text(encoding="utf-8", errors="ignore")
#     else:
#         text = await asyncio.to_thread(handler, body.file_path)

#     return {"text": text, "chars": len(text)}


# # ── Research Agent endpoints ─────────────────────────────────────────────────

# @app.post("/research/invoke")
# async def research_invoke(body: ResearchInvokeRequest):
#     """
#     Start Research Agent asynchronously.
#     Backend can poll GET /research/state/{thread_id}.
#     """
#     if _research_graph is None:
#         raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

#     if body.domain != "general":
#         raise HTTPException(status_code=400, detail="This Research Agent currently supports domain='general' only.")

#     _run_in_background(_run_research_job(body.thread_id, body.question, body.domain))

#     return {
#         "status": "started",
#         "thread_id": body.thread_id,
#         "poll_url": f"/research/state/{body.thread_id}",
#     }


# @app.post("/research/run")
# async def research_run(body: ResearchRunRequest):
#     """
#     Run Research Agent and return final result in the same request.
#     Use this for simple backend calls when you do not need polling.
#     """
#     if _research_graph is None:
#         raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

#     if body.domain != "general":
#         raise HTTPException(status_code=400, detail="This Research Agent currently supports domain='general' only.")

#     initial_state = {
#         "question": body.question,
#         "domain": body.domain,
#         "plan": None,
#         "plan_revision": 0,
#         "findings": {},
#         "completed_step_ids": [],
#         "next_action": "execute",
#         "error_message": None,
#     }

#     try:
#         final_state = await asyncio.to_thread(_research_graph.invoke, initial_state)
#         return {
#             "status": "completed",
#             "result": _summarize_research_state(final_state),
#         }
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))


# @app.get("/research/state/{thread_id}")
# async def research_state(thread_id: str):
#     """
#     Get status/result of an async Research Agent run.
#     """
#     run = _research_runs.get(thread_id)
#     if not run:
#         raise HTTPException(status_code=404, detail="Research thread_id not found.")

#     return run


# @app.get("/research/tools")
# async def research_tools():
#     """List tools available to the Research Agent."""
#     if _research_graph is None:
#         raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

#     try:
#         # Import after _load_research_graph() has configured sys.path.
#         from tools import list_tools
#         return {"domain": "general", "tools": list_tools("general")}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))


# @app.get("/research/health")
# async def research_health():
#     return {
#         "status": "ok" if _research_graph is not None else "not_ready",
#         "research_graph_ready": _research_graph is not None,
#         "research_dir_exists": _RESEARCH_DIR.exists(),
#         "active_or_saved_runs": len(_research_runs),
#     }


# @app.get("/health")
# async def health():
#     return {
#         "status": "ok",
#         "lecture_graph_ready": _graph is not None,
#         "research_graph_ready": _research_graph is not None,
#     }


# Lecture_Agent/api_server.py
"""
FastAPI server for HoloLearn AI.

It exposes:
1) Lecture Agent endpoints:
   - POST /invoke
   - POST /resume
   - GET  /state/{thread_id}
   - POST /extract

2) Research Agent endpoints:
   - POST /research/invoke      # start async research run
   - POST /research/run         # run and return result in same request
   - GET  /research/state/{thread_id}
   - GET  /research/tools
   - GET  /research/health
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


# ── Path setup ────────────────────────────────────────────────────────────────
_AI_DIR       = Path(__file__).resolve().parent          # HoloLearn-AI/Lecture_Agent
_PROJECT_ROOT = _AI_DIR.parent                           # HoloLearn-AI
_GEN_ROOT     = _PROJECT_ROOT / "generators"
_RESEARCH_DIR = _PROJECT_ROOT / "Research_Agent"

# Add project paths for Lecture Agent imports.
for _p in [str(_PROJECT_ROOT), str(_AI_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _sub in _GEN_ROOT.rglob("*.py"):
    _d = str(_sub.parent)
    if _d not in sys.path:
        sys.path.insert(0, _d)

# Import the Lecture graph first and alias it before any sys.modules manipulation.
# This prevents confusion when Research_Agent's 'graph' package is loaded later.
from graph import build_graph as build_lecture_graph


# ── Globals ───────────────────────────────────────────────────────────────────
_graph = None                          # Lecture Agent LangGraph
_research_graph = None                 # Research Agent LangGraph
_research_runs: Dict[str, dict] = {}   # In-memory status/results for research runs


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_research_graph():
    """
    Load Research_Agent/graph/research_graph.py safely.

    The Lecture Agent has a local file named graph.py, while the Research Agent
    has a package named graph/. Because Python caches imports in sys.modules,
    we remove the old 'graph' module after importing the lecture graph, then
    temporarily put Research_Agent first in sys.path.

    IMPORTANT — path restoration:
    After loading, this function MUST restore _PROJECT_ROOT to the front of
    sys.path and re-anchor utils/ to HoloLearn-AI/utils/. Without this,
    all subsequent 'from utils.configs import ...' calls (inside the extractor
    modules) would resolve to Research_Agent/utils/ (wrong) or fail entirely.
    """
    global _research_graph

    if not _RESEARCH_DIR.exists():
        print("[api_server] ⚠️  Research_Agent folder not found; research endpoints disabled.")
        return None

    # Load Research_Agent/.env if it exists.
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_RESEARCH_DIR / ".env", override=False)
    except Exception:
        pass

    # Snapshot the current utils modules so we can restore them afterwards.
    _saved_utils = {
        k: v for k, v in sys.modules.items()
        if k == "utils" or k.startswith("utils.")
    }

    research_path = str(_RESEARCH_DIR)

    # Put Research_Agent at the front temporarily so its packages resolve first.
    if research_path in sys.path:
        sys.path.remove(research_path)
    sys.path.insert(0, research_path)

    # Remove conflicting cached modules from Lecture_Agent imports.
    # Do NOT remove build_lecture_graph — it is already safely aliased above.
    for module_name in [
        "graph",
        "graph.state",
        "graph.research_graph",
        "agent",
        "agent.planner",
        "agent.executor",
        "schemas",
        "tools",
        "llm",
        "prompts",
        "utils",
    ]:
        sys.modules.pop(module_name, None)

    try:
        from graph.research_graph import build_graph as build_research_graph
        _research_graph = build_research_graph()
        print("[api_server] ✅ Research Agent graph ready")
    except Exception as exc:
        print(f"[api_server] ⚠️  Failed to load Research Agent: {exc}")
        _research_graph = None
    finally:
        # ── Restore Lecture Agent path priority ───────────────────────────────
        # Move Research_Agent/ to the END of sys.path.
        # It stays importable (needed if Research Agent code does dynamic imports
        # at runtime), but Lecture Agent packages now resolve first again.
        if research_path in sys.path:
            sys.path.remove(research_path)
        sys.path.append(research_path)

        # Re-insert _PROJECT_ROOT at the front so HoloLearn-AI/utils/ is found
        # before anything in Research_Agent/ on every subsequent import.
        project_root = str(_PROJECT_ROOT)
        if project_root in sys.path:
            sys.path.remove(project_root)
        sys.path.insert(0, project_root)

        # Clear any stale/wrong utils cache entries that landed during loading
        # and restore the original Lecture-Agent-side utils modules.
        for mod in [k for k in sys.modules if k == "utils" or k.startswith("utils.")]:
            sys.modules.pop(mod, None)
        sys.modules.update(_saved_utils)

        print(f"[api_server] sys.path restored — root: {sys.path[0]}")
        # ─────────────────────────────────────────────────────────────────────

    return _research_graph


def _run_in_background(coro):
    return asyncio.create_task(coro)


def _jsonable(obj: Any) -> Any:
    """Convert Pydantic models/dataclasses/LangGraph state into JSON-safe data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return _jsonable(obj.model_dump())
    if is_dataclass(obj):
        return _jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    return str(obj)


def _summarize_research_state(final_state: dict) -> dict:
    """Return a clean response for the backend/frontend."""
    findings  = final_state.get("findings", {}) or {}
    completed = final_state.get("completed_step_ids", []) or []
    plan      = final_state.get("plan")

    return {
        "question":           final_state.get("question"),
        "domain":             final_state.get("domain", "general"),
        "next_action":        final_state.get("next_action"),
        "error_message":      final_state.get("error_message"),
        "steps_completed":    len(completed),
        "completed_step_ids": _jsonable(completed),
        "plan":               _jsonable(plan),
        "findings":           _jsonable(findings),
    }


async def _run_research_job(thread_id: str, question: str, domain: str = "general"):
    """Background research runner used by /research/invoke."""
    if _research_graph is None:
        _research_runs[thread_id] = {
            "status": "error",
            "error":  "Research Agent is not loaded.",
        }
        return

    _research_runs[thread_id] = {
        "status":    "running",
        "thread_id": thread_id,
        "question":  question,
        "domain":    domain,
    }

    initial_state = {
        "question":           question,
        "domain":             domain,
        "plan":               None,
        "plan_revision":      0,
        "findings":           {},
        "completed_step_ids": [],
        "next_action":        "execute",
        "error_message":      None,
    }

    try:
        final_state = await asyncio.to_thread(_research_graph.invoke, initial_state)
        _research_runs[thread_id] = {
            "status":    "completed",
            "thread_id": thread_id,
            "result":    _summarize_research_state(final_state),
        }
    except Exception as exc:
        _research_runs[thread_id] = {
            "status":    "error",
            "thread_id": thread_id,
            "question":  question,
            "domain":    domain,
            "error":     str(exc),
        }


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph

    postgres_url = os.environ.get("POSTGRES_URL")
    if not postgres_url:
        raise RuntimeError("POSTGRES_URL not set in environment")

    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()

        # Lecture Agent graph with PostgreSQL checkpointing.
        _graph = build_lecture_graph(checkpointer=saver)

        # Research Agent graph (does not use PostgreSQL checkpointing).
        # _load_research_graph() restores sys.path in its finally block,
        # so extractor imports remain healthy after this call.
        _load_research_graph()

        print("[api_server] ✅ AI service ready on port 8001")
        yield
        print("[api_server] AI service shutting down")


app = FastAPI(title="HoloLearn AI API", lifespan=lifespan)


# ── Request models: Lecture Agent ─────────────────────────────────────────────

class InvokeRequest(BaseModel):
    thread_id:     str
    initial_state: Optional[dict] = None


class ResumeRequest(BaseModel):
    thread_id: str
    status:    str        # "approved" | "rejected"
    feedback:  str = ""


class ExtractRequest(BaseModel):
    file_path:     str
    resource_type: str   # pdf, docx, pptx, audio, video, website


# ── Request models: Research Agent ────────────────────────────────────────────

class ResearchInvokeRequest(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question:  str
    domain:    str = "general"


class ResearchRunRequest(BaseModel):
    question: str
    domain:   str = "general"


# ── Lecture Agent endpoints ───────────────────────────────────────────────────

@app.post("/invoke")
async def invoke(body: InvokeRequest):
    """
    Start a new Lecture Agent run or resume a paused one.
    Returns immediately; graph continues in background.
    """
    if _graph is None:
        raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

    config = {"configurable": {"thread_id": body.thread_id}}

    if body.initial_state:
        _run_in_background(_graph.ainvoke(body.initial_state, config))
    else:
        _run_in_background(
            _graph.ainvoke(
                Command(resume={"status": "approved", "feedback": ""}),
                config,
            )
        )

    return {"status": "started", "thread_id": body.thread_id}


@app.post("/resume")
async def resume(body: ResumeRequest):
    if _graph is None:
        raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

    config   = {"configurable": {"thread_id": body.thread_id}}
    snapshot = await _graph.aget_state(config)
    print(f"[resume] next nodes: {snapshot.next if snapshot else None}")

    current_approval = {}
    if snapshot and snapshot.values:
        current_approval = snapshot.values.get("lecture_approval") or {}

    iteration = current_approval.get("iteration", 0)
    max_iter  = current_approval.get("max_iterations", 3)

    print(f"[resume] status={body.status} iteration={iteration} feedback={body.feedback}")

    await _graph.aupdate_state(
        config,
        {
            "lecture_approval": {
                "status":           body.status,
                "teacher_feedback": body.feedback if body.status == "rejected" else None,
                "iteration":        iteration,
                "max_iterations":   max_iter,
            }
        },
        as_node="interrupt_for_approval",
    )

    snapshot_after = await _graph.aget_state(config)
    print(f"[resume] next after update: {snapshot_after.next if snapshot_after else None}")

    _run_in_background(_graph.ainvoke(None, config))

    return {"status": "resumed", "thread_id": body.thread_id}


@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    """Read Lecture Agent state from LangGraph checkpoint."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Lecture Agent graph is not ready.")

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


@app.post("/extract")
async def extract(body: ExtractRequest):
    """Extract text from a resource file using the extractor wrapper."""
    from wrapper import SimpleExtractorWrapper

    extractor = SimpleExtractorWrapper()

    type_map = {
        "pdf":     extractor.extract_pdf,
        "docx":    extractor.extract_docx,
        "pptx":    extractor.extract_pptx,
        "audio":   extractor.extract_audio,
        "video":   extractor.extract_video,
        "website": extractor.extract_url,
    }

    handler = type_map.get(body.resource_type.lower())
    if not handler:
        text = Path(body.file_path).read_text(encoding="utf-8", errors="ignore")
    else:
        text = await asyncio.to_thread(handler, body.file_path)

    return {"text": text, "chars": len(text)}


# ── Research Agent endpoints ──────────────────────────────────────────────────

@app.post("/research/invoke")
async def research_invoke(body: ResearchInvokeRequest):
    """Start Research Agent asynchronously. Poll GET /research/state/{thread_id}."""
    if _research_graph is None:
        raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

    if body.domain != "general":
        raise HTTPException(status_code=400, detail="This Research Agent currently supports domain='general' only.")

    _run_in_background(_run_research_job(body.thread_id, body.question, body.domain))

    return {
        "status":    "started",
        "thread_id": body.thread_id,
        "poll_url":  f"/research/state/{body.thread_id}",
    }


@app.post("/research/run")
async def research_run(body: ResearchRunRequest):
    """Run Research Agent and return final result in the same request."""
    if _research_graph is None:
        raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

    if body.domain != "general":
        raise HTTPException(status_code=400, detail="This Research Agent currently supports domain='general' only.")

    initial_state = {
        "question":           body.question,
        "domain":             body.domain,
        "plan":               None,
        "plan_revision":      0,
        "findings":           {},
        "completed_step_ids": [],
        "next_action":        "execute",
        "error_message":      None,
    }

    try:
        final_state = await asyncio.to_thread(_research_graph.invoke, initial_state)
        return {
            "status": "completed",
            "result": _summarize_research_state(final_state),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/research/state/{thread_id}")
async def research_state(thread_id: str):
    """Get status/result of an async Research Agent run."""
    run = _research_runs.get(thread_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research thread_id not found.")
    return run


@app.get("/research/tools")
async def research_tools():
    """List tools available to the Research Agent."""
    if _research_graph is None:
        raise HTTPException(status_code=503, detail="Research Agent graph is not ready.")

    try:
        from tools import list_tools
        return {"domain": "general", "tools": list_tools("general")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/research/health")
async def research_health():
    return {
        "status":               "ok" if _research_graph is not None else "not_ready",
        "research_graph_ready": _research_graph is not None,
        "research_dir_exists":  _RESEARCH_DIR.exists(),
        "active_or_saved_runs": len(_research_runs),
    }


@app.get("/health")
async def health():
    return {
        "status":               "ok",
        "lecture_graph_ready":  _graph is not None,
        "research_graph_ready": _research_graph is not None,
    }