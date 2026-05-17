"""
crop_and_save.py  /  crop_extractor.py
=======================================
Crops detected regions from a document image, saves them as PNG files,
and writes a CSV with one row per crop.

CSV columns
-----------
  crop_path       — relative path to the saved crop image
  source_image    — original image file path
  region_index    — 1-based reading order (top→bottom, left→right)
  x1, y1, x2, y2 — bounding box in the original image (pixels)
  cca_region_type — type from CCA pipeline: text | table | diagram | code
  label           — empty; filled by CNN classifier
  confidence      — empty; filled by CNN classifier (0.0 – 1.0)
  transcription   — empty; filled by run_vlm.py
"""

import os
import csv
import argparse

from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# Core crop function
# ─────────────────────────────────────────────────────────────────────────────

def crop_and_save(image_path: str,
                  regions:    list,
                  out_dir:    str = "frames",
                  padding:    int = 4,
                  font_size:  int = 20) -> list:
    """
    Crop every region from image_path, save to out_dir, return CSV rows.

    Reading order sort
    ------------------
    PIL coordinates: x grows right, y grows down.
    We quantise y1 into row bands of height=font_size so regions on the
    same visual line share the same band index, then sort left→right by x1
    within each band.

    Parameters
    ----------
    image_path : source document image
    regions    : list of region dicts from group_blobs_into_regions()
    out_dir    : folder to save crop PNGs (created if absent)
    padding    : pixels of extra margin around each bounding box
    font_size  : estimated body-text height in px (row-band quantisation)

    Returns
    -------
    list[dict]  one dict per crop, ready to write to CSV
    """
    image_path = os.path.abspath(image_path)
    img_stem   = os.path.splitext(os.path.basename(image_path))[0]
    os.makedirs(out_dir, exist_ok=True)

    src_img      = Image.open(image_path).convert("RGB")
    img_w, img_h = src_img.size   # (width=x_max, height=y_max)

    # ── Reading-order sort ────────────────────────────────────────────────────
    band    = max(10, font_size)
    regions = sorted(regions, key=lambda r: (r["y1"] // band, r["x1"]))

    print(f"\n{'='*60}")
    print(f"Cropping: {os.path.basename(image_path)}  "
          f"({len(regions)} regions  band={band}px)")
    print(f"{'='*60}")

    rows = []
    for n, region in enumerate(regions, start=1):
        x1 = max(0,         region["x1"] - padding)
        y1 = max(0,         region["y1"] - padding)
        x2 = min(img_w - 1, region["x2"] + padding)
        y2 = min(img_h - 1, region["y2"] + padding)

        crop      = src_img.crop((x1, y1, x2, y2))
        filename  = f"{img_stem}_{n}.png"
        crop_path = os.path.join(out_dir, filename)
        crop.save(crop_path)

        rows.append({
            "crop_path":       os.path.relpath(crop_path),
            "source_image":    os.path.relpath(image_path),
            "region_index":    n,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "cca_region_type": region.get("region_type", "text"),
            "label":           "",
            "confidence":      "",      # filled by classifier_runner.py
            "transcription":   "",
        })
        print(f"  [{n:>3}] {region.get('region_type','text'):8s}  "
              f"({x1},{y1})→({x2},{y2})  → {filename}")

    print(f"\n  Saved {len(rows)} crops → {out_dir}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# CSV writer
# ─────────────────────────────────────────────────────────────────────────────

def write_csv(rows: list, csv_path: str, append: bool = False) -> None:
    fieldnames = [
        "crop_path", "source_image", "region_index",
        "x1", "y1", "x2", "y2",
        "cca_region_type", "label", "confidence", "transcription",
    ]
    mode   = "a" if append else "w"
    exists = os.path.isfile(csv_path)
    with open(csv_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not (append and exists):
            writer.writeheader()
        writer.writerows(rows)
    print(f"  CSV {'appended' if append and exists else 'written'} → {csv_path}  "
          f"({len(rows)} rows)")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point  (called by pipeline.py)
# ─────────────────────────────────────────────────────────────────────────────

def extract_crops(image_path: str,
                  regions:    list,
                  output_dir: str = "output",
                  padding:    int = 4,
                  font_size:  int = 20) -> str:
    """
    Crop regions, save PNGs, write CSV, return csv_path.

    Parameters
    ----------
    image_path : source document image
    regions    : list of region dicts from group_blobs_into_regions()
    output_dir : root output folder
    padding    : pixels of padding around each crop
    font_size  : passed to crop_and_save for reading-order sort

    Returns
    -------
    str  path to the written CSV, or None if no regions
    """
    if not os.path.isfile(image_path):
        print(f"WARNING: file not found — {image_path}")
        return None

    image_name = os.path.splitext(os.path.basename(image_path))[0]
    frames_dir = os.path.join(output_dir, f"{image_name}_regions")
    csv_path   = os.path.join(frames_dir, f"{image_name}_regions.csv")

    rows = crop_and_save(
        image_path,
        regions,
        out_dir   = frames_dir,
        padding   = padding,
        font_size = font_size,
    )

    if not rows:
        print("No regions found.")
        return None

    os.makedirs(frames_dir, exist_ok=True)
    write_csv(rows, csv_path, append=False)
    print(f"Done. {len(rows)} crops  |  CSV → {csv_path}")
    return csv_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crop CCA regions and save to CSV.")
    parser.add_argument("images",    nargs="+")
    parser.add_argument("--out_dir", default="frames")
    parser.add_argument("--csv",     default="regions.csv")
    parser.add_argument("--padding", type=int, default=4)
    args = parser.parse_args()

    all_rows = []
    for img_path in args.images:
        if not os.path.isfile(img_path):
            print(f"WARNING: file not found — {img_path}")
            continue
        rows = crop_and_save(img_path, regions=[], out_dir=args.out_dir,
                             padding=args.padding)
        all_rows.extend(rows)

    if all_rows:
        write_csv(all_rows, args.csv)
        print(f"Done. {len(all_rows)} crops  |  CSV → {args.csv}")
    else:
        print("No regions found.")