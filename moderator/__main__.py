"""
CLI entry point for HoloLearn.

Usage:
    python -m moderator file1.pdf file2.docx https://example.com \
        --course CS101 --title "AI Basics" --generators quiz summary
"""

import argparse
import os
import sys

# Ensure project root is on sys.path
sys.path.append(str(__import__("pathlib").Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(
        prog="python -m moderator",
        description="HoloLearn: Extract content from files/URLs and generate educational materials.",
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="File paths and/or URLs to process",
    )
    parser.add_argument(
        "--course",
        default="",
        help="Course code (e.g. CS101)",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Title or topic for generated materials",
    )
    parser.add_argument(
        "--generators",
        nargs="*",
        default=None,
        choices=["lecture", "quiz", "summary", "worksheet", "flowchart", "script", "all"],
        help="Generators to run (default: all). Pass none to skip generation.",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only extract content, skip generation stage",
    )
    parser.add_argument(
        "--groq-api-key",
        default=None,
        help="Groq API key (overrides environment variable)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Thread pool size for parallel extraction",
    )

    args = parser.parse_args()

    # Set API key early if provided via CLI (before any module imports it)
    if args.groq_api_key:
        os.environ["GROQ_API_KEY"] = args.groq_api_key

    from moderator.pipeline import Pipeline

    # Determine generator list
    if args.extract_only:
        gen_list = []
    elif args.generators is not None:
        gen_list = args.generators
    else:
        gen_list = None  # Pipeline default: all

    pipeline = Pipeline(max_workers=args.max_workers)
    result = pipeline.run(
        inputs=args.inputs,
        course_code=args.course,
        title=args.title,
        generators=gen_list,
        groq_api_key=args.groq_api_key,
    )

    _print_result(result)
    sys.exit(0 if result["extraction_summary"]["successful"] > 0 else 1)


def _print_result(result):
    """Pretty-print pipeline results to the console."""
    print()
    print("=" * 60)
    print("  HoloLearn Pipeline Results")
    print("=" * 60)

    ext = result["extraction_summary"]
    print(f"\n  Inputs:      {ext['total']}")
    print(f"  Successful:  {ext['successful']}")
    print(f"  Failed:      {ext['failed']}")
    print(f"  Extract time: {ext['processing_time_seconds']}s")

    if result["session_dir"]:
        print(f"  Session dir: {result['session_dir']}")

    # Extraction details
    for r in ext.get("results", []):
        status = "OK" if r["success"] else "FAIL"
        print(f"\n  [{status}] ({r['type']}) {r['input']}")
        if r["success"]:
            print(f"         -> {r['text_file']}")
        else:
            print(f"         !! {r['error']}")

    # Combined text
    if result.get("combined_text_file"):
        print(f"\n  Combined text: {result['combined_text_file']}")

    # Generation results
    gen = result.get("generation_results", {})
    if gen:
        print(f"\n  --- Generation ---")
        for name, res in gen.items():
            status = "OK" if res["success"] else "FAIL"
            print(f"  [{status}] {name}")
            if res["success"]:
                for f in res["output_files"]:
                    print(f"         -> {f}")
            else:
                print(f"         !! {res['error']}")

    # Errors
    if result.get("errors"):
        print(f"\n  --- Errors ---")
        for err in result["errors"]:
            print(f"  !! {err}")

    print(f"\n  Total time: {result['total_processing_time_seconds']}s")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
