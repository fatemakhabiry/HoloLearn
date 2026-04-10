# Lecture_Agent/test_real.py

import sys
from pathlib import Path

# ── Path fixes — must be first ────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_AGENT_DIR    = Path(__file__).parent
_GEN_ROOT     = _PROJECT_ROOT / "generators"

for _p in [str(_PROJECT_ROOT), str(_AGENT_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _sub in _GEN_ROOT.rglob("*.py"):
    _d = str(_sub.parent)
    if _d not in sys.path:
        sys.path.insert(0, _d)
# ─────────────────────────────────────────────────────────────────────────────

import uuid
import textwrap
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

load_dotenv()

from state import AgentState
from graph import build_graph

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_BASE = _PROJECT_ROOT / "test_real_output"
OUTPUT_BASE.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _divider(label: str = "", width: int = 65):
    if label:
        pad = (width - len(label) - 2) // 2
        print("\n" + "═" * pad + f" {label} " + "═" * pad)
    else:
        print("\n" + "─" * width)


def _ask(prompt: str, valid: list[str]) -> str:
    while True:
        val = input(prompt).strip().lower()
        if val in valid:
            return val
        print(f"  Please enter one of: {valid}")


def _read_multiline(prompt: str) -> str:
    """Read multi-line input until user enters a blank line."""
    print(prompt)
    print("(Press Enter on an empty line when done)")
    lines = []
    while True:
        line = input()
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _show_lecture_preview(state: dict):
    """Tell the teacher where the PDF is so they can open and review it."""
    paths    = state.get("lecture_paths") or {}
    approval = state.get("lecture_approval") or {}
    iteration = approval.get("iteration", 0)

    _divider(f"LECTURE VERSION {iteration} — READY FOR REVIEW")

    pdf_path = paths.get("pdf")
    txt_path = paths.get("txt")

    if pdf_path and Path(pdf_path).exists():
        print(f"\n  PDF ready → {pdf_path}")
        print(f"\n  Open the PDF, read the lecture, then come back here.")

        # Try to open the PDF automatically with the system default viewer
        try:
            import os
            os.startfile(pdf_path)          # Windows
            print("  (Opening PDF automatically...)")
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["open", pdf_path])   # macOS fallback
            except Exception:
                pass                                    # user opens manually
    else:
        print("  ⚠  PDF not found — falling back to text preview")
        text = state.get("final_lecture") or ""
        preview = text[:800] + ("..." if len(text) > 800 else "")
        print(preview)

    if txt_path:
        print(f"\n  TXT also available → {txt_path}")

    _divider()


def _show_results(state: dict):
    """Print all generated output file paths."""
    _divider("GENERATED OUTPUT")

    lp = state.get("lecture_paths") or {}
    if any(lp.values()):
        print("\n  LECTURE FILES:")
        for k, v in lp.items():
            if v:
                print(f"    {k:8s} → {v}")

    gc = state.get("generated_content") or {}
    for gen_name, val in gc.items():
        print(f"\n  {gen_name.upper()}:")
        if val is None:
            print("    ❌  failed or skipped")
        else:
            for file_key, path in val.items():
                status = f"→ {path}" if path else "❌  not produced"
                print(f"    {file_key:20s} {status}")

    manifest = Path(state["meta"]["output_dir"]) / "manifest.json"
    if manifest.exists():
        print(f"\n  MANIFEST  → {manifest}")

    _divider()


def _teacher_hitl(state: dict) -> tuple[str, str]:
    """
    Show the lecture preview and ask the teacher to approve or reject.
    Returns (status, feedback).
    """
    _show_lecture_preview(state)
    approval = state.get("lecture_approval", {})
    iteration = approval.get("iteration", 0)
    max_iter  = approval.get("max_iterations", 3)

    print(f"  Revision {iteration} of {max_iter} maximum.")
    choice = _ask(
        "\n  Approve this lecture? [a = approve  /  r = reject with feedback]: ",
        ["a", "r"],
    )

    if choice == "a":
        return "approved", ""

    feedback = ""
    while not feedback.strip():
        feedback = input("  Enter your revision feedback: ").strip()
        if not feedback:
            print("  Feedback cannot be empty.")
    return "rejected", feedback


# ─────────────────────────────────────────────────────────────────────────────
# STATE BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_prepared_state(session_id: str) -> AgentState:
    """
    PATH A — teacher provides their own lecture as a .txt file.
    No LLM call for lecture generation.
    """
    _divider("PATH A — PREPARED LECTURE INPUT")

    while True:
        raw = input("\nPath to your lecture .txt file: ").strip().strip('"')
        source_path = Path(raw)
        if source_path.exists() and source_path.suffix.lower() == ".txt":
            break
        if not source_path.exists():
            print(f"  File not found: {source_path}")
        else:
            print("  File must be a .txt file.")

    prepared_text = source_path.read_text(encoding="utf-8", errors="ignore").strip()

    if not prepared_text:
        raise ValueError(f"File is empty: {source_path}")

    print(f"  Loaded {len(prepared_text):,} characters from {source_path.name}")

    topic = input("\nLecture topic / title: ").strip()
    if not topic:
        topic = source_path.stem
        print(f"  Using filename as topic: '{topic}'")

    course_code = input("Course code (e.g. CS101) [optional, press Enter to skip]: ").strip()
    if not course_code:
        course_code = "COURSE"

    output_dir = OUTPUT_BASE / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "meta": {
            "session_id":  session_id,
            "teacher_id":  "teacher-terminal",
            "course_code": course_code,
            "title":       topic,
            "output_dir":  str(output_dir),
        },
        "source": {
            "type":          "prepared_lecture",
            "prepared_text": prepared_text,
            "pdf":     None,
            "docx":    None,
            "pptx":    None,
            "audio":   None,
            "video":   None,
            "website": None,
            "images":  None,
        },
        "final_lecture":    None,
        "lecture_paths":    None,
        "lecture_approval": None,
        "generated_content": {
            "script":          None,
            "worksheet":       None,
            "quiz":            None,
            "summary":         None,
            "flowchart":       None,
            "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }


def _build_generated_state(session_id: str) -> AgentState:
    """
    PATH B — agent generates the lecture from a source file.
    Teacher is prompted for the source file path and query.
    """
    _divider("PATH B — GENERATED LECTURE INPUT")

    # Source file
    while True:
        raw = input("\nPath to source text file (.txt): ").strip().strip('"')
        source_path = Path(raw)
        if source_path.exists() and source_path.suffix.lower() == ".txt":
            break
        if not source_path.exists():
            print(f"  File not found: {source_path}")
        else:
            print("  File must be a .txt file (pre-extracted text).")

    source_text = source_path.read_text(encoding="utf-8", errors="ignore")
    print(f"  Loaded {len(source_text):,} characters from {source_path.name}")

    query = input("\nExtraction query (e.g. 'explain all key concepts'): ").strip()
    if not query:
        query = f"explain all key concepts comprehensively"
        print(f"  Using default query: '{query}'")

    topic = input("\nLecture topic / title: ").strip()
    if not topic:
        topic = source_path.stem
        print(f"  Using filename as topic: '{topic}'")

    course_code = input("Course code (e.g. CS101) [optional, press Enter to skip]: ").strip()
    if not course_code:
        course_code = "COURSE"

    max_iter_raw = input("Max revision iterations before auto-proceed [default 3]: ").strip()
    max_iterations = int(max_iter_raw) if max_iter_raw.isdigit() else 3

    output_dir = OUTPUT_BASE / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "meta": {
            "session_id":  session_id,
            "teacher_id":  "teacher-terminal",
            "course_code": course_code,
            "title":       topic,
            "output_dir":  str(output_dir),
        },
        "source": {
            "type":          "generated_lecture",
            "prepared_text": None,
            "pdf": [
                {"text": source_text, "query": query},
            ],
            "docx":    None,
            "pptx":    None,
            "audio":   None,
            "video":   None,
            "website": None,
            "images":  None,
        },
        "final_lecture":    None,
        "lecture_paths":    None,
        "lecture_approval": {
            "status":           "pending",
            "teacher_feedback": None,
            "iteration":        0,
            "max_iterations":   max_iterations,
        },
        "generated_content": {
            "script":          None,
            "worksheet":       None,
            "quiz":            None,
            "summary":         None,
            "flowchart":       None,
            "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATH A TEST — prepared_lecture
# ─────────────────────────────────────────────────────────────────────────────

def run_prepared_lecture():
    _divider("TEST A — prepared_lecture (no HITL)")
    print("The lecture text you enter goes directly to content generation.")
    print("No LLM call is made for the lecture itself.")

    sid    = str(uuid.uuid4())[:8]
    state  = _build_prepared_state(sid)
    config = {"configurable": {"thread_id": sid}}

    saver = MemorySaver()
    graph = build_graph(checkpointer=saver)

    _divider("RUNNING GRAPH")
    final = None
    for event in graph.stream(state, config=config, stream_mode="values"):
        step = event.get("current_step", "?")
        print(f"  ✓ {step}")
        final = event

    # Assertions
    assert final is not None,                          "Graph produced no output"
    assert final["current_step"] == "done",            f"Expected done, got {final['current_step']}"
    assert final["lecture_approval"] is None,          "lecture_approval must be None for path A"
    assert final["final_lecture"],                     "final_lecture must be populated"
    assert final["lecture_paths"]["txt"],              "lecture txt path must exist"
    assert Path(final["lecture_paths"]["txt"]).exists(),"lecture txt file must exist on disk"

    _show_results(final)
    print("\nTEST A PASSED ✅")
    return final


# ─────────────────────────────────────────────────────────────────────────────
# PATH B TEST — generated_lecture with terminal HITL
# ─────────────────────────────────────────────────────────────────────────────

def run_generated_lecture():
    _divider("TEST B — generated_lecture (real LLM + terminal HITL)")
    print("The agent will generate a lecture from your source file.")
    print("You will review it in the terminal and approve or reject.")

    sid    = str(uuid.uuid4())[:8]
    state  = _build_generated_state(sid)
    config = {"configurable": {"thread_id": sid}}

    saver = MemorySaver()
    graph = build_graph(checkpointer=saver)

    # ── First run — generates lecture, pauses at interrupt ────────────────────
    _divider("RUNNING GRAPH")
    print("  Generating lecture — this may take 30–90 seconds...")

    paused = None
    for event in graph.stream(state, config=config, stream_mode="values"):
        step = event.get("current_step", "?")
        print(f"  ✓ {step}")
        paused = event

    assert paused is not None, "Graph produced no output on first run"

    # ── HITL loop — runs until approved or cap reached ────────────────────────
    while paused.get("current_step") == "awaiting_approval":
        status, feedback = _teacher_hitl(paused)

        print(f"\n  Resuming with status='{status}'...")
        if feedback:
            print(f"  Feedback: {feedback}")

        paused = None
        for event in graph.stream(
            Command(resume={"status": status, "feedback": feedback}),
            config=config,
            stream_mode="values",
        ):
            step = event.get("current_step", "?")
            print(f"  ✓ {step}")
            paused = event

        assert paused is not None, "Graph produced no output after resume"

    # ── Final assertions ──────────────────────────────────────────────────────
    assert paused["current_step"] == "done", \
        f"Expected done, got {paused['current_step']}"
    assert paused["final_lecture"], \
        "final_lecture must be populated"
    assert paused["lecture_paths"]["txt"], \
        "lecture txt path must exist"
    assert Path(paused["lecture_paths"]["txt"]).exists(), \
        "lecture txt file must exist on disk"
    assert paused["lecture_approval"] is not None, \
        "lecture_approval must be present for path B"

    # Check all generators produced something
    gc = paused.get("generated_content") or {}
    failed = [k for k, v in gc.items() if v is None]
    if failed:
        print(f"\n  ⚠  These generators failed: {failed}")
    else:
        print("\n  ✓  All generators produced output")

    _show_results(paused)
    print("\nTEST B PASSED ✅")
    return paused


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _divider("HOLOLEARN AGENT — REAL FLOW TEST")
    print("Runs the actual generators with real LLM calls.")
    print("Make sure your .env API keys are configured.")
    print(f"Output will be written to: {OUTPUT_BASE}")

    _divider("SELECT TEST")
    print("  a    — PATH A: prepared_lecture (you enter the text, no LLM for lecture)")
    print("  b    — PATH B: generated_lecture (LLM generates, you approve/reject)")
    print("  both — run A then B")

    choice = _ask("\nChoice [a / b / both]: ", ["a", "b", "both"])

    results = {}

    if choice in ("a", "both"):
        try:
            run_prepared_lecture()
            results["TEST A"] = "PASSED ✅"
        except Exception as e:
            results["TEST A"] = f"FAILED ❌ — {e}"
            import traceback
            traceback.print_exc()

    if choice in ("b", "both"):
        try:
            run_generated_lecture()
            results["TEST B"] = "PASSED ✅"
        except Exception as e:
            results["TEST B"] = f"FAILED ❌ — {e}"
            import traceback
            traceback.print_exc()

    _divider("RESULTS")
    for name, result in results.items():
        print(f"  {result}  {name}")
    _divider()