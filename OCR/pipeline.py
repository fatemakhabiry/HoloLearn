"""
pipeline/pipeline.py — Main orchestrator.

Stages
------
1  Preprocessing        (preprocess)
2  Blob analysis        (run_blob_analysis)
3  Line/frame filter    (filter_line_blobs)
4  Density detection    (BlobDocumentTypeDetector)
5  Region grouping      (group_blobs_into_regions)
6  Crop extraction      (extract_crops)          ← writes CSV + crop images
7  CNN classification   (run_classifier)         ← fills label column
8  VLM transcription    (run_transcription)      ← fills transcription column
9  JSON assembly        (build_json)             ← structured output

Stages 7-9 are optional — call run_cca_pipeline() to stop after stage 6
(crops + CSV ready for your CNN), or run_full_pipeline() for everything.
"""

import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from blob_detector       import BlobDocumentTypeDetector
from region_grouping     import group_blobs_into_regions
from preprocessing       import preprocess
from blob_analysis       import run_blob_analysis
from frame_line_detector import filter_line_blobs
from crop_extractor      import extract_crops


def _detect_density(blobs, font_size, width, height, debug):
    detector = BlobDocumentTypeDetector()
    result   = detector.detect(
        blobs=blobs, img_width=width, img_height=height,
        font_size=font_size, debug=debug,
    )
    return result.density_class, result.confidence


_DENSITY_LABELS = {0: "SPARSE", 1: "MEDIUM", 2: "DENSE"}


# ═══════════════════════════════════════════════════════════════════════════════
# Stages 1-6: CCA pipeline → crops + CSV
# ═══════════════════════════════════════════════════════════════════════════════

def run_cca_pipeline(image_path, output_dir="output/crops",
                     detector_mode="blob", debug=False):
    """
    Run stages 1–6: preprocess → blobs → filter → group → crop.

    Returns
    -------
    gray, binary, blobs, font_size, regions, csv_path
    """

    # ── Stage 1 — Preprocessing ───────────────────────────────────────────────
    print(f"[1/6] Preprocessing: {os.path.basename(image_path)}")
    pre    = preprocess(image_path)
    gray   = pre["gray"]
    binary = pre["binary"]
    width  = pre["width"]
    height = pre["height"]
    print(f"      {width}×{height}px  skew={pre['skew_angle']:.1f}°")

    # ── Stage 2 — Blob analysis ───────────────────────────────────────────────
    print("[2/6] Blob analysis...")
    blob_res  = run_blob_analysis(binary)
    blobs     = blob_res["blobs"]
    font_size = blob_res["font_size"]
    print(f"      blobs={len(blobs)}  font_size={font_size}px")

    # ── Stage 3 — Line / frame filter ────────────────────────────────────────
    print("[3/6] Line/frame filter...")
    filt  = filter_line_blobs(blobs, width, height, font_size)
    blobs = filt["clean_blobs"]

    # ── Stage 4 — Density classification ─────────────────────────────────────
    print("[4/6] Density classification...")
    density_class, dt_conf = _detect_density(blobs, font_size, width, height, debug)
    label = _DENSITY_LABELS[density_class]
    print(f"      → class {density_class} ({label})  conf={dt_conf:.0%}")

    line_v_factor = {0: 1.0, 1: 0.8, 2: 0.6}.get(density_class, 1.2)
    h_gap_factor  = {0: 2.2, 1: 2,   2: 1.8}.get(density_class, 2.0)

    # ── Stage 5 — Region grouping ─────────────────────────────────────────────
    print("[5/6] Region grouping...")
    regions = group_blobs_into_regions(
        blobs, font_size,
        img_width=width,
        img_height=height,
        h_gap_factor=h_gap_factor,
        line_v_factor=line_v_factor,
        para_v_factor=None,
        min_blobs_per_region=3,
    )
    print(f"      → {len(regions)} raw regions")

    # ── Stage 6 — Crop extraction ─────────────────────────────────────────────
    print("[6/6] Extracting crops...")
    csv_path = extract_crops(
        image_path=image_path,
        output_dir=output_dir,
        regions=regions,
        font_size=font_size,
    )

    return gray, binary, blobs, font_size, regions, csv_path


# ═══════════════════════════════════════════════════════════════════════════════
# Stages 7-9: classifier + VLM + JSON
# ═══════════════════════════════════════════════════════════════════════════════

def run_classifier_stage(csv_path, model_path, device="cuda"):
    """Stage 7: CNN classifier → fills label column."""
    from classifier_runner import run_classifier
    print(f"[7] Running CNN classifier  (model={model_path})...")
    return run_classifier(csv_path, model_path, device)


def run_vlm_stage(csv_path, api_key, model="gpt-4o", base_url=None):
    """Stage 8: VLM transcription → fills transcription column."""
    from vlm_transcriber import run_transcription
    print(f"[8] Running VLM transcription  (model={model})...")
    return run_transcription(
        csv_path = csv_path,
        model    = model,
        api_key  = api_key,
        base_url = base_url,
    )


def run_json_stage(csv_path, output_dir):
    """
    Stage 9: assemble completed CSV into structured JSON.

    Saves <output_dir>/<csv_stem>.json and returns (docs, json_path).
    """
    from csv_to_json import build_json
    print("[9] Assembling JSON output...")
    json_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(csv_path))[0] + ".json"
    )
    docs = build_json(csv_path, out_path=json_path)
    print(f"    → {json_path}")
    return docs, json_path


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience: run everything end-to-end
# ═══════════════════════════════════════════════════════════════════════════════

import os, csv, shutil

def run_full_pipeline(image_path, model_path, api_key,
                      output_dir="output/crops",
                      classifier_device="cpu",
                      vlm_model="gpt-4o",
                      vlm_base_url=None,
                      debug=False):
    _, _, _, _, _, csv_path = run_cca_pipeline(
        image_path, output_dir=output_dir, debug=debug
    )
    csv_path = run_classifier_stage(csv_path, model_path, classifier_device)
    csv_path = run_vlm_stage(csv_path, api_key, vlm_model, vlm_base_url)
    docs, json_path = run_json_stage(csv_path, output_dir)

    # ── Delete crop files now that JSON is saved ──────────────────────────
    deleted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            crop = row.get("crop_path", "").strip()
            if crop and os.path.isfile(crop):
                try:
                    os.remove(crop)
                    deleted += 1
                except OSError:
                    pass

    # Also remove the crops folder if it's now empty
    crops_dir = os.path.dirname(csv_path)
    if os.path.isdir(crops_dir) and not any(
        f.endswith(".png") for f in os.listdir(crops_dir)
    ):
        pass  # keep the folder — CSV and JSON still live there

    print(f"\n{'='*60}")
    print(f"Done.")
    print(f"  CSV      → {csv_path}")
    print(f"  JSON     → {json_path}")
    print(f"  docs     → {len(docs)} document(s)")
    print(f"  deleted  → {deleted} crop file(s)")
    return docs, json_path, csv_path

# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    image_path        = "images/img5.png"
    model_path        = "model/modelv3.pth"
    output_dir        = "outputv3/"
    classifier_device = "cpu"
    api_key           = "ollama"
   # "gemma3:4b" "qwen2.5vl:3b" "moondream" "MedAIBase/PaddleOCR-VL:0.9b" "qwen3-vl:2b"
    vlm_model         ="gemma3:4b" 
    vlm_base_url      = "http://localhost:11434/v1"

    docs, json_path, csv_path = run_full_pipeline(
        image_path        = image_path,
        model_path        = model_path,
        output_dir        = output_dir,
        classifier_device = classifier_device,
        vlm_model         = vlm_model,
        vlm_base_url      = vlm_base_url,
        api_key           = api_key,
        debug             = True,
    )