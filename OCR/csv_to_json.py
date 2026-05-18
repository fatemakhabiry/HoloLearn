"""
csv_to_json.py
==============
Final stage: reads the completed CSV (crop_path, label, transcription all
filled) and assembles one structured JSON document per source image.

Output structure per image
--------------------------
{
    "source_image": "page1.png",
    "text": "Some paragraph text [EQ_1] more text [CODE_1] continued [FIG_1]",
    "equations": [
        {"id": "EQ_1", "latex": "..."}
    ],
    "code": [
        {"id": "CODE_1", "language": "python", "content": "..."}
    ],
    "figures": [
        {"id": "FIG_1", "filename": "page1_7.png", "caption": "..."}
    ]
}

Rules
-----
- Regions are processed in reading order (region_index).
- text / equation regions go inline into the "text" field.
  Equations appear as [EQ_n] placeholders in the text.
- code regions appear as [CODE_n] placeholders in the text.
- diagram/figure/table regions appear as [FIG_n] placeholders in the text.
- The placeholder lists (equations, code, figures) hold the actual content.
- Tables are treated as figures (markdown table as caption).

Usage
-----
    from csv_to_json import build_json

    docs = build_json("regions.csv")
    # docs is a list of dicts, one per source image

    # or save to file:
    docs = build_json("regions.csv", out_path="output.json")
"""

import csv
import json
import os
import re


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_code_block(transcription: str) -> tuple:
    """
    Extract language and content from a markdown fenced code block.
    Returns (language, content).
    Falls back to ("", transcription) if no fence found.
    """
    match = re.match(r"```(\w*)\n?(.*?)```", transcription, re.DOTALL)
    if match:
        lang    = match.group(1).strip() or "unknown"
        content = match.group(2).strip()
        return lang, content
    return "unknown", transcription.strip()


def _rows_for_image(rows: list, source_image: str) -> list:
    """Return rows for one source image, sorted by region_index."""
    subset = [r for r in rows if r.get("source_image") == source_image]
    subset.sort(key=lambda r: int(r.get("region_index", 0)))
    return subset


# ─────────────────────────────────────────────────────────────────────────────
# Core builder
# ─────────────────────────────────────────────────────────────────────────────

# def _build_document(source_image: str, rows: list) -> dict:
#     """
#     Assemble one document dict from the rows belonging to source_image.
#     """
#     text_parts = []   # segments that form the final "text" string
#     equations  = []
#     code_blocks= []
#     figures    = []

#     eq_n   = 0
#     code_n = 0
#     fig_n  = 0

#     for row in rows:
#         label         = (row.get("label") or row.get("cca_region_type") or "text").strip().lower()
#         transcription = (row.get("transcription") or "").strip()
#         crop_path     = row.get("crop_path", "")
#         crop_filename = os.path.basename(crop_path)

#         # skip rows with errors or empty transcriptions
#         if not transcription or transcription.startswith("ERROR"):
#             continue

#         if label == "text":
#             text_parts.append(transcription)

#         elif label == "equation":
#             eq_n += 1
#             eq_id = f"EQ_{eq_n}"
#             equations.append({"id": eq_id, "latex": transcription})
#             text_parts.append(f"[{eq_id}]")

#         elif label == "code":
#             code_n += 1
#             code_id  = f"CODE_{code_n}"
#             lang, content = _parse_code_block(transcription)
#             code_blocks.append({"id": code_id, "language": lang, "content": content})
#             text_parts.append(f"[{code_id}]")

#         elif label in ("diagram", "figure", "table"):
#             fig_n += 1
#             fig_id = f"FIG_{fig_n}"
#             figures.append({
#                 "id":       fig_id,
#                 "filename": crop_filename,
#                 "caption":  transcription,
#             })
#             text_parts.append(f"[{fig_id}]")

#         else:
#             # unknown label — treat as plain text
#             text_parts.append(transcription)

#     return {
#         "source_image": source_image,
#         "text":         "\n\n".join(text_parts),
#         "equations":    equations,
#         "code":         code_blocks,
#         "figures":      figures,
#     }

def _build_document(source_image: str, rows: list) -> dict:
    """
    Assemble one document dict from the rows belonging to source_image.

    Equations and code are inserted INLINE into the text.
    Only figures/tables/diagrams are extracted into separate lists.
    """
    text_parts = []
    figures    = []

    fig_n = 0

    for row in rows:
        label         = (row.get("label") or row.get("cca_region_type") or "text").strip().lower()
        transcription = (row.get("transcription") or "").strip()
        crop_path     = row.get("crop_path", "")
        crop_filename = os.path.basename(crop_path)

        # skip invalid rows
        if not transcription or transcription.startswith("ERROR"):
            continue

        # ─────────────────────────────────────────────
        # INLINE CONTENT
        # ─────────────────────────────────────────────
        if label == "text":
            text_parts.append(transcription)

        elif label == "equation":
            # equations inserted directly inline
            text_parts.append(transcription)

        elif label == "code":
            # code inserted directly inline
            lang, content = _parse_code_block(transcription)

            # preserve markdown fencing
            inline_code = f"```{lang}\n{content}\n```"
            text_parts.append(inline_code)

        # ─────────────────────────────────────────────
        # EXTERNAL FIGURES
        # ─────────────────────────────────────────────
        elif label in ("diagram", "figure", "table"):
            fig_n += 1
            fig_id = f"FIG_{fig_n}"

            figures.append({
                "id":       fig_id,
                "filename": crop_filename,
                "caption":  transcription,
            })

            # placeholder remains in text
            text_parts.append(f"[{fig_id}]")

        else:
            # unknown labels treated as text
            text_parts.append(transcription)

    return {
        "source_image": source_image,
        "text": "\n\n".join(text_parts),
        "figures": figures,
    }
# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_json(
    csv_path: str,
    out_path: str = None,
    indent:   int = 2,
) -> list:
    """
    Read a completed CSV and return a list of document dicts,
    one per unique source_image.

    Parameters
    ----------
    csv_path : path to the CSV (all columns filled including transcription)
    out_path : if given, write the JSON array to this file
    indent   : JSON indentation (default 2)

    Returns
    -------
    list[dict]  one dict per source image
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # preserve original page order
    seen   = []
    images = []
    for r in rows:
        si = r.get("source_image", "")
        if si and si not in seen:
            seen.append(si)
            images.append(si)

    documents = []
    for source_image in images:
        image_rows = _rows_for_image(rows, source_image)
        doc        = _build_document(source_image, image_rows)
        documents.append(doc)
        # print(f"  built doc: {source_image}  "
        #     #   f"eq={len(doc['equations'])}  "
        #       f"code={len(doc['code'])}  "
        #       f"fig={len(doc['figures'])}  "
        #       f"text_len={len(doc['text'])}")

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=indent, ensure_ascii=False)
        print(f"  JSON saved → {out_path}")

    return documents


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Assemble completed CSV into structured JSON.")
    parser.add_argument("--csv",  required=True,  help="Path to completed CSV")
    parser.add_argument("--out",  default=None,   help="Output JSON file path")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}")
        sys.exit(1)

    out_path = args.out or args.csv.replace(".csv", ".json")
    docs = build_json(args.csv, out_path=out_path)
    print(f"\nDone. {len(docs)} document(s) written → {out_path}")
