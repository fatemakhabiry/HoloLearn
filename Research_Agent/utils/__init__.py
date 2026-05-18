"""Utility helpers — pretty printing and result formatting."""
from __future__ import annotations
from typing import Any, Dict


def print_plan(state: Dict[str, Any]) -> None:
    """Pretty-print the investigation plan from AgentState."""
    plan = state.get("plan")
    if not plan:
        print("No plan found in state.")
        return

    print("\n" + "═" * 70)
    print("  INVESTIGATION PLAN")
    print("═" * 70)
    for s in plan.steps:
        deps = f" (depends on: {', '.join(s.depends_on)})" if s.depends_on else ""
        print(
            f"  [{s.step_id}] w={s.weight:.3f} | tool={s.tool:<12}"
            f"{deps}\n  → {s.sub_question}\n"
        )


def print_findings(state: Dict[str, Any]) -> None:
    """Pretty-print all findings from AgentState."""
    findings = state.get("findings", {})
    if not findings:
        print("No findings yet.")
        return

    print("\n" + "═" * 70)
    print("  FINDINGS")
    print("═" * 70)
    for key, f in findings.items():
        status_icon = {"done": "✓", "error": "✗", "running": "…"}.get(f.status, "?")
        print(f"\n  {status_icon} [{f.step_id}] {f.sub_question}")
        print(f"    Tool: {f.tool} | Credibility: {f.credibility_score:.2f}")
        print(f"    Key:  {f.finding_key}")
        print()
        # Indent content
        for line in f.content.split("\n")[:8]:   # first 8 lines
            print(f"    {line}")
        if f.content.count("\n") > 8:
            print("    …")
        if f.sources:
            print(f"\n    Sources ({len(f.sources)}):")
            for src in f.sources[:4]:
                print(f"      • {src}")
        print()


def findings_to_dict(state: Dict[str, Any]) -> list[dict]:
    """Convert findings to a list of plain dicts (JSON-serialisable)."""
    findings = state.get("findings", {})
    out = []
    for key, f in findings.items():
        out.append({
            "step_id": f.step_id,
            "sub_question": f.sub_question,
            "tool": f.tool,
            "finding_key": f.finding_key,
            "status": f.status,
            "credibility_score": f.credibility_score,
            "content": f.content,
            "sources": f.sources,
            "error": f.error,
        })
    return out
