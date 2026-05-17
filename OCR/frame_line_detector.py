"""
Line / frame detector — pipeline/line_frame_detector.py

Removes blobs that are page-border frame strokes before region grouping.

Place in pipeline AFTER blob_analysis and BEFORE region_grouping.  Call:

    clean_blobs, rejected = filter_line_blobs(blobs, image_w, image_h, font_size)

then pass `clean_blobs` to group_blobs_into_regions.

Design philosophy
-----------------
This filter does ONE thing only: remove strokes that hug the physical page
border (scan frames, document borders).  It does NOT try to remove ruled
lines, table borders, or box outlines inside the content area — those are
handled downstream by region_classifier.py.

The previous version was too aggressive: LINE_SPAN_FACTOR=0.15 meant any
line spanning 15% of the image was removed, which wiped out equation box
borders and table rules that are legitimate content.
"""

from __future__ import annotations
from typing import TypedDict


# ── types ────────────────────────────────────────────────────────────────────

class Blob(TypedDict):
    x1: int; y1: int; x2: int; y2: int


class FilterResult(TypedDict):
    clean_blobs:       list
    rejected_blobs:    list
    rejection_reasons: dict


# ── tuneable defaults ────────────────────────────────────────────────────────

# How close to the image edge (in pixels) a blob must be to be
# considered a page-border stroke.  Raise this if borders are missed,
# lower it if content near the margin is being wrongly removed.
BORDER_MARGIN_PX: int = 8

# A border stroke must span at least this fraction of the image in its
# long axis to be considered a frame (not just a short mark near the edge).
# Set high (0.60) so only true full-page borders are caught.
BORDER_SPAN_FACTOR: float = 0.60

# A border stroke must be thinner than font_size * this factor in its
# short axis.  Keeps thick decorative borders but removes hairline frames.
BORDER_THIN_FACTOR: float = 0.8


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_page_border(blob: Blob, image_w: int, image_h: int,
                    thin_px: float) -> tuple[bool, str]:
    """
    Return (True, reason) if blob is a page-border frame stroke, else (False, '').

    Conditions (ALL must hold):
      1. The blob hugs one of the four image edges (within BORDER_MARGIN_PX).
      2. It spans >= BORDER_SPAN_FACTOR of the image in its long axis.
      3. Its short axis <= thin_px  (it is a stroke, not a block of text).
    """
    x1, y1, x2, y2 = blob["x1"], blob["y1"], blob["x2"], blob["y2"]
    m  = BORDER_MARGIN_PX
    bw = x2 - x1
    bh = y2 - y1

    # ── horizontal border (top or bottom edge) ────────────────────────────────
    hugs_top    = y1 <= m
    hugs_bottom = y2 >= image_h - m
    if (hugs_top or hugs_bottom):
        if bw >= image_w * BORDER_SPAN_FACTOR and bh <= thin_px:
            return True, "frame_stroke"

    # ── vertical border (left or right edge) ──────────────────────────────────
    hugs_left  = x1 <= m
    hugs_right = x2 >= image_w - m
    if (hugs_left or hugs_right):
        if bh >= image_h * BORDER_SPAN_FACTOR and bw <= thin_px:
            return True, "frame_stroke"

    return False, ""


# ── public API ───────────────────────────────────────────────────────────────

def filter_line_blobs(
    blobs:    list[Blob],
    image_w:  int,
    image_h:  int,
    font_size: float,
    *,
    border_margin_px:  int   = BORDER_MARGIN_PX,
    border_span_factor: float = BORDER_SPAN_FACTOR,
    border_thin_factor: float = BORDER_THIN_FACTOR,
) -> FilterResult:
    """
    Remove page-border frame blobs from the blob list.

    Parameters
    ----------
    blobs            : raw blob list from blob_analysis
    image_w/image_h  : pixel dimensions of the source image
    font_size        : estimated font size (pixels) from blob_analysis
    border_margin_px : how close to the edge counts as "hugging the border"
    border_span_factor: min fraction of image dimension to be a border stroke
    border_thin_factor: short axis must be < font_size × this to be a stroke

    Returns
    -------
    FilterResult with clean_blobs, rejected_blobs, rejection_reasons
    """
    thin_px = font_size * border_thin_factor

    # Temporarily override module constants with call-site values
    global BORDER_MARGIN_PX, BORDER_SPAN_FACTOR
    _saved_margin = BORDER_MARGIN_PX
    _saved_span   = BORDER_SPAN_FACTOR
    BORDER_MARGIN_PX  = border_margin_px
    BORDER_SPAN_FACTOR = border_span_factor

    clean:    list[Blob] = []
    rejected: list[Blob] = []
    reasons:  dict[int, str] = {}

    for idx, blob in enumerate(blobs):
        is_border, reason = _is_page_border(blob, image_w, image_h, thin_px)
        if is_border:
            rejected.append(blob)
            reasons[idx] = reason
        else:
            clean.append(blob)

    BORDER_MARGIN_PX  = _saved_margin
    BORDER_SPAN_FACTOR = _saved_span

    print(f"  Line filter: {len(rejected)} blob(s) removed "
          f"({len(clean)} remaining) [frame={len(rejected)}]")

    return {
        "clean_blobs":       clean,
        "rejected_blobs":    rejected,
        "rejection_reasons": reasons,
    }