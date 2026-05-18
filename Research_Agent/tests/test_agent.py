"""
tests/test_agent.py — Unit + smoke tests (no LLM or API keys required).

Run:
    cd research_agent
    pytest tests/test_agent.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from schemas import InvestigationPlan, PlanStep, Finding, ToolResult
from prompts import build_planner_system_prompt, build_planner_user_prompt
from prompts.personas.general import PERSONA
from tools import build_registry, list_tools
from utils import findings_to_dict


# ── Schema tests ─────────────────────────────────────────────────────────────

def test_plan_step_creation():
    step = PlanStep(
        step_id="step_1",
        sub_question="What is quantum computing?",
        tool="wikipedia",
        finding_key="background",
        weight=0.20,
    )
    assert step.step_id == "step_1"
    assert step.depends_on == []


def test_investigation_plan_normalise():
    steps = [
        PlanStep(step_id=f"step_{i}", sub_question="Q", tool="web_search",
                 finding_key=f"k_{i}", weight=1.0)
        for i in range(1, 5)
    ]
    plan = InvestigationPlan(steps=steps)
    plan.normalize_weights()
    total = sum(s.weight for s in plan.steps)
    assert abs(total - 1.0) < 0.01


# ── Prompt tests ──────────────────────────────────────────────────────────────

def test_planner_system_prompt_contains_rules():
    prompt = build_planner_system_prompt(PERSONA)
    assert "TOOL RULES" in prompt
    assert "PLANNING RULES" in prompt
    assert "web_search" in prompt
    assert "wikipedia" in prompt


def test_planner_user_prompt():
    q = "What is the future of renewable energy?"
    prompt = build_planner_user_prompt(q)
    assert q in prompt


# ── Tool registry tests ───────────────────────────────────────────────────────

def test_general_registry_has_expected_tools():
    tools = list_tools("general")
    assert "web_search" in tools
    assert "wikipedia" in tools


def test_unsupported_domain_raises():
    with pytest.raises(ValueError, match="Unsupported domain"):
        build_registry("poultry")


# ── Finding tests ─────────────────────────────────────────────────────────────

def test_finding_to_dict():
    f = Finding(
        step_id="step_1",
        sub_question="Q?",
        tool="web_search",
        finding_key="key_1",
        content="Some content",
        sources=["https://example.com"],
        credibility_score=0.75,
        status="done",
    )
    state = {"findings": {"key_1": f}}
    result = findings_to_dict(state)
    assert len(result) == 1
    assert result[0]["step_id"] == "step_1"
    assert result[0]["status"] == "done"


# ── Graph structure test ──────────────────────────────────────────────────────

def test_graph_compiles():
    from graph.research_graph import research_graph
    assert research_graph is not None


def test_graph_nodes():
    from graph.research_graph import research_graph
    # LangGraph compiled graphs expose their nodes
    nodes = research_graph.nodes
    assert "planner" in nodes
    assert "executor" in nodes
