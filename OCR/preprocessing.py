"""
preprocessing.py
================
Stages 1 & 2 of the CCA pipeline.

Changes from original
---------------------
• Added auto skew detection and correction (OpenCV when available,
  pure-Python fallback otherwise). Everything else is unchanged.

Pure Python — Pillow used ONLY for image I/O.
OpenCV/NumPy used ONLY for skew detection + rotation (optional).
"""

from PIL import Image
import math

try:
    import cv2
    import numpy as np
    _CV2 = True
except ImportError:
    _CV2 = False


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Mode normalisation + loading
# ═══════════════════════════════════════════════════════════════════════════════

def _load_normalised(path):
    """Open any PIL-readable image and return a plain RGB PIL Image."""
    img  = Image.open(path)
    mode = img.mode

    if mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if mode == "RGBA":
            bg.paste(img, mask=img.split()[3])
        else:
            bg.paste(img.convert("RGB"))
        img = bg
    elif mode == "P":
        img = img.convert("RGBA").convert("RGB") \
            if "transparency" in img.info else img.convert("RGB")
    elif mode == "1":
        img = img.convert("L").convert("RGB")
    elif mode == "L":
        img = img.convert("RGB")
    elif mode != "RGB":
        img = img.convert("RGB")

    return img


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Grayscale conversion  (BT.601)
# ═══════════════════════════════════════════════════════════════════════════════

def _to_grayscale(img):
    """Y = 0.299R + 0.587G + 0.114B → 2-D list[list[int]] (0-255)."""
    w, h   = img.size
    pixels = list(img.getdata())
    gray   = []
    for r in range(h):
        row = []
        for c in range(w):
            R, G, B  = pixels[r * w + c]
            row.append(int(0.299 * R + 0.587 * G + 0.114 * B))
        gray.append(row)
    return gray


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Contrast normalisation  (histogram stretch)
# ═══════════════════════════════════════════════════════════════════════════════

def _needs_stretch(gray, low_contrast_threshold=120):
    h, w = len(gray), len(gray[0])
    flat = sorted(gray[r][c] for r in range(h) for c in range(w))
    n    = len(flat)
    return (flat[int(0.98 * n)] - flat[int(0.02 * n)]) < low_contrast_threshold


def _stretch_contrast(gray):
    h, w  = len(gray), len(gray[0])
    flat  = sorted(gray[r][c] for r in range(h) for c in range(w))
    n     = len(flat)
    lo    = flat[int(0.02 * n)]
    hi    = flat[int(0.98 * n)]
    if hi == lo:
        return [row[:] for row in gray]
    scale = 255.0 / (hi - lo)
    return [[max(0, min(255, int((gray[r][c] - lo) * scale)))
             for c in range(w)] for r in range(h)]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Gaussian blur  (separable 1-D passes)
# ═══════════════════════════════════════════════════════════════════════════════

def _gaussian_kernel_1d(radius):
    if radius == 0:
        return [1.0]
    sigma  = max(radius / 2.0, 0.5)
    kernel = [math.exp(-((i - radius) ** 2) / (2 * sigma ** 2))
              for i in range(2 * radius + 1)]
    total  = sum(kernel)
    return [k / total for k in kernel]


def _convolve_h(image, kernel):
    h, w   = len(image), len(image[0])
    radius = len(kernel) // 2
    out    = []
    for r in range(h):
        row = []
        for c in range(w):
            acc = sum(image[r][min(max(c + ki - radius, 0), w - 1)] * kv
                      for ki, kv in enumerate(kernel))
            row.append(acc)
        out.append(row)
    return out


def _convolve_v(image, kernel):
    h, w   = len(image), len(image[0])
    radius = len(kernel) // 2
    out    = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            out[r][c] = sum(image[min(max(r + ki - radius, 0), h - 1)][c] * kv
                            for ki, kv in enumerate(kernel))
    return out


def _gaussian_blur(gray, radius):
    if radius == 0:
        return gray
    kernel  = _gaussian_kernel_1d(radius)
    tmp     = _convolve_h(gray, kernel)
    blurred = _convolve_v(tmp, kernel)
    h, w    = len(blurred), len(blurred[0])
    return [[int(round(blurred[r][c])) for c in range(w)] for r in range(h)]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5a — Global Otsu binarization  (exported for standalone use)
# ═══════════════════════════════════════════════════════════════════════════════

def otsu_binarize(gray):
    flat = [p for row in gray for p in row]
    hist = [0] * 256
    for v in flat:
        hist[v] += 1

    total     = len(flat)
    total_sum = sum(i * hist[i] for i in range(256))
    sum_bg = weight_bg = 0
    best_var = threshold = 0

    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg   += t * hist[t]
        mean_bg   = sum_bg / weight_bg
        mean_fg   = (total_sum - sum_bg) / weight_fg
        var       = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var > best_var:
            best_var  = var
            threshold = t

    threshold -= 5
    h, w = len(gray), len(gray[0])
    binary = [[1 if gray[r][c] < threshold else 0 for c in range(w)]
              for r in range(h)]
    return binary, threshold


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5b — Adaptive tiled Otsu binarization  (default)
# ═══════════════════════════════════════════════════════════════════════════════

def _otsu_on_patch(flat_pixels, clamp_threshold=None):
    total = len(flat_pixels)
    if total == 0:
        return 128
    hist = [0] * 256
    for v in flat_pixels:
        hist[v] += 1
    best_t = best_var = 0
    weight_bg = sum_bg = 0
    total_sum = sum(i * hist[i] for i in range(256))
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (total_sum - sum_bg) / weight_fg
        var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var > best_var:
            best_var = var
            best_t   = t

    if clamp_threshold is not None:
        dark_pixels = sum(hist[v] for v in range(128))
        ink_ratio   = dark_pixels / total
        if ink_ratio < 0.03:
            best_t = min(best_t, clamp_threshold)

    return best_t


def _adaptive_binarize(gray, tile_size=128):
    h, w = len(gray), len(gray[0])

    flat_all      = [gray[r][c] for r in range(h) for c in range(w)]
    global_thresh = _otsu_on_patch(flat_all)

    n_rows = max(1, (h + tile_size - 1) // tile_size)
    n_cols = max(1, (w + tile_size - 1) // tile_size)
    tile_thresh = []
    for tr in range(n_rows):
        row_t = []
        r0, r1 = tr * tile_size, min((tr + 1) * tile_size, h)
        for tc in range(n_cols):
            c0, c1 = tc * tile_size, min((tc + 1) * tile_size, w)
            patch  = [gray[r][c] for r in range(r0, r1) for c in range(c0, c1)]
            row_t.append(_otsu_on_patch(patch, clamp_threshold=global_thresh))
        tile_thresh.append(row_t)

    THIN_STROKE_BIAS = 5
    binary = []
    for r in range(h):
        row   = []
        tf    = (r + 0.5) / tile_size - 0.5
        tr0   = max(0, min(n_rows - 2, int(math.floor(tf))))
        tr1   = min(tr0 + 1, n_rows - 1)
        dr    = tf - tr0
        for c in range(w):
            cf  = (c + 0.5) / tile_size - 0.5
            tc0 = max(0, min(n_cols - 2, int(math.floor(cf))))
            tc1 = min(tc0 + 1, n_cols - 1)
            dc  = cf - tc0
            t00 = tile_thresh[tr0][tc0]
            t01 = tile_thresh[tr0][tc1]
            t10 = tile_thresh[tr1][tc0]
            t11 = tile_thresh[tr1][tc1]
            thr = (t00 * (1-dr) * (1-dc) + t01 * (1-dr) * dc +
                   t10 * dr     * (1-dc) + t11 * dr     * dc)
            row.append(1 if gray[r][c] < thr + THIN_STROKE_BIAS else 0)
        binary.append(row)

    return binary, global_thresh


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Morphological operations
# ═══════════════════════════════════════════════════════════════════════════════

def _erode(binary):
    h, w = len(binary), len(binary[0])
    out  = [[0] * w for _ in range(h)]
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if (binary[r][c] and
                    binary[r-1][c-1] and binary[r-1][c] and binary[r-1][c+1] and
                    binary[r  ][c-1] and                    binary[r  ][c+1] and
                    binary[r+1][c-1] and binary[r+1][c] and binary[r+1][c+1]):
                out[r][c] = 1
    return out


def _dilate(binary):
    h, w = len(binary), len(binary[0])
    out  = [[0] * w for _ in range(h)]
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if (binary[r][c] or
                    binary[r-1][c-1] or binary[r-1][c] or binary[r-1][c+1] or
                    binary[r  ][c-1] or                   binary[r  ][c+1] or
                    binary[r+1][c-1] or binary[r+1][c] or binary[r+1][c+1]):
                out[r][c] = 1
    return out


def _morphological_opening(binary):
    return _dilate(_erode(binary))


def _morphological_closing(binary):
    return _erode(_dilate(binary))


# ═══════════════════════════════════════════════════════════════════════════════
# SKEW — detect and correct  ← NEW
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_skew_angle(gray):
    """
    Estimate document skew angle in degrees.
    Returns 0.0 when skew is negligible (< 0.3°).

    OpenCV path : HoughLinesP on a horizontally-dilated binary image.
    Fallback    : horizontal-projection variance sweep over ±5°.
    """
    h, w = len(gray), len(gray[0])

    if _CV2:
        arr   = np.array(gray, dtype=np.uint8)
        _, bw = cv2.threshold(arr, 0, 255,
                               cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        dilated = cv2.dilate(bw, kernel)
        lines   = cv2.HoughLinesP(
            dilated, 1, math.pi / 180,
            threshold=max(50, w // 10),
            minLineLength=max(50, w // 8),
            maxLineGap=20,
        )
        if lines is None or len(lines) == 0:
            return 0.0
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(angle) < 30:      # near-horizontal lines only
                angles.append(angle)
        if not angles:
            return 0.0
        angles.sort()
        median = angles[len(angles) // 2]
        return median if abs(median) >= 0.3 else 0.0

    else:
        # Pure-Python projection variance over -5° … +5°
        best_angle, best_score = 0.0, -1.0
        for deg_10 in range(-50, 51):
            angle = deg_10 * 0.1
            rad   = math.radians(angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            row_sums = [0] * h
            for r in range(0, h, 4):
                for c in range(0, w, 4):
                    nr = int(r * cos_a + c * sin_a)
                    if 0 <= nr < h:
                        row_sums[nr] += 1 if gray[r][c] < 128 else 0
            mean  = sum(row_sums) / h
            score = sum((v - mean) ** 2 for v in row_sums) / h
            if score > best_score:
                best_score = score
                best_angle = angle
        return best_angle if abs(best_angle) >= 0.3 else 0.0


def _deskew(pil_img, angle_deg):
    """Rotate PIL image by -angle_deg to correct skew; white fill."""
    if _CV2:
        arr    = np.array(pil_img)
        h, w   = arr.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        M      = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
        cos_a  = abs(M[0, 0]);  sin_a = abs(M[0, 1])
        new_w  = int(h * sin_a + w * cos_a)
        new_h  = int(h * cos_a + w * sin_a)
        M[0, 2] += (new_w / 2) - cx
        M[1, 2] += (new_h / 2) - cy
        rotated = cv2.warpAffine(
            arr, M, (new_w, new_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
        return Image.fromarray(rotated)
    else:
        return pil_img.rotate(-angle_deg, expand=True,
                               fillcolor=(255, 255, 255))


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS — tile size + downscale  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

def _auto_tile_size(width, height):
    estimated_font_px = height / 74.0
    raw_tile = int(estimated_font_px * 3)
    return max(32, min(128, raw_tile))


def _resize_if_needed(img, max_dim):
    if max_dim is None:
        return img, False
    w, h = img.size
    if max(w, h) <= max_dim:
        return img, False
    scale = max_dim / max(w, h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return img.resize((new_w, new_h), Image.LANCZOS), True


def _check_and_fix_polarity(binary):
    """
    If more than 60% of pixels are ink (=1), the image has a dark background.
    Invert so that ink always = minority class (actual glyphs).
    """
    h, w = len(binary), len(binary[0])
    total = h * w
    ink_count = sum(binary[r][c] for r in range(h) for c in range(w))
    ink_ratio = ink_count / total
    if ink_ratio > 0.60:
        print(f"      polarity inverted (ink_ratio={ink_ratio:.2%})")
        return [[1 - binary[r][c] for c in range(w)] for r in range(h)], True
    return binary, False

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def preprocess(path, gaussian_noise=False, negative_noise=False,
               unconnected=False, fix_skew=False, tile_size=None, max_dim=2000):
    """
    Run the full preprocessing pipeline on a single image.

    Parameters
    ----------
    path            : str        path to any PIL-readable image
    gaussian_noise  : bool       apply Gaussian blur before binarization
    negative_noise  : bool       apply morphological opening after binarization
    unconnected     : bool       apply morphological closing after binarization
    fix_skew        : bool       auto-detect and correct skew (default True)
    tile_size       : int|None   adaptive Otsu tile size; None = auto
    max_dim         : int|None   clamp longest dimension (default 2000)

    Returns
    -------
    dict:
        gray             — 2-D list[list[int]]
        binary           — 2-D list[list[int]]   (1=ink, 0=background)
        width            — int
        height           — int
        global_threshold — int
        was_stretched    — bool
        skew_angle       — float  degrees corrected (0.0 = no correction)
    """
    # Step 1: Load + optional downscale
    img, _ = _resize_if_needed(_load_normalised(path), max_dim)

    # Step 2: Skew correction  ← NEW
    skew_angle = 0.0
    if fix_skew:
        gray_for_skew = _to_grayscale(img)
        skew_angle    = _detect_skew_angle(gray_for_skew)
        if abs(skew_angle) >= 0.3:
            print(f"      skew detected: {skew_angle:.2f}° → correcting")
            img = _deskew(img, skew_angle)
        else:
            print("      skew: negligible")

    # Step 3: Grayscale
    gray   = _to_grayscale(img)
    height = len(gray)
    width  = len(gray[0])

    # Step 4: Contrast normalisation
    was_stretched = False
    if _needs_stretch(gray):
        gray          = _stretch_contrast(gray)
        was_stretched = True

    # Step 5: Optional Gaussian blur
    if gaussian_noise:
        blur_radius = 2 if was_stretched else 1
        gray        = _gaussian_blur(gray, blur_radius)

    # Step 6: Adaptive tiled Otsu binarization
    effective_tile = tile_size if tile_size is not None else _auto_tile_size(width, height)
    print(f"      tile_size={effective_tile}px  "
          f"({'auto' if tile_size is None else 'caller-set'})")
    binary, global_threshold = _adaptive_binarize(gray, tile_size=effective_tile)
    binary, _ = _check_and_fix_polarity(binary)

    # Step 7: Optional morphological cleanup
    if negative_noise:
        binary = _morphological_opening(binary)
    if unconnected:
        binary = _morphological_closing(binary)

    return {
        "gray":             gray,
        "binary":           binary,
        "width":            width,
        "height":           height,
        "global_threshold": global_threshold,
        "was_stretched":    was_stretched,
        "skew_angle":       skew_angle,
    }