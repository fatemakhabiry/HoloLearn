"""
Planner node — entry point for every research run.

Receives the research question + domain, makes one LLM call, returns an
InvestigationPlan of 6-10 steps. Retries up to 3 times on JSON parse errors.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict

from schemas import InvestigationPlan
from prompts import build_planner_system_prompt, build_planner_user_prompt
from prompts.personas.general import PERSONA
from llm import call_llm

logger = logging.getLogger(__name__)

MAX_PLANNER_RETRIES = 3


def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Planner.

    Reads:   state["question"], state["domain"]
    Returns: {"plan": InvestigationPlan, "plan_revision": 0,
               "findings": {}, "completed_step_ids": [],
               "next_action": "execute"}
    """
    question: str = state["question"]
    domain: str = state.get("domain", "general")

    if domain != "general":
        raise ValueError(f"This build only supports domain='general', got '{domain}'.")

    persona = PERSONA
    system_prompt = build_planner_system_prompt(persona)
    user_prompt = build_planner_user_prompt(question)

    logger.info(f"[Planner] Planning for question: {question!r}")

    last_error = None
    for attempt in range(1, MAX_PLANNER_RETRIES + 1):
        raw = call_llm(
            messages=[{"role": "user", "content": user_prompt}],
            role="flash",
            system=system_prompt,
            temperature=0.1,
            max_tokens=2048,
        )

        # Strip markdown fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()

        try:
            data = json.loads(clean)
            plan = InvestigationPlan(**data)
            plan.normalize_weights()

            logger.info(
                f"[Planner] Plan created — {len(plan.steps)} steps "
                f"(attempt {attempt})"
            )
            for s in plan.steps:
                logger.debug(
                    f"  {s.step_id} | tool={s.tool} | w={s.weight:.3f} | {s.sub_question[:60]}"
                )

            return {
                "plan": plan,
                "plan_revision": 0,
                "findings": {},
                "completed_step_ids": [],
                "next_action": "execute",
            }

        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning(f"[Planner] Parse error on attempt {attempt}: {exc}")

    # All retries exhausted
    logger.error(f"[Planner] Failed after {MAX_PLANNER_RETRIES} attempts: {last_error}")
    return {
        "next_action": "error",
        "error_message": f"Planner failed to produce a valid plan: {last_error}",
    }
