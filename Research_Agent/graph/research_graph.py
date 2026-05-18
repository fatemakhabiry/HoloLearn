"""
LangGraph StateGraph — Planner → Executor (→ Executor loop) → END.

This is the cut version of the full pipeline:
  Full pipeline: Planner → Executor → Reflector → (Replanner) → Synthesiser
  This cut:      Planner → Executor → (loop until all steps done) → END

The graph is compiled ONCE at module import and reused for all runs.
"""
from __future__ import annotations
import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agent.planner import planner_node
from agent.executor import executor_node

logger = logging.getLogger(__name__)


# ── Routing function ──────────────────────────────────────────────────────────

def route_after_executor(state: Dict[str, Any]) -> str:
    """
    Conditional edge after Executor.
      - "execute"  → loop back to Executor (more steps remain)
      - "done"     → END
      - "error"    → END
    """
    action = state.get("next_action", "done")
    logger.debug(f"[Router] next_action={action!r}")
    return action


def route_after_planner(state: Dict[str, Any]) -> str:
    action = state.get("next_action", "execute")
    return action   # "execute" or "error"


# ── Build & compile graph ─────────────────────────────────────────────────────

def build_graph() -> Any:
    """Build and compile the LangGraph StateGraph."""
    builder = StateGraph(AgentState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)

    # ── Entry point ──────────────────────────────────────────────────────────
    builder.set_entry_point("planner")

    # ── Edges ────────────────────────────────────────────────────────────────
    # Planner → Executor (or END on error)
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "execute": "executor",
            "error": END,
        },
    )

    # Executor → loop or END
    builder.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "execute": "executor",   # more steps remain
            "done": END,
            "error": END,
        },
    )

    graph = builder.compile()
    logger.info("[Graph] Research graph compiled successfully.")
    return graph


# Singleton — compiled once at import
research_graph = build_graph()
