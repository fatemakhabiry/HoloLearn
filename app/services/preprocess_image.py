"""
preprocess_image.py - Image Preprocessing Pipeline for LongCat-Video Avatar
=============================================================================
Run this script BEFORE run_chunked_avatar.py to validate and normalize your
input image. It applies the following corrections in order:

  Step 0  Load & validate (convert to RGB)
  Step 1  Face detection (OpenCV Haar: frontal → profile → flipped profile)
  Step 2  Background analysis (sample border band, classify BG type)
  Step 3  Conditional BG removal (rembg + birefnet-portrait → RGBA output)
  Step 4  Square framing: subject center-bottom on 1080×1080 canvas
  Step 5  Final validation (re-run face detection, warn if off-center)
  Step 6  Save RGBA PNG + print quality report

Usage examples:
  # Basic (auto-everything, 1080×1080 output, black background)
  python preprocess_image.py --input photo.jpg

  # Transparent background canvas
  python preprocess_image.py --input photo.jpg --bg-color transparent

  # White background canvas
  python preprocess_image.py --input photo.jpg --bg-color white

  # Enable PyMatting edge refinement (slower, better hair)
  python preprocess_image.py --input photo.jpg --alpha-matting

  # Alternate model
  python preprocess_image.py --input photo.jpg --bg-model isnet-general-use

  # Always remove BG, then run pipeline
  python preprocess_image.py --input photo.jpg --force-bg-removal
"""

import argparse
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image


# ══════════════════════════════════════════════════════════════════════════════
# ImageReport dataclass
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImageReport:
    input_path: str = ""
    output_path: str = ""

    # Step 0
    original_size: Tuple[int, int] = (0, 0)   # (w, h)
    mode_converted: bool = False

    # Step 1 - initial face detection
    face_found: bool = False
    face_rect: Optional[dict] = None           # {x, y, w, h, cx, cy}

    # Step 2 - background
    bg_type: str = "UNKNOWN"                   # CLEAN_DARK / CLEAN_UNIFORM / COMPLEX

    # Step 3 - bg removal
    bg_removal_applied: bool = False
    bg_removal_skipped_reason: str = ""
    bg_model: str = "birefnet-portrait"

    # Step 4 - framing
    framing_action: str = ""                   # "scale_up" | "scale_down" | "fit" | "skipped"
    framing_scale: float = 1.0
    pre_frame_size: Tuple[int, int] = (0, 0)
    post_frame_size: Tuple[int, int] = (0, 0)

    # Step 5 - final validation
    final_face_found: bool = False
    final_face_centered: bool = False
    final_size: Tuple[int, int] = (0, 0)

    # Warnings
    warnings: list = field(default_factory=list)

    def print_report(self):
        sep = "=" * 60
        print(sep)
        print("  PREPROCESSING REPORT")
        print(sep)
        print(f"  Input  : {self.input_path}")
        print(f"  Output : {self.output_path}")
        print(f"  Original size : {self.original_size[0]}x{self.original_size[1]}")
        if self.mode_converted:
            print("  Mode   : converted to RGB")

        print()
        print(f"  [Step 1] Face: {'FOUND' if self.face_found else 'NOT FOUND'}", end="")
        if self.face_found and self.face_rect:
            r = self.face_rect
            print(f"  @ ({r['cx']},{r['cy']})  size={r['w']}x{r['h']}", end="")
        print()

        print(f"  [Step 2] Background: {self.bg_type}")
        if self.bg_removal_applied:
            print(f"  [Step 3] BG Removal: APPLIED ({self.bg_model})")
        else:
            print(f"  [Step 3] BG Removal: SKIPPED ({self.bg_removal_skipped_reason})")

        print(f"  [Step 4] Framing: {self.framing_action}  "
              f"{self.pre_frame_size[0]}x{self.pre_frame_size[1]} -> "
              f"{self.post_frame_size[0]}x{self.post_frame_size[1]}")

        centered_str = "centered" if self.final_face_centered else "OFF-CENTER"
        print(f"  [Step 5] Final face: {'FOUND' if self.final_face_found else 'NOT FOUND'}"
              + (f", {centered_str}" if self.final_face_found else ""))
        print(f"  [Step 6] Final size: {self.final_size[0]}x{self.final_size[1]}")

        if self.warnings:
            print()
            print("  WARNINGS:")
            for w in self.warnings:
                print(f"    ! {w}")
        print(sep)


# ══════════════════════════════════════════════════════════════════════════════
# BackgroundAnalyzer
# ══════════════════════════════════════════════════════════════════════════════

class BackgroundAnalyzer:
    """Classify the background by sampling a border band around the image."""

    def analyze(self, img_rgb: np.ndarray) -> str:
        """
        Returns one of: 'CLEAN_DARK', 'CLEAN_UNIFORM', 'COMPLEX'
        img_rgb: HxWx3 uint8 numpy array
        """
        h, w = img_rgb.shape[:2]
        band = max(15, int(min(h, w) * 0.05))

        top    = img_rgb[:band, :, :]
        bottom = img_rgb[h - band:, :, :]
        left   = img_rgb[band:h - band, :band, :]
        right  = img_rgb[band:h - band, w - band:, :]

        border = np.concatenate(
            [top.reshape(-1, 3), bottom.reshape(-1, 3),
             left.reshape(-1, 3), right.reshape(-1, 3)],
            axis=0
        ).astype(np.float32)

        mean_brightness = border.mean()
        dark_pct = (border.max(axis=1) < 60).mean()
        std = border.std()

        if dark_pct > 0.80 and mean_brightness < 60:
            return "CLEAN_DARK"
        if std < 25:
            return "CLEAN_UNIFORM"
        return "COMPLEX"


# ══════════════════════════════════════════════════════════════════════════════
# BackgroundRemover
# ══════════════════════════════════════════════════════════════════════════════

class BackgroundRemover:
    """Portrait matting via rembg + BiRefNet. Returns full RGBA — no black compositing."""

    def __init__(self, model_name: str = "birefnet-portrait", bg_device: str = "cpu"):
        from rembg import new_session
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if bg_device == "cuda"
            else ["CPUExecutionProvider"]
        )
        self.session = new_session(model_name, providers=providers)
        print(f"  [BG] Loaded rembg '{model_name}' ({providers[0]})")

    def remove(
        self,
        img_rgb: np.ndarray,
        alpha_matting: bool = False,
        alpha_matting_fg: int = 240,
        alpha_matting_bg: int = 20,
        alpha_matting_erode: int = 15,
        post_process: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns (rgba HxWx4 uint8, hard_mask HxW uint8).
        rgba:      full-resolution RGBA — alpha is the BiRefNet matte,
                   no premultiplication, no black background.
        hard_mask: binary uint8 (alpha > 20) used for bbox detection.
        """
        from rembg import remove as rembg_remove

        rgba_pil = rembg_remove(
            Image.fromarray(img_rgb),
            session=self.session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_fg,
            alpha_matting_background_threshold=alpha_matting_bg,
            alpha_matting_erode_size=alpha_matting_erode,
        )
        rgba = np.array(rgba_pil)                          # HxWx4

        if post_process:
            alpha = rgba[:, :, 3]
            kernel = np.ones((3, 3), np.uint8)
            # MORPH_CLOSE: fills tiny holes (e.g. inside glasses, between fingers)
            alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
            rgba[:, :, 3] = alpha

        hard_mask = (rgba[:, :, 3] > 20).astype(np.uint8)
        return rgba, hard_mask

    def cleanup(self):
        """No-op: ONNX Runtime manages its own memory."""
        pass


# ══════════════════════════════════════════════════════════════════════════════
# FaceDetector
# ══════════════════════════════════════════════════════════════════════════════

class FaceDetector:
    """OpenCV Haar cascade: frontal → profile → flipped profile fallback."""

    def __init__(self):
        cascade_dir = Path(cv2.data.haarcascades)
        frontal_path = str(cascade_dir / "haarcascade_frontalface_default.xml")
        profile_path = str(cascade_dir / "haarcascade_profileface.xml")

        self.frontal = cv2.CascadeClassifier(frontal_path)
        self.profile = cv2.CascadeClassifier(profile_path)

        if self.frontal.empty():
            warnings.warn("Could not load frontal face cascade.")
        if self.profile.empty():
            warnings.warn("Could not load profile face cascade.")

    def detect(self, img_rgb: np.ndarray) -> Optional[dict]:
        """
        Accepts RGB or RGBA (alpha channel is ignored).
        Returns dict {x, y, w, h, cx, cy} or None.
        """
        rgb = img_rgb[:, :, :3] if img_rgb.ndim == 3 and img_rgb.shape[2] == 4 else img_rgb
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray_eq = cv2.equalizeHist(gray)

        faces = self._run_cascade(self.frontal, gray_eq)
        if len(faces) == 0:
            faces = self._run_cascade(self.profile, gray_eq)
        if len(faces) == 0:
            flipped = cv2.flip(gray_eq, 1)
            flipped_faces = self._run_cascade(self.profile, flipped)
            if len(flipped_faces) > 0:
                w_img = img_rgb.shape[1]
                mirrored = []
                for (fx, fy, fw, fh) in flipped_faces:
                    mirrored.append((w_img - fx - fw, fy, fw, fh))
                faces = mirrored

        if len(faces) == 0:
            return None

        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        return {
            "x": int(x), "y": int(y),
            "w": int(fw), "h": int(fh),
            "cx": int(x + fw // 2),
            "cy": int(y + fh // 2),
        }

    def _run_cascade(self, cascade, gray: np.ndarray):
        if cascade.empty():
            return []
        detected = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30),
        )
        return detected if len(detected) > 0 else []


# ══════════════════════════════════════════════════════════════════════════════
# SquareFramer
# ══════════════════════════════════════════════════════════════════════════════

class SquareFramer:
    """
    Place the subject on a square canvas:
      - horizontally centered, with edge_pad pixels on each side
      - bottom-anchored with edge_pad pixels from canvas bottom
      - scales UP small subjects to fill available width, DOWN if oversized
    Input and output are RGBA (HxWx4 uint8).
    """

    def frame(
        self,
        rgba: np.ndarray,
        canvas_size: int = 1080,
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
        edge_pad: int = 55,
    ) -> Tuple[np.ndarray, str]:
        """
        Returns (canvas HxWx4, action_str).
        action: "scale_up" | "scale_down" | "fit"
        """
        h, w = rgba.shape[:2]
        alpha = rgba[:, :, 3]

        # ── A: tight subject bbox from alpha ──────────────────────────────
        pts = cv2.findNonZero((alpha > 20).astype(np.uint8))
        if pts is not None:
            bx, by, bw, bh = cv2.boundingRect(pts)
        else:
            bx, by, bw, bh = 0, 0, w, h
        crop = rgba[by:by + bh, bx:bx + bw]

        # ── B: compute scale to fill available space ───────────────────────
        # Available width:  canvas_size - 2*edge_pad  (equal left/right gaps)
        # Available height: canvas_size - edge_pad     (bottom gap; top can reach 0)
        avail_w = canvas_size - 2 * edge_pad   # e.g. 1080 - 110 = 970
        avail_h = canvas_size                   # full height; top absorbs leftover space

        scale = avail_w / bw               # try to fill width first
        if bh * scale > avail_h:           # would exceed height budget?
            scale = avail_h / bh           # fall back to height-constrained scale

        placed_w = max(1, int(bw * scale))
        placed_h = max(1, int(bh * scale))

        # ── C: resize with best interpolation ─────────────────────────────
        if abs(scale - 1.0) > 0.01:
            interp = cv2.INTER_LANCZOS4 if scale > 1.0 else cv2.INTER_AREA
            crop = cv2.resize(crop, (placed_w, placed_h), interpolation=interp)

        # ── D: center-bottom placement with alpha compositing ─────────────
        canvas = np.full((canvas_size, canvas_size, 4), bg_color, dtype=np.uint8)
        x_off = (canvas_size - placed_w) // 2   # centered horizontally; sides = edge_pad
        y_off = canvas_size - placed_h           # bottom flush with canvas edge

        # Alpha-composite crop "over" canvas so transparent subject pixels
        # reveal the bg_color rather than overwriting it with alpha=0.
        src = crop.astype(np.float32)
        dst = canvas[y_off:y_off + placed_h, x_off:x_off + placed_w].astype(np.float32)
        src_a = src[:, :, 3:4] / 255.0
        dst_a = dst[:, :, 3:4] / 255.0
        out_a = src_a + dst_a * (1.0 - src_a)
        out_rgb = np.where(
            out_a > 0,
            (src[:, :, :3] * src_a + dst[:, :, :3] * dst_a * (1.0 - src_a))
            / np.maximum(out_a, 1e-6),
            0.0,
        )
        composited = np.concatenate(
            [out_rgb, out_a * 255.0], axis=2
        ).clip(0, 255).astype(np.uint8)
        canvas[y_off:y_off + placed_h, x_off:x_off + placed_w] = composited

        if scale > 1.01:
            action = "scale_up"
        elif scale < 0.99:
            action = "scale_down"
        else:
            action = "fit"
        return canvas, action


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def parse_bg_color(color_str: str) -> Tuple[int, int, int, int]:
    """Parse --bg-color string to RGBA tuple."""
    s = color_str.strip().lower()
    if s == "transparent":
        return (0, 0, 0, 0)
    if s == "white":
        return (255, 255, 255, 255)
    if s == "black":
        return (0, 0, 0, 255)
    if s.startswith("#"):
        h = s.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b, 255)
    raise ValueError(f"Unknown --bg-color value: '{color_str}'. "
                     "Use: transparent, white, black, or #RRGGBB")


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ══════════════════════════════════════════════════════════════════════════════

def preprocess_image(args) -> ImageReport:
    report = ImageReport()
    report.input_path = str(args.input)

    input_path = Path(args.input)
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = input_path.with_name(input_path.stem + "_preprocessed.png")
    report.output_path = str(out_path)

    bg_color = parse_bg_color(args.bg_color)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 0 - Load & validate (always work in RGB for BG analysis + removal)
    # ─────────────────────────────────────────────────────────────────────────
    print("[Step 0] Loading image...")
    pil_img = Image.open(str(input_path))
    original_mode = pil_img.mode
    if original_mode != "RGB":
        pil_img = pil_img.convert("RGB")
        report.mode_converted = True
        print(f"  Converted {original_mode} -> RGB")

    img_rgb = np.array(pil_img)
    h, w = img_rgb.shape[:2]
    report.original_size = (w, h)
    print(f"  Size: {w}x{h}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1 - Face detection (initial, on RGB)
    # ─────────────────────────────────────────────────────────────────────────
    if not args.skip_face_detection:
        print("[Step 1] Detecting face...")
        detector = FaceDetector()
        face = detector.detect(img_rgb)
        if face:
            report.face_found = True
            report.face_rect = face
            print(f"  Face found: center=({face['cx']},{face['cy']}), "
                  f"size={face['w']}x{face['h']}")
        else:
            print("  Face NOT found")
            report.warnings.append("No face detected in source image")
    else:
        face = None
        print("[Step 1] Skipped (--skip-face-detection)")

    if args.save_debug and face:
        debug_img = img_rgb.copy()
        cv2.rectangle(
            debug_img,
            (face["x"], face["y"]),
            (face["x"] + face["w"], face["y"] + face["h"]),
            (0, 255, 0), 3,
        )
        debug_path = out_path.with_name(out_path.stem + "_debug_face.jpg")
        Image.fromarray(debug_img).save(str(debug_path))
        print(f"  Debug face saved: {debug_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2 - Background analysis
    # ─────────────────────────────────────────────────────────────────────────
    print("[Step 2] Analyzing background...")
    analyzer = BackgroundAnalyzer()
    bg_type = analyzer.analyze(img_rgb)
    report.bg_type = bg_type
    print(f"  Background: {bg_type}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3 - Conditional background removal → RGBA
    # ─────────────────────────────────────────────────────────────────────────
    do_removal = False
    skip_reason = ""

    if args.skip_bg_removal:
        skip_reason = "--skip-bg-removal flag set"
    elif args.force_bg_removal:
        do_removal = True
    elif bg_type == "CLEAN_DARK":
        skip_reason = "CLEAN_DARK background - no removal needed"
    else:
        do_removal = True

    if do_removal:
        print(f"[Step 3] Removing background (rembg/{args.bg_model})...")
        remover = BackgroundRemover(model_name=args.bg_model, bg_device=args.bg_device)
        img_rgba, person_mask = remover.remove(
            img_rgb,
            alpha_matting=args.alpha_matting,
            alpha_matting_fg=args.alpha_matting_fg,
            alpha_matting_bg=args.alpha_matting_bg,
            alpha_matting_erode=args.alpha_matting_erode,
            post_process=not args.no_post_process,
        )
        remover.cleanup()
        report.bg_removal_applied = True
        report.bg_model = args.bg_model
        if args.save_debug:
            debug_path = out_path.with_name(out_path.stem + "_debug_bg.png")
            Image.fromarray(img_rgba).save(str(debug_path))
            print(f"  Debug BG saved: {debug_path}")
    else:
        # No BG removal: wrap RGB as opaque RGBA
        img_rgba = np.dstack([img_rgb, np.full((h, w), 255, dtype=np.uint8)])
        person_mask = None
        report.bg_removal_skipped_reason = skip_reason
        print(f"[Step 3] BG removal skipped: {skip_reason}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4 - Square framing: center-bottom, 1080×1080
    # ─────────────────────────────────────────────────────────────────────────
    if args.skip_reframe:
        pre_h, pre_w = img_rgba.shape[:2]
        report.pre_frame_size = (pre_w, pre_h)
        report.post_frame_size = (pre_w, pre_h)
        report.framing_action = "skipped"
        print("[Step 4] Framing skipped (--skip-reframe)")
    else:
        print(f"[Step 4] Framing to {args.canvas_size}×{args.canvas_size} "
              f"(center-bottom, bg={args.bg_color})...")
        framer = SquareFramer()
        pre_h, pre_w = img_rgba.shape[:2]
        report.pre_frame_size = (pre_w, pre_h)

        img_rgba, action = framer.frame(
            img_rgba,
            canvas_size=args.canvas_size,
            bg_color=bg_color,
            edge_pad=args.edge_pad,
        )
        post_h, post_w = img_rgba.shape[:2]
        report.post_frame_size = (post_w, post_h)
        report.framing_action = action
        print(f"  {action}: {pre_w}x{pre_h} -> {post_w}x{post_h}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5 - Final validation (face detect on RGBA)
    # ─────────────────────────────────────────────────────────────────────────
    print("[Step 5] Final validation...")
    fh, fw = img_rgba.shape[:2]
    report.final_size = (fw, fh)

    if not args.skip_face_detection:
        final_face = detector.detect(img_rgba)
        if final_face:
            report.final_face_found = True
            cx, cy = final_face["cx"], final_face["cy"]
            cx_frac = cx / fw
            cy_frac = cy / fh
            centered = (0.30 <= cx_frac <= 0.70) and (0.05 <= cy_frac <= 0.80)
            report.final_face_centered = centered
            if not centered:
                report.warnings.append(
                    f"Final face appears off-centre: cx={cx_frac:.2f}, cy={cy_frac:.2f}"
                )
                print(f"  WARNING: face off-centre (cx={cx_frac:.2f}, cy={cy_frac:.2f})")
            else:
                print(f"  Face centered OK (cx={cx_frac:.2f}, cy={cy_frac:.2f})")
        else:
            report.warnings.append("Final face detection failed - check output manually")
            print("  WARNING: face not detected in final image")
    else:
        print("  Skipped (--skip-face-detection)")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6 - Save RGBA PNG
    # ─────────────────────────────────────────────────────────────────────────
    print(f"[Step 6] Saving -> {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img_rgba).save(str(out_path), format="PNG")
    print(f"  Saved: {out_path}  ({fw}x{fh})  RGBA")

    return report


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Preprocess an image for LongCat-Video Avatar pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Path to input image (JPG/PNG/etc.)")
    parser.add_argument("--output", "-o", default=None,
                        help="Path for output PNG (default: <input>_preprocessed.png)")

    bg_group = parser.add_mutually_exclusive_group()
    bg_group.add_argument("--skip-bg-removal", action="store_true",
                          help="Never run background removal")
    bg_group.add_argument("--force-bg-removal", action="store_true",
                          help="Always run background removal (even on CLEAN_DARK)")

    parser.add_argument("--bg-model", default="birefnet-portrait",
                        help="rembg model name (default: birefnet-portrait; "
                             "alt: isnet-general-use, u2net_human_seg)")
    parser.add_argument("--bg-device", default="cuda", choices=["cuda", "cpu"],
                        help="ONNX provider hint for rembg (default: cuda)")
    parser.add_argument("--alpha-matting", action="store_true",
                        help="Enable PyMatting edge refinement after BiRefNet "
                             "(slower, improves fine hair/fur detail)")
    parser.add_argument("--alpha-matting-fg", type=int, default=240,
                        help="PyMatting foreground threshold for trimap (0-255, "
                             "default: 240)")
    parser.add_argument("--alpha-matting-bg", type=int, default=20,
                        help="PyMatting background threshold for trimap (0-255, "
                             "default: 20)")
    parser.add_argument("--alpha-matting-erode", type=int, default=15,
                        help="PyMatting trimap erosion size in pixels (default: 15)")
    parser.add_argument("--no-post-process", action="store_true",
                        help="Disable MORPH_CLOSE alpha cleanup after BG removal")
    parser.add_argument("--canvas-size", type=int, default=1080,
                        help="Square canvas side in pixels (default: 1080)")
    parser.add_argument("--bg-color", default="black",
                        help="Canvas background color: transparent, white, black, "
                             "or #RRGGBB (default: black)")
    parser.add_argument("--edge-pad", type=int, default=55,
                        help="Fixed pixel gap on bottom and sides of canvas "
                             "(default: 55)")
    parser.add_argument("--skip-reframe", action="store_true",
                        help="Skip framing step; output is BG-removed RGBA at "
                             "original dimensions")
    parser.add_argument("--skip-face-detection", action="store_true",
                        help="Skip all face detection steps")
    parser.add_argument("--save-debug", action="store_true",
                        help="Save intermediate debug images alongside output")

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    report = preprocess_image(args)
    report.print_report()


if __name__ == "__main__":
    main()
