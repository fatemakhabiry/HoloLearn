# Lecture_Agent/test.py  — these 10 lines must be FIRST, before everything else

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent   # HoloLearn/
_AGENT_DIR    = Path(__file__).parent          # HoloLearn/Lecture_Agent/
_GEN_ROOT     = _PROJECT_ROOT / "generators"

# Project root — so 'generators.xxx' imports work
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Agent dir — so 'state', 'graph', 'nodes', 'wrapper' imports work
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

# Every generator sub-package dir — so bare imports like
# 'from Config import ...' and 'from kg_config import ...' work
for _sub in _GEN_ROOT.rglob("*.py"):
    _d = str(_sub.parent)
    if _d not in sys.path:
        sys.path.insert(0, _d)

# ── Now safe to import everything else ───────────────────────────────────────
import uuid
import json
from unittest.mock import MagicMock, patch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from state import AgentState, GeneratedContent, LecturePaths
from graph import build_graph


# ─────────────────────────────────────────────────────────────────────────────
# MOCK SETUP
# Every generator returns a fake paths dict instantly.
# Replace with real wrapper calls once graph logic is confirmed.
# ─────────────────────────────────────────────────────────────────────────────

def _make_mock_wrapper(output_dir: Path, course_code: str):
    """
    Returns a MagicMock that looks exactly like SimpleGeneratorWrapper
    but writes small stub files instead of calling any LLM.
    """
    m = MagicMock()

    # Lecture generator — writes a real .txt so KG and final_lecture work
    def _mock_generate_lecture(lecture_topic, output_dir, course_code, sources, **kw):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        txt = out / f"{course_code}_lecture.txt"
        pdf = out / f"{course_code}_lecture.pdf"
        js  = out / f"{course_code}_lecture.json"
        txt.write_text(f"[MOCK LECTURE] Topic: {lecture_topic}", encoding="utf-8")
        pdf.write_bytes(b"%PDF mock")
        js.write_text(json.dumps({"title": lecture_topic}), encoding="utf-8")
        return {"pdf": str(pdf), "txt": str(txt), "json": str(js)}

    def _mock_generate_script(content, output_dir, course_code, title, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        p = out / f"{course_code}_script.txt"
        p.write_text("[MOCK SCRIPT]", encoding="utf-8")
        return {"txt": str(p)}

    def _mock_generate_summary(content, output_dir, course_code, title, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        p = out / f"{course_code}_summary.pdf"
        p.write_bytes(b"%PDF mock summary")
        return {"pdf": str(p), "txt": None}

    def _mock_generate_worksheet(content, output_dir, course_code, title, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        q = out / f"{course_code}_worksheet.pdf"
        a = out / f"{course_code}_worksheet_answers.pdf"
        q.write_bytes(b"%PDF mock ws"); a.write_bytes(b"%PDF mock ws ans")
        return {"questions_pdf": str(q), "answers_pdf": str(a), "json": None}

    def _mock_generate_quiz(content, output_dir, course_code, title, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        q = out / f"{course_code}_quiz.pdf"
        a = out / f"{course_code}_quiz_answers.pdf"
        q.write_bytes(b"%PDF mock quiz"); a.write_bytes(b"%PDF mock quiz ans")
        return {"quiz_pdf": str(q), "answers_pdf": str(a)}

    def _mock_generate_flowchart(content, output_dir, course_code, title, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        p = out / f"{course_code}_flowchart.html"
        p.write_text("<html>mock flowchart</html>", encoding="utf-8")
        return {"html": str(p), "mmd": None}

    def _mock_generate_knowledge_graph(txt_path, output_dir, course_code, **kw):
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        p = out / f"{course_code}_kg.html"
        p.write_text("<html>mock KG</html>", encoding="utf-8")
        return {"html": str(p)}

    m.generate_lecture.side_effect          = _mock_generate_lecture
    m.generate_script.side_effect           = _mock_generate_script
    m.generate_summary.side_effect          = _mock_generate_summary
    m.generate_worksheet.side_effect        = _mock_generate_worksheet
    m.generate_quiz.side_effect             = _mock_generate_quiz
    m.generate_flowchart.side_effect        = _mock_generate_flowchart
    m.generate_knowledge_graph.side_effect  = _mock_generate_knowledge_graph

    return m


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

BASE_OUTPUT = Path("test_output")

def _session_id() -> str:
    return str(uuid.uuid4())[:8]


def _make_prepared_state(session_id: str) -> AgentState:
    """Initial state for PATH A (prepared_lecture)."""
    return {
        "meta": {
            "session_id":  session_id,
            "teacher_id":  "teacher-001",
            "course_code": "CS101",
            "title":       "Introduction to Python",
            "output_dir":  str(BASE_OUTPUT / session_id),
        },
        "source": {
            "type":          "prepared_lecture",
            "prepared_text": "Python is a high-level programming language. " * 20,
            "pdf":     None, "docx": None, "pptx": None,
            "audio":   None, "video": None, "website": None,
            "images":  None,
        },
        "final_lecture":    None,
        "lecture_paths":    None,
        "lecture_approval": None,
        "generated_content": {
            "script": None, "worksheet": None, "quiz": None,
            "summary": None, "flowchart": None, "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }


def _make_generated_state(session_id: str, max_iterations: int = 3) -> AgentState:
    """Initial state for PATH B (generated_lecture)."""
    return {
        "meta": {
            "session_id":  session_id,
            "teacher_id":  "teacher-001",
            "course_code": "ML202",
            "title":       "Logistic Regression",
            "output_dir":  str(BASE_OUTPUT / session_id),
        },
        "source": {
            "type":          "generated_lecture",
            "prepared_text": None,
            "pdf": [
                {"text": "Logistic regression theory text...", "query": "explain logistic regression"},
            ],
            "docx": None, "pptx": None, "audio": None,
            "video": None, "website": None, "images": None,
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
            "script": None, "worksheet": None, "quiz": None,
            "summary": None, "flowchart": None, "knowledge_graph": None,
        },
        "current_step": "starting",
        "error":        None,
    }


def _assert_content_generated(state: dict, test_name: str):
    """Check that all 6 generators produced output."""
    content = state.get("generated_content", {})
    failures = []
    for key in ["script", "summary", "worksheet", "quiz", "flowchart", "knowledge_graph"]:
        if content.get(key) is None:
            failures.append(key)
    if failures:
        print(f"  ⚠  {test_name}: missing content for: {failures}")
    else:
        print(f"  ✓  {test_name}: all 6 generators produced output")


def _print_state_summary(state: dict):
    print(f"     current_step     : {state.get('current_step')}")
    print(f"     final_lecture    : {len(state.get('final_lecture') or '')} chars")
    lp = state.get("lecture_paths") or {}
    print(f"     lecture_paths.txt: {lp.get('txt')}")
    ap = state.get("lecture_approval") or {}
    print(f"     approval.status  : {ap.get('status')} | iteration={ap.get('iteration')}")
    gc = state.get("generated_content") or {}
    done = [k for k, v in gc.items() if v is not None]
    print(f"     generated        : {done}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — prepared_lecture (no HITL)
# ─────────────────────────────────────────────────────────────────────────────

def test_prepared_lecture():
    print("\n" + "="*60)
    print("TEST 1 — prepared_lecture (no HITL, straight to content)")
    print("="*60)

    sid    = _session_id()
    state  = _make_prepared_state(sid)
    mock   = _make_mock_wrapper(BASE_OUTPUT / sid, "CS101")
    config = {"configurable": {"thread_id": sid}}

    with patch("nodes._wrapper", mock):
        saver = MemorySaver()
        graph = build_graph(checkpointer=saver)

        final = None
        for event in graph.stream(state, config=config, stream_mode="values"):
            final = event

    assert final is not None, "Graph produced no output"
    assert final["current_step"] == "done", \
        f"Expected 'done', got '{final['current_step']}'"
    assert final["lecture_approval"] is None, \
        "lecture_approval should be None for prepared_lecture path"
    assert final["final_lecture"], "final_lecture should be populated"

    _assert_content_generated(final, "TEST 1")
    _print_state_summary(final)
    print("TEST 1 PASSED ✅")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — generated_lecture, approve on first review
# ─────────────────────────────────────────────────────────────────────────────

def test_generated_approve():
    print("\n" + "="*60)
    print("TEST 2 — generated_lecture, approve immediately")
    print("="*60)

    sid    = _session_id()
    state  = _make_generated_state(sid)
    mock   = _make_mock_wrapper(BASE_OUTPUT / sid, "ML202")
    config = {"configurable": {"thread_id": sid}}

    with patch("nodes._wrapper", mock):
        saver = MemorySaver()
        graph = build_graph(checkpointer=saver)

        # ── Run until interrupt ───────────────────────────────
        print("  → Running graph until HITL interrupt...")
        paused = None
        for event in graph.stream(state, config=config, stream_mode="values"):
            paused = event

        assert paused is not None
        assert paused["current_step"] == "awaiting_approval", \
            f"Expected 'awaiting_approval', got '{paused['current_step']}'"
        assert paused["final_lecture"], "final_lecture must be set before interrupt"
        print(f"  ✓  Paused at interrupt (iteration={paused['lecture_approval']['iteration']})")

        # ── Teacher approves ──────────────────────────────────
        print("  → Teacher approves...")
        final = None
        for event in graph.stream(
            Command(resume={"status": "approved", "feedback": ""}),
            config=config,
            stream_mode="values",
        ):
            final = event

    assert final is not None
    assert final["current_step"] == "done", \
        f"Expected 'done', got '{final['current_step']}'"
    assert final["lecture_approval"]["status"] == "approved"

    _assert_content_generated(final, "TEST 2")
    _print_state_summary(final)
    print("TEST 2 PASSED ✅")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — generated_lecture, reject once then approve
# ─────────────────────────────────────────────────────────────────────────────

def test_generated_reject_then_approve():
    print("\n" + "="*60)
    print("TEST 3 — generated_lecture, reject once then approve")
    print("="*60)

    sid    = _session_id()
    state  = _make_generated_state(sid, max_iterations=3)
    mock   = _make_mock_wrapper(BASE_OUTPUT / sid, "ML202")
    config = {"configurable": {"thread_id": sid}}

    with patch("nodes._wrapper", mock):
        saver = MemorySaver()
        graph = build_graph(checkpointer=saver)

        # ── First run → interrupt ─────────────────────────────
        print("  → Running to first interrupt...")
        for event in graph.stream(state, config=config, stream_mode="values"):
            paused = event

        assert paused["current_step"] == "awaiting_approval"
        iter_before = paused["lecture_approval"]["iteration"]
        print(f"  ✓  First interrupt (iteration={iter_before})")

        # ── Teacher rejects ───────────────────────────────────
        print("  → Teacher rejects with feedback...")
        for event in graph.stream(
            Command(resume={"status": "rejected", "feedback": "Please add more examples"}),
            config=config,
            stream_mode="values",
        ):
            paused = event

        assert paused["current_step"] == "awaiting_approval", \
            f"Expected 'awaiting_approval' after regen, got '{paused['current_step']}'"
        iter_after = paused["lecture_approval"]["iteration"]
        assert iter_after > iter_before, \
            f"Iteration should have incremented: {iter_before} → {iter_after}"
        print(f"  ✓  Second interrupt after regen (iteration={iter_after})")

        # ── Teacher approves on second review ─────────────────
        print("  → Teacher approves on second review...")
        final = None
        for event in graph.stream(
            Command(resume={"status": "approved", "feedback": ""}),
            config=config,
            stream_mode="values",
        ):
            final = event

    assert final["current_step"] == "done"
    assert final["lecture_approval"]["status"] == "approved"
    assert mock.generate_lecture.call_count == 2, \
        f"generate_lecture should be called twice, got {mock.generate_lecture.call_count}"

    _assert_content_generated(final, "TEST 3")
    _print_state_summary(final)
    print("TEST 3 PASSED ✅")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — generated_lecture, reject until max_iterations cap
# ─────────────────────────────────────────────────────────────────────────────

def test_generated_max_iterations():
    print("\n" + "="*60)
    print("TEST 4 — generated_lecture, reject until cap (max_iterations=2)")
    print("="*60)

    sid    = _session_id()
    # Set max_iterations=2 so the cap is hit quickly
    state  = _make_generated_state(sid, max_iterations=2)
    mock   = _make_mock_wrapper(BASE_OUTPUT / sid, "ML202")
    config = {"configurable": {"thread_id": sid}}

    with patch("nodes._wrapper", mock):
        saver = MemorySaver()
        graph = build_graph(checkpointer=saver)

        paused = None

        # ── Run and reject max_iterations times ───────────────
        for event in graph.stream(state, config=config, stream_mode="values"):
            paused = event

        reject_count = 0
        while paused["current_step"] == "awaiting_approval":
            iteration = paused["lecture_approval"]["iteration"]
            max_iter  = paused["lecture_approval"]["max_iterations"]
            print(f"  → Rejecting (iteration={iteration}, max={max_iter})...")

            paused = None
            for event in graph.stream(
                Command(resume={"status": "rejected", "feedback": f"Rejection #{reject_count+1}"}),
                config=config,
                stream_mode="values",
            ):
                paused = event

            reject_count += 1

            # Safety valve — should never need more than max_iterations+1 loops
            if reject_count > 5:
                raise AssertionError("Rejection loop did not terminate — check _approval_edge")

        # After cap is hit the graph should proceed to done
        assert paused is not None
        assert paused["current_step"] == "done", \
            f"Expected 'done' after cap, got '{paused['current_step']}'"
        print(f"  ✓  Cap enforced after {reject_count} rejection(s)")
        print(f"  ✓  generate_lecture called {mock.generate_lecture.call_count} time(s)")

        _assert_content_generated(paused, "TEST 4")
        _print_state_summary(paused)
    print("TEST 4 PASSED ✅")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    BASE_OUTPUT.mkdir(exist_ok=True)

    results = {}

    for name, fn in [
        ("TEST 1 prepared_lecture",          test_prepared_lecture),
        ("TEST 2 generated_approve",         test_generated_approve),
        ("TEST 3 generated_reject_approve",  test_generated_reject_then_approve),
        ("TEST 4 generated_max_iterations",  test_generated_max_iterations),
    ]:
        try:
            fn()
            results[name] = "PASSED ✅"
        except Exception as e:
            results[name] = f"FAILED ❌ — {e}"
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    for name, result in results.items():
        print(f"  {result}  {name}")
    print("="*60)