"""
Moderator for HoloLearn
Orchestrates input classification and parallel extraction across all extractor types.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from classifier import classify_inputs
from utils.configs import MAX_PARALLEL_EXTRACTIONS, GROQ_API_KEY, OUTPUT_DIR, LOGS_DIR

# Lazy extractor imports to avoid loading heavy dependencies until needed
_EXTRACTOR_CACHE: Dict[str, Any] = {}


def _get_extractor(input_type: str):
    """
    Lazily instantiate and cache an extractor by type.
    Returns the extractor instance or None if the type is unknown.
    """
    if input_type in _EXTRACTOR_CACHE:
        return _EXTRACTOR_CACHE[input_type]

    extractor = None

    if input_type == "pdf":
        from extractors.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()

    elif input_type == "docx":
        from extractors.docx_extractor import DOCXExtractor
        extractor = DOCXExtractor()

    elif input_type == "pptx":
        from extractors.pptx_extractor import PPTXExtractor
        extractor = PPTXExtractor()

    elif input_type == "video":
        from extractors.video_extractor import VideoExtractor
        extractor = VideoExtractor(api_key=GROQ_API_KEY)

    elif input_type == "audio":
        from extractors.audio_extractor import AudioExtractor
        extractor = AudioExtractor(api_key=GROQ_API_KEY)

    elif input_type == "url":
        from extractors.url_extractor import URLExtractor
        extractor = URLExtractor()

    if extractor is not None:
        _EXTRACTOR_CACHE[input_type] = extractor

    return extractor


def _run_extraction(classification: Dict[str, Any],
                    output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a single extraction based on the classification result.
    This function is designed to be called inside a thread pool.

    Args:
        classification: Classification dict from classify_inputs().
        output_dir: Optional shared session output directory. When provided,
            all extractors write their files here instead of per-resource subfolders.

    Returns:
        A result dict with keys: input, type, success, output_dir,
        text_file, metadata_file, error.
    """
    input_path = classification["input"]
    input_type = classification["type"]

    # Build a base result
    result = {
        "input": input_path,
        "type": input_type,
        "success": False,
        "output_dir": None,
        "text_file": None,
        "metadata_file": None,
        "error": None,
    }

    # Skip invalid inputs early
    if not classification["valid"]:
        result["error"] = classification["reason"]
        return result

    try:
        extractor = _get_extractor(input_type)
        if extractor is None:
            result["error"] = f"No extractor available for type: {input_type}"
            return result

        # All extractors expose .extract(<path_or_url>) as their first arg
        if input_type == "url":
            ext_result = extractor.extract(url=input_path, output_dir=output_dir)
        elif input_type == "pdf":
            ext_result = extractor.extract(pdf_path=input_path, output_dir=output_dir)
        elif input_type == "docx":
            ext_result = extractor.extract(docx_path=input_path, output_dir=output_dir)
        elif input_type == "pptx":
            ext_result = extractor.extract(pptx_path=input_path, output_dir=output_dir)
        elif input_type == "video":
            ext_result = extractor.extract(video_path=input_path, output_dir=output_dir)
        elif input_type == "audio":
            ext_result = extractor.extract(audio_path=input_path, output_dir=output_dir)
        else:
            result["error"] = f"Unknown type: {input_type}"
            return result

        result["success"] = ext_result.get("success", False)
        result["output_dir"] = ext_result.get("output_dir")
        result["text_file"] = ext_result.get("text_file")
        result["metadata_file"] = ext_result.get("metadata_file")

        if not result["success"]:
            result["error"] = ext_result.get("error", "Extraction failed")

    except Exception as e:
        result["error"] = str(e)

    return result


class Moderator:
    """
    Central orchestrator that accepts mixed inputs (files + URLs),
    classifies them, dispatches to the correct extractor in parallel,
    and returns a unified summary with output paths.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Args:
            max_workers: Thread pool size. Defaults to MAX_PARALLEL_EXTRACTIONS from config.
        """
        self.max_workers = max_workers or MAX_PARALLEL_EXTRACTIONS

    def process(self, inputs: List[str]) -> Dict[str, Any]:
        """
        Process a list of inputs (file paths and/or URLs).

        Args:
            inputs: List of file path strings and/or URL strings.

        Returns:
            {
                "total": int,
                "successful": int,
                "failed": int,
                "processing_time_seconds": float,
                "session_dir": str,             # shared output folder for this session
                "results": [
                    {
                        "input": str,
                        "type": str,
                        "success": bool,
                        "output_dir": str | None,
                        "text_file": str | None,
                        "metadata_file": str | None,
                        "error": str | None
                    },
                    ...
                ],
                "output_paths": [str, ...]   # text_file paths from successful extractions
            }
        """
        start_time = time.time()

        # 1. Create session directories (timestamp-based, shared across all inputs)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_output_dir = OUTPUT_DIR / f"session_{timestamp}"
        session_logs_dir = LOGS_DIR / f"session_{timestamp}"
        session_output_dir.mkdir(parents=True, exist_ok=True)
        session_logs_dir.mkdir(parents=True, exist_ok=True)

        # 2. Classify all inputs
        classifications = classify_inputs(inputs)

        # 3. Run extractions in parallel, passing the shared session dir
        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_cls = {
                executor.submit(_run_extraction, cls, str(session_output_dir)): cls
                for cls in classifications
            }

            for future in as_completed(future_to_cls):
                try:
                    results.append(future.result())
                except Exception as e:
                    cls = future_to_cls[future]
                    results.append({
                        "input": cls["input"],
                        "type": cls["type"],
                        "success": False,
                        "output_dir": None,
                        "text_file": None,
                        "metadata_file": None,
                        "error": str(e),
                    })

        # 4. Preserve original input order
        input_order = {cls["input"]: i for i, cls in enumerate(classifications)}
        results.sort(key=lambda r: input_order.get(r["input"], 0))

        # 5. Build summary
        successful = sum(1 for r in results if r["success"])
        output_paths = [r["text_file"] for r in results if r["success"] and r["text_file"]]

        return {
            "total": len(inputs),
            "successful": successful,
            "failed": len(inputs) - successful,
            "processing_time_seconds": round(time.time() - start_time, 2),
            "session_dir": str(session_output_dir),
            "results": results,
            "output_paths": output_paths,
        }


# ── Example / Testing ──
if __name__ == "__main__":
    import sys as _sys

    print("=== HoloLearn Moderator ===\n")

    # Accept inputs from command line args, or use a demo list
    if len(_sys.argv) > 1:
        test_inputs = _sys.argv[1:]
    else:
        print("Usage: python -m moderator.moderator <file1> <file2> <url1> ...")
        print("No inputs provided. Running with empty list.\n")
        test_inputs = []

    if test_inputs:
        moderator = Moderator()
        summary = moderator.process(test_inputs)

        print(f"Total:      {summary['total']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed:     {summary['failed']}")
        print(f"Time:       {summary['processing_time_seconds']}s")
        print(f"Session:    {summary['session_dir']}\n")

        for r in summary["results"]:
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{status}] ({r['type']}) {r['input']}")
            if r["success"]:
                print(f"         -> {r['text_file']}")
            else:
                print(f"         !! {r['error']}")

        if summary["output_paths"]:
            print(f"\nOutput paths for downstream module:")
            for p in summary["output_paths"]:
                print(f"  {p}")
    else:
        print("Nothing to process.")
