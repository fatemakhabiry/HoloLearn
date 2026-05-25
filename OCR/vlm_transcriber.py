"""
run_vlm.py
==========
One VLM call per crop.

High confidence  → tight label-specific prompt, plain output
Low confidence   → open prompt, VLM prefixes "LABEL:<type>\n" for relabelling
Failure signal   → fallback retry with open prompt

Backend
-------
  Ollama   base_url = "http://localhost:11434/v1"  api_key = "ollama"
  OpenAI   base_url = None                         api_key = "sk-..."

Usage
-----
  python run_vlm.py --csv regions.csv --model minicpm-v:8b-2.6-q4_K_M
"""

import os, sys, csv, base64, argparse, time, tempfile,re
from PIL import Image
import tempfile

# ─────────────────────────────────────────────────────────────────────────────
# Image safety — pad crops that are too small for qwen3-vl (min 32px each dim)
# ─────────────────────────────────────────────────────────────────────────────

_MIN_VLM_DIM = 40  # slightly above the 32px hard limit to add margin

def _safe_image_path(image_path: str) -> tuple:
    """
    Return (path_to_use, is_temp).
    If either dimension < _MIN_VLM_DIM, creates a padded copy in a temp file.
    Caller must delete the temp file when is_temp=True.
    """
    try:
        img = Image.open(image_path)
        w, h = img.size
        if w >= _MIN_VLM_DIM and h >= _MIN_VLM_DIM:
            return image_path, False  # original is fine

        new_w = max(w, _MIN_VLM_DIM)
        new_h = max(h, _MIN_VLM_DIM)
        padded = Image.new("RGB", (new_w, new_h), (255, 255, 255))
        padded.paste(img.convert("RGB"), (0, 0))

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        padded.save(tmp.name)
        tmp.close()
        return tmp.name, True
    except Exception:
        return image_path, False  # if anything fails, use original


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

FALLBACK_PROMPT = (
    "Look at this image. Identify the content type and transcribe it.\n"
    "Line 1: LABEL:<type>  where <type> is one of: text | equation | table | code | diagram \n"
    "Line 2+: transcription in the correct format:\n"
    "  text     → plain text\n"
    "  equation → LaTeX using $...$ or $$...$$\n"
    "  table    → Markdown table\n"
    "  code     → Markdown fenced block\n"
    "  diagram  → plain-English description\n"
    "if it contains mixed items (e.g. text + eqn, digram +eqn), label with the dominant type. and transcript each with its format"
    "if the image is blank or unreadable, respond with LABEL:text and an empty transcription."
    "Output only LABEL line + content. No commentary. "
)

# Tight prompts — plain output, no label needed (CNN already classified)
LABEL_PROMPTS = {
    "text": (
        "You are a precise OCR engine. "
        "Transcribe every word in this image exactly as written. "
        "Output plain text only — no markdown, no commentary, no extra formatting. "
        "Preserve line breaks where they are meaningful. "
        "If the image does not contain text"
        f"ignore the text instruction and instead {FALLBACK_PROMPT}"
    ),
    "equation": (
        "You are a LaTeX transcription expert. "
        "Transcribe the mathematical content in this image as valid LaTeX. "
        "Use $...$ for inline expressions and $$...$$ for display equations. "
        "Output LaTeX and surrounding text — no explanation "
        "If the image does not contain any mathematical content"
        f"ignore the eqution instruction and instead {FALLBACK_PROMPT}"
    ),
    "table": (
        "You are a precise table transcription engine. "
        "Transcribe the table in this image as a Markdown table. "
        "Output the Markdown table only — no commentary. "
        "If the image does not contain a table"
        f"ignore the table instruction and instead {FALLBACK_PROMPT}"
    ),
    "code": (
        "You are a precise code transcription engine. "
        "Transcribe the code in this image into a Markdown fenced code block. "
        "Detect the programming language and use it in the fence (e.g. ```python). "
        "If it does NOT contain a code (i.e. it is plain text, an equation, a table, or diagram), "
        f"ignore the code instruction and instead {FALLBACK_PROMPT}"
    ),
    "diagram": (
        f"{FALLBACK_PROMPT}"
        # "You are a professional content describer. "
        # "First, determine what this image actually contains. "
        # "If it is primarily text, respond with just the text content. "
        # "If it is an equation or mathematical expression, respond with just the LaTeX. "
        # "If it is a table, respond with a plain text representation of the table. "
        # "If it is a code snippet, respond with just the code. "
        # "If it is a photograph, texture, background, or decorative image with no informational content, "
        # "respond with exactly: [non-informational image] "
        # "Only if it is a genuine diagram, chart, figure, or drawing with informational content, "
        # "describe it clearly and concisely in one or two sentences of plain English."
    ),
}

ALL_LABELS           = {"text", "equation", "table", "code", "diagram"}
CONFIDENCE_THRESHOLD = 0.95

FIELDNAMES = [
    "crop_path", "source_image", "region_index",
    "x1", "y1", "x2", "y2",
    "cca_region_type", "label", "confidence", "transcription",
]

# ─────────────────────────────────────────────────────────────────────────────
# Prefix parser  (only used for fallback responses)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_fallback(raw: str) -> tuple:
    """
    Parse:
        LABEL:<type>\n<content>

    Returns:
        (label, content)

    Handles:
      - "LABEL: diagram"
      - "diagram → ..."
      - "diagram: ..."
      - repeated labels in content
    """

    raw = raw.strip()
    if not raw:
        return None, ""

    lines = raw.splitlines()
    first_line = lines[0].strip()

    # Must start with LABEL:
    if not first_line.upper().startswith("LABEL:"):
        return None, raw

    label = first_line[6:].strip().lower()
    content_lines = lines[1:]

    # Remove repeated label prefixes from first content line
    if content_lines:
        first_content = content_lines[0].strip()

        for lbl in ALL_LABELS:
            pattern = rf"^{re.escape(lbl)}\s*[:→\-–>]\s*(.*)$"
            match = re.match(pattern, first_content, re.IGNORECASE)

            if match:
                cleaned = match.group(1).strip()
                content_lines = (
                    ([cleaned] if cleaned else []) + content_lines[1:]
                )
                break

    content = "\n".join(content_lines).strip()

    # Allow empty text content if desired
    if label == "text":
        return "text", content

    if label in ALL_LABELS and content:
        return label, content

    return None, raw


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_client(api_key: str, base_url: str = None):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai")
    kwargs = {"api_key": api_key or "ollama"}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _call_vlm(client, model: str, prompt: str, image_path: str, retries: int = 3) -> str:
    safe_path, is_temp = _safe_image_path(image_path)
    try:
        with open(safe_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    finally:
        if is_temp and os.path.isfile(safe_path):
            os.remove(safe_path)

    ext  = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png",  "webp": "image/webp"}.get(ext, "image/png")

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.001,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text",      "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }],
            )
            time.sleep(0.5)
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries - 1 and "500" in str(e):
                print(f"  ⚠ 500 error, retrying in 5s...", end="", flush=True)
                time.sleep(5)
            else:
                raise


# ─────────────────────────────────────────────────────────────────────────────
# CSV helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_csv(rows: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_transcription(
    csv_path:             str,
    model:                str,
    api_key:              str   = "ollama",
    base_url:             str   = "http://localhost:11434/v1",
    skip_done:            bool  = True,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> str:
    client = _make_client(api_key, base_url)
    rows   = _load_csv(csv_path)
    total  = len(rows)
    done = skipped = errors = fallbacks = relabels = 0

    print(f"  VLM: {model}  |  {total} crops  |  threshold: {confidence_threshold}\n")

    for i, row in enumerate(rows, start=1):
        crop_path = row.get("crop_path", "").strip()

        if skip_done and row.get("transcription", "").strip():
            skipped += 1
            continue

        if not os.path.isfile(crop_path):
            print(f"  [{i:>4}/{total}] MISSING  {crop_path}")
            row["transcription"] = "ERROR: file not found"
            errors += 1
            continue

        label      = (row.get("label") or "").strip().lower()
        confidence = float(row.get("confidence") or 0.0)
        high_conf  = confidence >= confidence_threshold and label in LABEL_PROMPTS

        if high_conf:
            prompt = LABEL_PROMPTS[label]
            prompt = FALLBACK_PROMPT

            source = "tight"
        else:
            prompt = FALLBACK_PROMPT
            source = "open"

        print(f"  [{i:>4}/{total}] [{source}] {label or '?':10s} "
              f"conf={confidence:.2f}  {os.path.basename(crop_path)}",
              end="", flush=True)

        try:
            text = _call_vlm(client, model, prompt, crop_path)

            # Parse LABEL prefix if present in the response.
            if "LABEL:" in text.upper():
                new_label, text = _parse_fallback(text)
                if new_label and new_label != label:
                    print(f"  ✎ {label or '?'} → {new_label}", end="")
                    row["label"] = new_label
                    relabels += 1

            row["transcription"] = text
            done += 1
            print(f"  ✓  {text[:60].replace(chr(10), ' ')}")

        except Exception as e:
            row["transcription"] = f"ERROR: {e}"
            errors += 1
            print(f"  ✗  {e}")

        _save_csv(rows, csv_path)

    _save_csv(rows, csv_path)
    print(f"\n  Done: {done} ok  |  {relabels} relabelled  |  "
          f"{fallbacks} fallbacks  |  {skipped} skipped  |  {errors} errors")
    return csv_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VLM transcription for document crops.")
    parser.add_argument("--csv",                  required=True)
    parser.add_argument("--model",                default="minicpm-v:8b-2.6-q4_K_M")
    parser.add_argument("--api_key",              default="ollama")
    parser.add_argument("--base_url",             default="http://localhost:11434/v1")
    parser.add_argument("--skip_done",            action="store_true")
    parser.add_argument("--confidence_threshold", type=float, default=CONFIDENCE_THRESHOLD)
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}")
        sys.exit(1)

    run_transcription(
        csv_path             = args.csv,
        model                = args.model,
        api_key              = args.api_key,
        base_url             = args.base_url,
        skip_done            = args.skip_done,
        confidence_threshold = args.confidence_threshold,
    )

if __name__ == "__main__":
    main()