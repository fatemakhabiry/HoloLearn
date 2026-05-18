"""
Executor node — runs tool steps in parallel using asyncio.gather.

For each step:
  1. LLM generates an optimised search query from the sub-question.
  2. The registered tool is called with that query.
  3. Result is stored in AgentState.findings.

Only steps whose depends_on are already in completed_step_ids are executed
('ready batch'). This mirrors the doc §3.2 design exactly.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List

from schemas import Finding, ToolResult
from tools import build_registry
from prompts import build_executor_system_prompt, build_executor_user_prompt
from llm import call_llm

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = int(__import__("os").getenv("MAX_TOOL_CALLS", 50))


# ── Query optimiser (Executor LLM call) ──────────────────────────────────────

def _optimise_query(main_question: str, sub_question: str, tool: str) -> str:
    """Ask the LLM for an optimised search query for the given sub-question."""
    system = (
        f"You are a search query optimiser. Given a research sub-question, "
        f"return ONLY a short, precise search query (max 12 words) optimised "
        f"for the '{tool}' tool. No explanation, no punctuation at the end."
    )
    user = f'Sub-question: "{sub_question}"'
    try:
        query = call_llm(
            messages=[{"role": "user", "content": user}],
            role="tool-caller",
            system=system,
            temperature=0.0,
            max_tokens=64,
        )
        return query.strip().strip('"').strip("'")
    except Exception:
        # Fallback: use sub_question directly
        return sub_question


# ── Single step execution ─────────────────────────────────────────────────────

async def _execute_step(
    main_question: str,
    step,          # PlanStep
    registry: Dict,
) -> Finding:
    """Execute one plan step asynchronously."""
    logger.info(f"[Executor] Running {step.step_id}: {step.sub_question[:60]!r}")

    # Query optimisation (sync in thread to avoid blocking event loop)
    loop = asyncio.get_event_loop()
    query = await loop.run_in_executor(
        None, _optimise_query, main_question, step.sub_question, step.tool
    )
    logger.debug(f"[Executor] {step.step_id} optimised query: {query!r}")

    # Tool call
    tool_fn = registry.get(step.tool)
    if tool_fn is None:
        return Finding(
            step_id=step.step_id,
            sub_question=step.sub_question,
            tool=step.tool,
            finding_key=step.finding_key,
            content=f"[Error: tool '{step.tool}' not found in registry]",
            status="error",
            error=f"Tool '{step.tool}' not registered",
        )

    try:
        result: ToolResult = await loop.run_in_executor(None, tool_fn, query)
        return Finding(
            step_id=step.step_id,
            sub_question=step.sub_question,
            tool=step.tool,
            finding_key=step.finding_key,
            content=result.content,
            sources=result.sources,
            credibility_score=result.credibility_score,
            status="done",
        )
    except Exception as exc:
        logger.error(f"[Executor] {step.step_id} tool error: {exc}")
        return Finding(
            step_id=step.step_id,
            sub_question=step.sub_question,
            tool=step.tool,
            finding_key=step.finding_key,
            content=f"[Tool error: {exc}]",
            status="error",
            error=str(exc),
        )


# ── Executor node ─────────────────────────────────────────────────────────────

def executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Executor.

    Reads:   state["question"], state["plan"], state["completed_step_ids"],
             state["findings"]
    Returns: updated {"findings", "completed_step_ids", "next_action"}
    """
    question: str = state["question"]
    plan = state["plan"]
    completed: List[str] = list(state.get("completed_step_ids", []))
    findings: Dict[str, Finding] = dict(state.get("findings", {}))
    domain: str = state.get("domain", "general")

    # Guard: tool call budget
    total_calls = len(completed)
    if total_calls >= MAX_TOOL_CALLS:
        logger.warning("[Executor] MAX_TOOL_CALLS reached — forcing done.")
        return {"next_action": "done", "completed_step_ids": completed, "findings": findings}

    # Build tool registry for domain
    registry = build_registry(domain)

    # Identify ready batch: steps whose depends_on are all satisfied
    completed_set = set(completed)
    ready = [
        s for s in plan.steps
        if s.step_id not in completed_set
        and all(dep in completed_set for dep in s.depends_on)
    ]
    ready.sort(key=lambda s: s.priority)

    if not ready:
        logger.info("[Executor] No ready steps — all done.")
        return {"next_action": "done", "completed_step_ids": completed, "findings": findings}

    logger.info(f"[Executor] Ready batch: {[s.step_id for s in ready]}")

    # Run ready batch in parallel
    async def run_batch():
        tasks = [_execute_step(question, step, registry) for step in ready]
        return await asyncio.gather(*tasks)

    loop = asyncio.new_event_loop()
    try:
        results: List[Finding] = loop.run_until_complete(run_batch())
    finally:
        loop.close()

    # Merge results into state
    for finding in results:
        findings[finding.finding_key] = finding
        completed.append(finding.step_id)
        logger.info(
            f"[Executor] {finding.step_id} → status={finding.status} "
            f"| credibility={finding.credibility_score:.2f}"
        )

    # Check if all steps are now completed
    all_step_ids = {s.step_id for s in plan.steps}
    remaining = all_step_ids - set(completed)

    next_action = "execute" if remaining else "done"
    logger.info(
        f"[Executor] Batch done. Remaining steps: {remaining or 'none'} → {next_action}"
    )

    return {
        "findings": findings,
        "completed_step_ids": completed,
        "next_action": next_action,
    }
