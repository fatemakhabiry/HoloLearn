# """
# region_grouping.py — Group blobs into candidate regions.

# Two-pass strategy
# -----------------
# Pass A (tight)  — connect blobs that are within one line-spacing.
#                   Produces small line-level regions.
# Pass B (para)   — merge line regions whose vertical gap is below the
#                   auto-detected paragraph gap threshold.

# Post-processing — split any surviving region that is too wide
#                   (column split) or too tall (strip split).
#                 — merge tiny scattered regions (< 2% image area)
#                 — remove nested boxes (child < 30% of parent area)
# """


# # ═══════════════════════════════════════════════════════════════════════════════
# # Internal helpers
# # ═══════════════════════════════════════════════════════════════════════════════

# def _union_find_group(blobs, h_gap, v_gap, min_members=1):
#     """Union-Find proximity grouping with path compression + v_gap early-break."""
#     sorted_blobs = sorted(blobs, key=lambda b: (b["y1"], b["x1"]))
#     n      = len(sorted_blobs)
#     parent = list(range(n))

#     def find(i):
#         while parent[i] != i:
#             parent[i] = parent[parent[i]]
#             i = parent[i]
#         return i

#     def union(i, j):
#         parent[find(i)] = find(j)

#     for i in range(n):
#         bi = sorted_blobs[i]
#         for j in range(i + 1, n):
#             bj = sorted_blobs[j]
#             if bj["y1"] - bi["y2"] > v_gap:
#                 break
#             v_dist = max(0, bj["y1"] - bi["y2"])
#             h_dist = max(0, max(bi["x1"], bj["x1"]) - min(bi["x2"], bj["x2"]))
#             if v_dist <= v_gap and h_dist <= h_gap:
#                 union(i, j)

#     groups = {}
#     for i in range(n):
#         groups.setdefault(find(i), []).append(sorted_blobs[i])

#     regions = []
#     for members in groups.values():
#         if len(members) < min_members:
#             continue
#         rx1 = min(b["x1"] for b in members)
#         ry1 = min(b["y1"] for b in members)
#         rx2 = max(b["x2"] for b in members)
#         ry2 = max(b["y2"] for b in members)
#         rw  = rx2 - rx1 + 1
#         rh  = ry2 - ry1 + 1
#         box_area = rw * rh
#         ink_area = sum(b["area"] for b in members)
#         regions.append({
#             "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
#             "width": rw, "height": rh,
#             "blob_count": len(members),
#             "density": ink_area / box_area if box_area > 0 else 0.0,
#             "blobs": members,
#         })
#     return regions


# def _estimate_para_gap_factor(line_regions, font_size):
#     """
#     Auto-detect the vertical gap threshold that separates lines within
#     a paragraph from gaps between paragraphs/blocks.
#     """
#     if len(line_regions) < 3:
#         return font_size * 2.5

#     sorted_lines = sorted(line_regions, key=lambda r: r["y1"])
#     gaps = []
#     for i in range(len(sorted_lines) - 1):
#         gap = sorted_lines[i + 1]["y1"] - sorted_lines[i]["y2"]
#         if gap > 0:
#             gaps.append(gap)

#     if len(gaps) < 3:
#         return font_size * 2.5

#     gaps.sort()
#     n = len(gaps)

#     threshold = None
#     for i in range(1, n):
#         if gaps[i] >= font_size and gaps[i] > gaps[i - 1] * 1.5:
#             threshold = gaps[i - 1] + 2
#             break

#     if threshold is None:
#         above = [g for g in gaps if g >= font_size]
#         if above:
#             threshold = above[0] - 1
#         else:
#             threshold = font_size * 1.1

#     return float(max(threshold, font_size * 1.1))


# def _split_region_by_x_gap(group_blobs, font_size, h_gap_factor,
#                              min_blobs_per_region, min_region_density):
#     """Split a too-wide region into x-axis columns."""
#     h_gap       = font_size * h_gap_factor
#     sorted_by_x = sorted(group_blobs, key=lambda b: b["center_c"])
#     columns, current = [], [sorted_by_x[0]]
#     for b in sorted_by_x[1:]:
#         if b["x1"] - current[-1]["x2"] > h_gap:
#             columns.append(current)
#             current = [b]
#         else:
#             current.append(b)
#     columns.append(current)

#     result = []
#     for col in columns:
#         if len(col) < min_blobs_per_region:
#             continue
#         rx1 = min(b["x1"] for b in col)
#         ry1 = min(b["y1"] for b in col)
#         rx2 = max(b["x2"] for b in col)
#         ry2 = max(b["y2"] for b in col)
#         rw  = rx2 - rx1 + 1
#         rh  = ry2 - ry1 + 1
#         box_area = rw * rh
#         density  = sum(b["area"] for b in col) / box_area if box_area > 0 else 0.0
#         if density < min_region_density:
#             continue
#         result.append({
#             "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
#             "width": rw, "height": rh,
#             "blobs": col,
#             "blob_count": len(col),
#             "density": density,
#         })
#     return result


# def _split_region_by_y_gap(group_blobs, font_size, line_v_factor,
#                              min_blobs_per_region, min_region_density):
#     """Split a too-tall region into horizontal strips."""
#     v_cut  = font_size * line_v_factor * 1.5
#     by_y   = sorted(group_blobs, key=lambda b: b["center_r"])
#     strips, current = [], [by_y[0]]
#     for b in by_y[1:]:
#         if b["y1"] - current[-1]["y2"] > v_cut:
#             strips.append(current)
#             current = [b]
#         else:
#             current.append(b)
#     strips.append(current)

#     result = []
#     for strip in strips:
#         if len(strip) < min_blobs_per_region:
#             continue
#         rx1 = min(b["x1"] for b in strip)
#         ry1 = min(b["y1"] for b in strip)
#         rx2 = max(b["x2"] for b in strip)
#         ry2 = max(b["y2"] for b in strip)
#         rw  = rx2 - rx1 + 1
#         rh  = ry2 - ry1 + 1
#         box_area = rw * rh
#         density  = sum(b["area"] for b in strip) / box_area if box_area > 0 else 0.0
#         n_lines  = max(1, rh / font_size)
#         if density < min_region_density / (n_lines ** 0.5):
#             continue
#         result.append({
#             "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
#             "width": rw, "height": rh,
#             "blobs": strip,
#             "blob_count": len(strip),
#             "density": density,
#         })
#     return result


# # ═══════════════════════════════════════════════════════════════════════════════
# # Post-processing filters
# # ═══════════════════════════════════════════════════════════════════════════════

# def _merge_tiny_regions(regions, img_width, img_height, tiny_ratio=0.02):
#     """
#     Collect every region whose bounding-box area < tiny_ratio × image area
#     and merge them all into one bounding box.

#     If the merged result is still tiny (e.g. only 1-2 stray letters exist on
#     the whole page), fall back to a full-image region so the VLM always gets
#     something useful.

#     Parameters
#     ----------
#     tiny_ratio : area fraction threshold  (default 0.02 = 2% of image)
#     """
#     img_area  = img_width * img_height
#     threshold = img_area * tiny_ratio

#     normal, tiny = [], []
#     for r in regions:
#         area = (r["x2"] - r["x1"] + 1) * (r["y2"] - r["y1"] + 1)
#         (tiny if area < threshold else normal).append(r)

#     if not tiny:
#         return regions                          # nothing to do

#     # Build one merged bounding box from all tiny regions
#     all_blobs = [b for r in tiny for b in r.get("blobs", [])]
#     mx1 = min(r["x1"] for r in tiny)
#     my1 = min(r["y1"] for r in tiny)
#     mx2 = max(r["x2"] for r in tiny)
#     my2 = max(r["y2"] for r in tiny)
#     mw, mh   = mx2 - mx1 + 1, my2 - my1 + 1
#     box_area = mw * mh
#     density  = (sum(b["area"] for b in all_blobs) / box_area
#                 if all_blobs and box_area > 0 else 0.0)

#     merged = {
#         "x1": mx1, "y1": my1, "x2": mx2, "y2": my2,
#         "width": mw, "height": mh,
#         "blob_count": sum(r["blob_count"] for r in tiny),
#         "density": density,
#         "blobs": all_blobs,
#     }

#     # If the merged box is still smaller than the threshold → full image
#     if mw * mh < threshold:
#         print("  Tiny-region fallback → full-image region")
#         merged = {
#             "x1": 0, "y1": 0,
#             "x2": img_width - 1, "y2": img_height - 1,
#             "width": img_width, "height": img_height,
#             "blob_count": sum(r["blob_count"] for r in tiny),
#             "density": 0.0, "blobs": all_blobs,
#         }

#     print(f"  Tiny-region merge: {len(tiny)} tiny → 1  "
#           f"({len(normal)} normal kept)")
#     return normal + [merged]


# def _remove_nested_regions(regions, nest_ratio=0.30):
#     """
#     Drop any region that is fully enclosed by a larger region AND whose
#     area is less than nest_ratio × the enclosing region's area.

#     Parameters
#     ----------
#     nest_ratio : if inner_area / outer_area < this, drop the inner region
#                  (default 0.30 = 30%)
#     """
#     if len(regions) < 2:
#         return regions

#     def _area(r):
#         return (r["x2"] - r["x1"] + 1) * (r["y2"] - r["y1"] + 1)

#     def _contains(outer, inner):
#         return (outer["x1"] <= inner["x1"] and
#                 outer["y1"] <= inner["y1"] and
#                 outer["x2"] >= inner["x2"] and
#                 outer["y2"] >= inner["y2"])

#     keep = [True] * len(regions)
#     for i, inner in enumerate(regions):
#         if not keep[i]:
#             continue
#         a_inner = _area(inner)
#         for j, outer in enumerate(regions):
#             if i == j or not keep[j]:
#                 continue
#             if _contains(outer, inner):
#                 if _area(outer) > 0 and (a_inner / _area(outer)) < nest_ratio:
#                     keep[i] = False
#                     break

#     removed = keep.count(False)
#     if removed:
#         print(f"  Nested-box removal: {removed} region(s) dropped")
#     return [r for r, k in zip(regions, keep) if k]


# # ═══════════════════════════════════════════════════════════════════════════════
# # PUBLIC ENTRY POINT
# # ═══════════════════════════════════════════════════════════════════════════════

# def group_blobs_into_regions(blobs, font_size,
#                               img_width=None,
#                               img_height=None,
#                               h_gap_factor=2.0,
#                               line_v_factor=1.5,
#                               para_v_factor=None,
#                               min_blobs_per_region=2,
#                               max_region_aspect=25.0,
#                               max_region_height_factor=20.0,
#                               min_region_density=0.02,
#                               tiny_region_ratio=0.02,
#                               nest_region_ratio=0.30):
#     """
#     Group blobs into candidate regions using a two-pass strategy.

#     Parameters
#     ----------
#     blobs                    : list[dict]  from find_all_blobs()
#     font_size                : int         estimated body-text height in px
#     img_width, img_height    : int         image dimensions — pass from preprocess()
#                                            (required for tiny-region filter)
#     h_gap_factor             : float       horizontal gap in font_size units
#     line_v_factor            : float       Pass A vertical gap
#     para_v_factor            : float|None  Pass B vertical gap; None = auto
#     min_blobs_per_region     : int         minimum blobs to keep a region
#     max_region_aspect        : float       width/height above which column-split fires
#     max_region_height_factor : float       height/font above which strip-split fires
#     min_region_density       : float       ink/box ratio below which region is dropped
#     tiny_region_ratio        : float       regions whose area < this × image area
#                                            are merged together  (default 0.02 = 2%)
#     nest_region_ratio        : float       nested child whose area < this × parent
#                                            area is dropped  (default 0.30 = 30%)

#     Returns
#     -------
#     list[dict] — each dict has:
#         x1, y1, x2, y2, width, height, blob_count, density, blobs
#     """
#     if not blobs:
#         return []

#     h_gap      = font_size * h_gap_factor
#     line_v_gap = font_size * line_v_factor

#     # ── Pass A: tight grouping ────────────────────────────────────────────────
#     line_regions = _union_find_group(
#         blobs, h_gap=h_gap, v_gap=line_v_gap, min_members=1
#     )

#     # ── Auto-detect paragraph gap ─────────────────────────────────────────────
#     if para_v_factor is None:
#         para_v_px = _estimate_para_gap_factor(line_regions, font_size)
#         para_v_px = min(para_v_px, font_size * 4.0)
#     else:
#         para_v_px = font_size * para_v_factor

#     # ── Pass B: paragraph grouping via super-blobs ────────────────────────────
#     super_blobs = []
#     for lr in line_regions:
#         super_blobs.append({
#             "x1":      lr["x1"],
#             "y1":      lr["y1"],
#             "x2":      lr["x2"],
#             "y2":      lr["y2"],
#             "center_r": (lr["y1"] + lr["y2"]) / 2,
#             "center_c": (lr["x1"] + lr["x2"]) / 2,
#             "area":    lr["density"] * lr["width"] * lr["height"],
#             "_blobs":  lr["blobs"],
#         })

#     para_regions_raw = _union_find_group(
#         super_blobs, h_gap=h_gap, v_gap=para_v_px, min_members=1
#     )

#     para_regions = []
#     for pr in para_regions_raw:
#         real_blobs = []
#         for sb in pr["blobs"]:
#             real_blobs.extend(sb.get("_blobs", [sb]))
#         if len(real_blobs) < min_blobs_per_region:
#             continue
#         rx1 = min(b["x1"] for b in real_blobs)
#         ry1 = min(b["y1"] for b in real_blobs)
#         rx2 = max(b["x2"] for b in real_blobs)
#         ry2 = max(b["y2"] for b in real_blobs)
#         rw  = rx2 - rx1 + 1
#         rh  = ry2 - ry1 + 1
#         box_area = rw * rh
#         density  = sum(b["area"] for b in real_blobs) / box_area if box_area > 0 else 0.0
#         if density < min_region_density:
#             continue
#         para_regions.append({
#             "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
#             "width": rw, "height": rh,
#             "blob_count": len(real_blobs),
#             "density": density,
#             "blobs": real_blobs,
#         })

#     # ── Post-processing: split oversized regions ──────────────────────────────
#     final = []
#     for region in para_regions:
#         rw = region["width"]
#         rh = region["height"]
#         ar = rw / rh if rh > 0 else 0

#         if ar > max_region_aspect:
#             parts = _split_region_by_x_gap(
#                 region["blobs"], font_size, h_gap_factor,
#                 min_blobs_per_region, min_region_density)
#             final.extend(parts)
#         elif rh > font_size * max_region_height_factor:
#             parts = _split_region_by_y_gap(
#                 region["blobs"], font_size, line_v_factor,
#                 min_blobs_per_region, min_region_density)
#             final.extend(parts)
#         else:
#             final.append(region)

#     # # ── Filter 1: merge tiny scattered regions ────────────────────────────────
#     # if img_width and img_height:
#     #     final = _merge_tiny_regions(
#     #         final, img_width, img_height, tiny_ratio=tiny_region_ratio)

#     # ── Filter 2: remove nested boxes ─────────────────────────────────────────
#     final = _remove_nested_regions(final, nest_ratio=nest_region_ratio)

#     print(f"  Regions after grouping: {len(final)}  "
#           f"(pass_a={len(line_regions)}  para_v={para_v_px:.1f}px)")
#     return final
"""
region_grouping.py — Group blobs into candidate regions.

Two-pass strategy
-----------------
Pass A (tight)  — connect blobs that are within one line-spacing.
                  Produces small line-level regions.
Pass B (para)   — merge line regions whose vertical gap is below the
                  auto-detected paragraph gap threshold.

Post-processing — split any surviving region that is too wide
                  (column split) or too tall (strip split).
                  Then resolve nested boxes by subtracting child boxes
                  from any parent box that contains them.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _union_find_group(blobs, h_gap, v_gap, min_members=1):
    """Union-Find proximity grouping with path compression + v_gap early-break."""
    sorted_blobs = sorted(blobs, key=lambda b: (b["y1"], b["x1"]))
    n      = len(sorted_blobs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    for i in range(n):
        bi = sorted_blobs[i]
        for j in range(i + 1, n):
            bj = sorted_blobs[j]
            if bj["y1"] - bi["y2"] > v_gap:
                break
            v_dist = max(0, bj["y1"] - bi["y2"])
            h_dist = max(0, max(bi["x1"], bj["x1"]) - min(bi["x2"], bj["x2"]))
            if v_dist <= v_gap and h_dist <= h_gap:
                union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(sorted_blobs[i])

    regions = []
    for members in groups.values():
        if len(members) < min_members:
            continue
        rx1 = min(b["x1"] for b in members)
        ry1 = min(b["y1"] for b in members)
        rx2 = max(b["x2"] for b in members)
        ry2 = max(b["y2"] for b in members)
        rw  = rx2 - rx1 + 1
        rh  = ry2 - ry1 + 1
        box_area = rw * rh
        ink_area = sum(b["area"] for b in members)
        regions.append({
            "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
            "width": rw, "height": rh,
            "blob_count": len(members),
            "density": ink_area / box_area if box_area > 0 else 0.0,
            "blobs": members,
        })
    return regions


def _estimate_para_gap_factor(line_regions, font_size):
    """
    Auto-detect the vertical gap threshold that separates lines within
    a paragraph from gaps between paragraphs/blocks.

    Finds the first significant jump in the sorted inter-line gap list
    at or above font_size, and cuts just below it.
    Falls back to font_size * 2.5 if fewer than 3 gaps are available.
    Hard floor: font_size * 1.1.
    """
    if len(line_regions) < 3:
        return font_size * 2.5

    sorted_lines = sorted(line_regions, key=lambda r: r["y1"])
    gaps = []
    for i in range(len(sorted_lines) - 1):
        gap = sorted_lines[i + 1]["y1"] - sorted_lines[i]["y2"]
        if gap > 0:
            gaps.append(gap)

    if len(gaps) < 3:
        return font_size * 2.5

    gaps.sort()
    n = len(gaps)

    threshold = None
    for i in range(1, n):
        if gaps[i] >= font_size and gaps[i] > gaps[i - 1] * 1.5:
            threshold = gaps[i - 1] + 2
            break

    if threshold is None:
        above = [g for g in gaps if g >= font_size]
        if above:
            threshold = above[0] - 1
        else:
            threshold = font_size * 1.1

    return float(max(threshold, font_size * 1.1))


def _split_region_by_x_gap(group_blobs, font_size, h_gap_factor,
                             min_blobs_per_region, min_region_density):
    """Split a too-wide region into x-axis columns."""
    h_gap       = font_size * h_gap_factor
    sorted_by_x = sorted(group_blobs, key=lambda b: b["center_c"])
    columns, current = [], [sorted_by_x[0]]
    for b in sorted_by_x[1:]:
        if b["x1"] - current[-1]["x2"] > h_gap:
            columns.append(current)
            current = [b]
        else:
            current.append(b)
    columns.append(current)

    result = []
    for col in columns:
        if len(col) < min_blobs_per_region:
            continue
        rx1 = min(b["x1"] for b in col)
        ry1 = min(b["y1"] for b in col)
        rx2 = max(b["x2"] for b in col)
        ry2 = max(b["y2"] for b in col)
        rw  = rx2 - rx1 + 1
        rh  = ry2 - ry1 + 1
        box_area = rw * rh
        density  = sum(b["area"] for b in col) / box_area if box_area > 0 else 0.0
        if density < min_region_density:
            continue
        result.append({
            "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
            "width": rw, "height": rh,
            "blobs": col,
            "blob_count": len(col),
            "density": density,
        })
    return result


def _split_region_by_y_gap(group_blobs, font_size, line_v_factor,
                             min_blobs_per_region, min_region_density):
    """Split a too-tall region into horizontal strips."""
    v_cut  = font_size * line_v_factor * 1.5
    by_y   = sorted(group_blobs, key=lambda b: b["center_r"])
    strips, current = [], [by_y[0]]
    for b in by_y[1:]:
        if b["y1"] - current[-1]["y2"] > v_cut:
            strips.append(current)
            current = [b]
        else:
            current.append(b)
    strips.append(current)

    result = []
    for strip in strips:
        if len(strip) < min_blobs_per_region:
            continue
        rx1 = min(b["x1"] for b in strip)
        ry1 = min(b["y1"] for b in strip)
        rx2 = max(b["x2"] for b in strip)
        ry2 = max(b["y2"] for b in strip)
        rw  = rx2 - rx1 + 1
        rh  = ry2 - ry1 + 1
        box_area = rw * rh
        density  = sum(b["area"] for b in strip) / box_area if box_area > 0 else 0.0
        n_lines  = max(1, rh / font_size)
        if density < min_region_density / (n_lines ** 0.5):
            continue
        result.append({
            "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
            "width": rw, "height": rh,
            "blobs": strip,
            "blob_count": len(strip),
            "density": density,
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Nested box resolution helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _box_area(b):
    return max(0, b["x2"] - b["x1"]) * max(0, b["y2"] - b["y1"])


def _is_contained(inner, outer, threshold=0.85):
    """
    True if inner box is mostly (>= threshold) covered by outer box.
    Both arguments are region dicts with x1/y1/x2/y2 keys.
    """
    ix1, iy1, ix2, iy2 = inner["x1"], inner["y1"], inner["x2"], inner["y2"]
    ox1, oy1, ox2, oy2 = outer["x1"], outer["y1"], outer["x2"], outer["y2"]

    inter_x1 = max(ix1, ox1); inter_y1 = max(iy1, oy1)
    inter_x2 = min(ix2, ox2); inter_y2 = min(iy2, oy2)

    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return False

    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    inner_area = max(1, (ix2 - ix1) * (iy2 - iy1))
    return (inter_area / inner_area) >= threshold


def _subtract_boxes_from_region(region, children, min_area=500):
    """
    Subtract all child bounding boxes from region using recursive 4-strip
    splitting.  Returns a list of remainder region dicts (blobs carried from
    the original region, box coords updated).

    Strip layout when child overlaps remainder rect (rx1,ry1)→(rx2,ry2):

        ┌─────────────────────┐
        │      TOP strip      │  y: ry1 → oy1,  x: rx1 → rx2
        ├──────┬────────┬─────┤
        │ LEFT │ child  │RIGHT│  y: oy1 → oy2
        │      │ (hole) │     │
        ├──────┴────────┴─────┤
        │     BOTTOM strip    │  y: oy2 → ry2,  x: rx1 → rx2
        └─────────────────────┘
    """
    # Work with plain coord tuples internally, convert back to dicts at the end
    remaining = [(region["x1"], region["y1"], region["x2"], region["y2"])]

    for child in children:
        cx1, cy1 = child["x1"], child["y1"]
        cx2, cy2 = child["x2"], child["y2"]
        next_remaining = []

        for (rx1, ry1, rx2, ry2) in remaining:
            # Intersection of this remainder with child
            ox1 = max(rx1, cx1); oy1 = max(ry1, cy1)
            ox2 = min(rx2, cx2); oy2 = min(ry2, cy2)

            if ox1 >= ox2 or oy1 >= oy2:
                # No overlap — keep remainder intact
                next_remaining.append((rx1, ry1, rx2, ry2))
                continue

            # Top strip
            if oy1 > ry1:
                next_remaining.append((rx1, ry1, rx2, oy1))
            # Bottom strip
            if oy2 < ry2:
                next_remaining.append((rx1, oy2, rx2, ry2))
            # Left strip  (middle band only, between oy1 and oy2)
            if ox1 > rx1:
                next_remaining.append((rx1, oy1, ox1, oy2))
            # Right strip (middle band only)
            if ox2 < rx2:
                next_remaining.append((ox2, oy1, rx2, oy2))

        remaining = next_remaining

    # Convert coord tuples back to region dicts, drop slivers
    result = []
    for (x1, y1, x2, y2) in remaining:
        w = x2 - x1
        h = y2 - y1
        if w * h < min_area:
            continue
        result.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "width": w, "height": h,
            # Carry blobs and density from the original parent region so
            # downstream classifiers still have access to them.
            "blob_count": region["blob_count"],
            "density":    region["density"],
            "blobs":      region["blobs"],
        })
    return result


def _resolve_nested_regions(regions, containment_threshold=0.85, min_area=500):
    """
    For every region that contains one or more smaller regions inside it,
    subtract the children from the parent so the returned set is
    non-overlapping.

    Small (child) regions are kept exactly as-is.
    Large (parent) regions are trimmed to the parts not covered by children.

    Parameters
    ----------
    regions               : list[dict]  region dicts with x1/y1/x2/y2 keys
    containment_threshold : float       fraction of child area that must lie
                                        inside parent to count as contained
                                        (default 0.85)
    min_area              : int         pixel² below which remainder rects are
                                        dropped as slivers (default 500)

    Returns
    -------
    list[dict]  — same dict format as input, non-overlapping
    """
    if not regions:
        return regions

    # Sort ascending by area so children come before parents
    by_area = sorted(regions, key=_box_area)
    result  = []

    for i, region in enumerate(by_area):
        # Find all smaller regions that sit inside this one
        children = [
            other
            for j, other in enumerate(by_area)
            if j != i
            and _box_area(other) < _box_area(region)   # strictly smaller
            and _is_contained(other, region, containment_threshold)
        ]

        if not children:
            result.append(region)
        else:
            trimmed = _subtract_boxes_from_region(region, children,
                                                   min_area=min_area)
            result.extend(trimmed)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def group_blobs_into_regions(blobs, font_size,
                              h_gap_factor=2.0,
                              line_v_factor=1.5,
                              para_v_factor=None,
                              min_blobs_per_region=2,
                              max_region_aspect=25.0,
                              max_region_height_factor=20.0,
                              min_region_density=0.02,
                              resolve_nested=True,
                              containment_threshold=0.85,
                              min_remainder_area=500):
    """
    Group blobs into candidate regions using a two-pass strategy, then
    resolve any nested / overlapping boxes so the final output is
    non-overlapping.

    Parameters
    ----------
    blobs                   : list[dict]  from find_all_blobs()
    font_size               : int         estimated body-text height in px
    h_gap_factor            : float       horizontal gap in font_size units (default 2.0)
    line_v_factor           : float       Pass A vertical gap — within-line merge (default 1.5)
    para_v_factor           : float|None  Pass B vertical gap — paragraph merge.
                                          If None, auto-detected from Pass A output.
    min_blobs_per_region    : int         minimum blobs to keep a region (default 2)
    max_region_aspect       : float       width/height above which column-split fires (default 25)
    max_region_height_factor: float       height/font_size above which strip-split fires (default 20)
    min_region_density      : float       ink/box ratio below which region is dropped (default 0.02)
    resolve_nested          : bool        subtract child boxes from parent boxes (default True)
    containment_threshold   : float       fraction of child area inside parent to count as
                                          contained (default 0.85)
    min_remainder_area      : int         pixel² below which remainder rects are dropped (default 500)

    Returns
    -------
    list[dict] — each dict has:
        x1, y1, x2, y2, width, height, blob_count, density, blobs
    """
    if not blobs:
        return []

    h_gap      = font_size * h_gap_factor
    line_v_gap = font_size * line_v_factor

    # ── Pass A: tight grouping — connect blobs within one line-spacing ────────
    line_regions = _union_find_group(
        blobs,
        h_gap=h_gap,
        v_gap=line_v_gap,
        min_members=1
    )

    # ── Auto-detect paragraph gap if not supplied ─────────────────────────────
    if para_v_factor is None:
        para_v_px = _estimate_para_gap_factor(line_regions, font_size)
        # Hard ceiling: never merge more than 4 line-heights apart
        para_v_px = min(para_v_px, font_size * 2.0)
    else:
        para_v_px = font_size * para_v_factor

    # ── Pass B: paragraph grouping — merge adjacent line regions ─────────────
    # Treat each line_region's bounding box as a single "super-blob"
    super_blobs = []
    for lr in line_regions:
        super_blobs.append({
            "x1":      lr["x1"],
            "y1":      lr["y1"],
            "x2":      lr["x2"],
            "y2":      lr["y2"],
            "center_r": (lr["y1"] + lr["y2"]) / 2,
            "center_c": (lr["x1"] + lr["x2"]) / 2,
            "area":    lr["density"] * lr["width"] * lr["height"],
            "_blobs":  lr["blobs"],   # carry original blobs through
        })

    para_regions_raw = _union_find_group(
        super_blobs,
        h_gap=h_gap,
        v_gap=para_v_px,
        min_members=1
    )

    # Rebuild real blob lists from merged super-blobs
    para_regions = []
    for pr in para_regions_raw:
        real_blobs = []
        for sb in pr["blobs"]:
            real_blobs.extend(sb.get("_blobs", [sb]))
        if len(real_blobs) < min_blobs_per_region:
            continue

        rx1 = min(b["x1"] for b in real_blobs)
        ry1 = min(b["y1"] for b in real_blobs)
        rx2 = max(b["x2"] for b in real_blobs)
        ry2 = max(b["y2"] for b in real_blobs)
        rw  = rx2 - rx1 + 1
        rh  = ry2 - ry1 + 1
        box_area = rw * rh
        density  = sum(b["area"] for b in real_blobs) / box_area if box_area > 0 else 0.0

        if density < min_region_density:
            continue

        para_regions.append({
            "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2,
            "width": rw, "height": rh,
            "blob_count": len(real_blobs),
            "density": density,
            "blobs": real_blobs,
        })

    # ── Post-processing: split oversized regions ──────────────────────────────
    final = []
    for region in para_regions:
        rw = region["width"]
        rh = region["height"]
        ar = rw / rh if rh > 0 else 0

        # Too wide → column split
        if ar > max_region_aspect:
            parts = _split_region_by_x_gap(
                region["blobs"], font_size, h_gap_factor,
                min_blobs_per_region, min_region_density
            )
            final.extend(parts)
            continue

        # Too tall → strip split
        if rh > font_size * max_region_height_factor:
            parts = _split_region_by_y_gap(
                region["blobs"], font_size, line_v_factor,
                min_blobs_per_region, min_region_density
            )
            final.extend(parts)
            continue

        final.append(region)

    # ── Nested box resolution ─────────────────────────────────────────────────
    if resolve_nested and len(final) > 1:
        before = len(final)
        final  = _resolve_nested_regions(
            final,
            containment_threshold=containment_threshold,
            min_area=min_remainder_area,
        )
        after = len(final)
        print(f"  Nested resolution: {before} → {after} regions "
              f"(containment_threshold={containment_threshold})")

    print(f"  Regions after grouping: {len(final)}  "
          f"(pass_a={len(line_regions)}  para_v={para_v_px:.1f}px)")
    return final