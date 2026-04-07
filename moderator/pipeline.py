"""
HoloLearn Pipeline
End-to-end orchestrator: extraction -> text combination -> generation.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from moderator.moderator import Moderator
from classifier import classify_inputs
from generators import AVAILABLE_GENERATORS


class Pipeline:
    """
    Full pipeline that extracts content from inputs and generates
    educational materials in a single call.

    Usage::

        from moderator import Pipeline

        pipeline = Pipeline()
        result = pipeline.run(
            inputs=["lecture.pdf", "https://example.com/notes"],
            course_code="CS101",
            title="Machine Learning Intro",
            generators=["quiz", "summary"],
        )
        print(result["session_dir"])
    """

    def __init__(self, max_workers: Optional[int] = None):
        self.moderator = Moderator(max_workers=max_workers)

    def run(
        self,
        inputs: List[str],
        course_code: str = "",
        title: str = "",
        generators: Optional[List[str]] = None,
        groq_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the full extract-then-generate pipeline.

        Args:
            inputs: File paths and/or URLs to process.
            course_code: Course code passed to generators (e.g. "CS101").
            title: Title/topic passed to generators.
            generators: Which generators to run after extraction.
                None or ["all"] runs all available generators.
                Pass an empty list to skip generation entirely.
            groq_api_key: Groq API key override. Falls back to env.

        Returns:
            {
                "session_dir": str | None,
                "extraction_summary": { ... },
                "combined_text": str,
                "combined_text_file": str | None,
                "generation_results": { "<name>": {"success": bool, "output_files": [...], "error": str|None} },
                "all_output_files": [str, ...],
                "total_processing_time_seconds": float,
                "errors": [str, ...],
            }
        """
        start_time = time.time()
        errors: List[str] = []

        # -- Resolve API key --
        api_key = groq_api_key or os.getenv("GROQ_API_KEY")

        # -- Resolve generator list --
        gen_list = self._resolve_generators(generators)

        # -- Classify inputs for upfront validation --
        classifications = classify_inputs(inputs)

        # -- Validate API key if needed --
        api_ok, api_err = self._validate_api_key(classifications, gen_list, api_key)
        if not api_ok:
            errors.append(api_err)
            return self._empty_result(inputs, errors, start_time)

        # -- Check at least one valid input --
        valid_count = sum(1 for c in classifications if c["valid"])
        if valid_count == 0:
            for c in classifications:
                if not c["valid"]:
                    errors.append(f"{c['input']}: {c['reason']}")
            return self._empty_result(inputs, errors, start_time)

        # -- Run extraction --
        extraction = self.moderator.process(inputs)
        session_dir = extraction["session_dir"]

        extraction_summary = {
            "total": extraction["total"],
            "successful": extraction["successful"],
            "failed": extraction["failed"],
            "processing_time_seconds": extraction["processing_time_seconds"],
            "results": extraction["results"],
        }

        # Collect extraction errors
        for r in extraction["results"]:
            if not r["success"] and r["error"]:
                errors.append(f"Extraction failed for {r['input']}: {r['error']}")

        # -- Combine extracted text --
        combined_text = self._combine_extracted_text(extraction)
        combined_text_file = None

        if combined_text.strip() and session_dir:
            combined_path = Path(session_dir) / "combined_text.txt"
            combined_path.write_text(combined_text, encoding="utf-8")
            combined_text_file = str(combined_path)

        # -- Run generators --
        generation_results: Dict[str, Any] = {}
        all_output_files: List[str] = []

        if gen_list and combined_text.strip():
            generation_results = self._run_generators(
                combined_text=combined_text,
                session_dir=session_dir,
                course_code=course_code,
                title=title,
                generators=gen_list,
                api_key=api_key,
            )
            for name, res in generation_results.items():
                if res["success"]:
                    all_output_files.extend(res["output_files"])
                else:
                    errors.append(f"Generator '{name}' failed: {res['error']}")
        elif gen_list and not combined_text.strip():
            errors.append("No text extracted — skipping generation stage.")

        # Add extraction output files
        for r in extraction["results"]:
            if r["success"] and r["text_file"]:
                all_output_files.append(r["text_file"])
            if r["success"] and r.get("metadata_file"):
                all_output_files.append(r["metadata_file"])
        if combined_text_file:
            all_output_files.append(combined_text_file)

        return {
            "session_dir": session_dir,
            "extraction_summary": extraction_summary,
            "combined_text": combined_text,
            "combined_text_file": combined_text_file,
            "generation_results": generation_results,
            "all_output_files": all_output_files,
            "total_processing_time_seconds": round(time.time() - start_time, 2),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_generators(generators: Optional[List[str]]) -> List[str]:
        """Expand None / ["all"] into the full generator list."""
        if generators is None:
            return list(AVAILABLE_GENERATORS)
        if "all" in generators:
            return list(AVAILABLE_GENERATORS)
        return [g for g in generators if g in AVAILABLE_GENERATORS]

    @staticmethod
    def _validate_api_key(
        classifications: List[Dict],
        generators: List[str],
        api_key: Optional[str],
    ) -> tuple:
        """Return (ok, error_message). Checks if API key is needed and present."""
        needs_key = False
        reasons = []

        if generators:
            needs_key = True
            reasons.append("generators require Groq API key")

        for cls in classifications:
            if cls["valid"] and cls["type"] in ("audio", "video"):
                needs_key = True
                reasons.append(f"{cls['type']} extraction requires Groq API key")

        if needs_key and (not api_key or api_key == "your-groq-api-key-here"):
            return False, (
                "GROQ_API_KEY is required but not set. "
                f"Reasons: {'; '.join(reasons)}. "
                "Set via environment variable, .env file, or --groq-api-key flag."
            )
        return True, ""

    @staticmethod
    def _combine_extracted_text(extraction: Dict[str, Any]) -> str:
        """Read all extracted text files and merge with source annotations."""
        parts = []
        for result in extraction["results"]:
            if result["success"] and result["text_file"]:
                text_path = Path(result["text_file"])
                if text_path.exists():
                    text = text_path.read_text(encoding="utf-8")
                    parts.append(
                        f"\n{'=' * 60}\n"
                        f"SOURCE: {result['input']} ({result['type']})\n"
                        f"{'=' * 60}\n"
                        f"{text}"
                    )
        return "\n".join(parts)

    @staticmethod
    def _empty_result(inputs, errors, start_time):
        return {
            "session_dir": None,
            "extraction_summary": {
                "total": len(inputs),
                "successful": 0,
                "failed": len(inputs),
                "processing_time_seconds": 0,
                "results": [],
            },
            "combined_text": "",
            "combined_text_file": None,
            "generation_results": {},
            "all_output_files": [],
            "total_processing_time_seconds": round(time.time() - start_time, 2),
            "errors": errors,
        }

    def _run_generators(
        self,
        combined_text: str,
        session_dir: str,
        course_code: str,
        title: str,
        generators: List[str],
        api_key: str,
    ) -> Dict[str, Any]:
        """Run each requested generator sequentially."""
        results: Dict[str, Any] = {}
        session_path = Path(session_dir)

        dispatch = {
            "lecture": self._run_lecture,
            "quiz": self._run_quiz,
            "summary": self._run_summary,
            "worksheet": self._run_worksheet,
            "flowchart": self._run_flowchart,
            "script": self._run_script,
        }

        for name in generators:
            runner = dispatch.get(name)
            if runner is None:
                results[name] = {
                    "success": False,
                    "output_files": [],
                    "error": f"Unknown generator: {name}",
                }
                continue
            try:
                results[name] = runner(
                    combined_text, session_path, course_code, title, api_key
                )
            except Exception as e:
                results[name] = {
                    "success": False,
                    "output_files": [],
                    "error": str(e),
                }

        return results

    # ------------------------------------------------------------------
    # Per-generator runners
    # ------------------------------------------------------------------

    @staticmethod
    def _run_lecture(content, session_dir, course_code, title, api_key):
        from generators.generate_lecture import generate_lecture_sync

        pdf_path = str(session_dir / "lecture.pdf")
        # The lecture generator accepts per-source text/query pairs.
        # We pass the combined text as pdf_text with a generic query.
        generate_lecture_sync(
            lecture_topic=title or "Lecture",
            output_pdf_path=pdf_path,
            groq_api_key=api_key,
            pdf_text=content,
            pdf_query=f"Extract all educational content related to {title or 'this lecture'}",
        )
        output_files = [pdf_path]
        txt_path = pdf_path.rsplit(".", 1)[0] + ".txt"
        if Path(txt_path).exists():
            output_files.append(txt_path)
        return {"success": True, "output_files": output_files, "error": None}

    @staticmethod
    def _run_quiz(content, session_dir, course_code, title, api_key):
        from generators.quiz_generator import QuizGenerator

        gen = QuizGenerator(api_key=api_key)
        quiz_path = str(session_dir / "quiz.pdf")
        answers_path = str(session_dir / "quiz_answers.pdf")
        gen.generate_pdfs(
            content=content,
            quiz_path=quiz_path,
            answers_path=answers_path,
            course_code=course_code,
            title=title,
        )
        return {
            "success": True,
            "output_files": [quiz_path, answers_path],
            "error": None,
        }

    @staticmethod
    def _run_summary(content, session_dir, course_code, title, api_key):
        from generators.summary_generator import SummaryGenerator

        gen = SummaryGenerator(api_key=api_key)
        output_path = str(session_dir / "summary.pdf")
        gen.generate_pdf(
            content=content,
            output_path=output_path,
            course_code=course_code,
            title=title,
        )
        return {"success": True, "output_files": [output_path], "error": None}

    @staticmethod
    def _run_worksheet(content, session_dir, course_code, title, api_key):
        from generators.worksheet_generator import WorksheetGenerator

        gen = WorksheetGenerator(api_key=api_key)
        questions_path = str(session_dir / "worksheet.pdf")
        answers_path = str(session_dir / "worksheet_answers.pdf")
        gen.generate_pdfs(
            content=content,
            questions_path=questions_path,
            answers_path=answers_path,
            course_code=course_code,
            title=title,
        )
        return {
            "success": True,
            "output_files": [questions_path, answers_path],
            "error": None,
        }

    @staticmethod
    def _run_flowchart(content, session_dir, course_code, title, api_key):
        from generators.Flow_Chart_generator import FlowchartGenerator

        gen = FlowchartGenerator(api_key=api_key)
        html_path = str(session_dir / "flowchart.html")
        gen.generate_html(
            content=content,
            output_path=html_path,
            course_code=course_code,
            title=title,
        )
        output_files = [html_path]
        mmd_path = html_path.replace(".html", ".mmd")
        if Path(mmd_path).exists():
            output_files.append(mmd_path)
        return {"success": True, "output_files": output_files, "error": None}

    @staticmethod
    def _run_script(content, session_dir, course_code, title, api_key):
        from generators.script_generator import HologramScriptGenerator

        gen = HologramScriptGenerator(api_key=api_key)
        output_path = str(session_dir / "script.txt")
        gen.generate_and_save(
            content=content,
            output_path=output_path,
            course_code=course_code,
            title=title,
        )
        return {"success": True, "output_files": [output_path], "error": None}
