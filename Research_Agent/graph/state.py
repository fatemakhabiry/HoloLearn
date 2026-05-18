"""
AgentState — the single shared state object passed through the LangGraph graph.
Every node reads from it and returns only the fields it changed.
LangGraph merges partial updates automatically.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict
from schemas import InvestigationPlan, Finding


class AgentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────────────
    question: str           # The original research question
    domain: str             # Always "general" for this cut

    # ── Plan ─────────────────────────────────────────────────────────────────
    plan: Optional[InvestigationPlan]
    plan_revision: int      # 0 = original; increments on replan (reserved)

    # ── Execution ────────────────────────────────────────────────────────────
    findings: Dict[str, Finding]   # finding_key → Finding
    completed_step_ids: List[str]  # step_ids that finished (done or error)

    # ── Routing ──────────────────────────────────────────────────────────────
    next_action: str        # "continue" | "execute" | "done" | "error"
    error_message: Optional[str]
