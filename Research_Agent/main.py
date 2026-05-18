"""
main.py — Entry point for the Research Agent (Planner + Executor cut).

Run from HoloLearn-AI root:
    python Research_Agent/main.py
    python Research_Agent/main.py --question "What is quantum computing?"
    python Research_Agent/main.py --json

Run from inside Research_Agent/:
    python main.py
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
import os
from pathlib import Path

# ── Ensure Research_Agent/ is on sys.path regardless of CWD ─────────────────
_agent_root = Path(__file__).resolve().parent
if str(_agent_root) not in sys.path:
    sys.path.insert(0, str(_agent_root))

# ── Load .env early (before any other import that needs keys) ────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_agent_root / ".env", override=False)
except ImportError:
    pass

# ── Now safe to import agent modules ─────────────────────────────────────────
from graph.research_graph import research_graph
from utils import print_plan, print_findings, findings_to_dict

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run(question: str, domain: str = "general", output_json: bool = False) -> dict:
    """
    Run the research agent for a given question.
    Returns the final AgentState dict.
    """
    logger.info(f"Starting research run: {question!r}")

    initial_state = {
        "question": question,
        "domain": domain,
        "plan": None,
        "plan_revision": 0,
        "findings": {},
        "completed_step_ids": [],
        "next_action": "execute",
        "error_message": None,
    }

    final_state = research_graph.invoke(initial_state)

    if final_state.get("error_message"):
        print(f"\n⚠  Agent error: {final_state['error_message']}", file=sys.stderr)
        return final_state

    print_plan(final_state)
    print_findings(final_state)

    findings  = final_state.get("findings", {})
    completed = final_state.get("completed_step_ids", [])
    done_count = sum(1 for f in findings.values() if f.status == "done")
    err_count  = sum(1 for f in findings.values() if f.status == "error")

    print("═" * 70)
    print(f"  SUMMARY  |  Steps completed: {len(completed)}"
          f"  |  OK: {done_count}  |  Errors: {err_count}")
    print("═" * 70 + "\n")

    if output_json:
        data = {
            "question": question,
            "domain": domain,
            "steps_completed": len(completed),
            "findings": findings_to_dict(final_state),
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))

    return final_state


def main():
    parser = argparse.ArgumentParser(
        description="Research Agent — Planner + Executor (general domain)"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        default=None,
        help="Research question (omit to be prompted interactively)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print findings as JSON at the end",
    )
    args = parser.parse_args()

    if args.question:
        question = args.question.strip()
    else:
        print("\n" + "═" * 70)
        print("  RESEARCH AGENT  —  Planner + Executor  (general domain)")
        print("═" * 70)
        question = input("\n  Enter your research question:\n  > ").strip()
        if not question:
            print("No question provided. Exiting.")
            sys.exit(1)

    run(question=question, domain="general", output_json=args.json)


if __name__ == "__main__":
    main()
