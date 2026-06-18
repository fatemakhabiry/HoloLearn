"""
video_extractor.py

Extracts text content from video files via two parallel branches:

  Audio branch  → FFmpeg WAV → Groq Whisper → timestamped segments
  Frame branch  → FFmpeg PNGs → phash dedup → CCA→CNN→VLM→JSON → frames_data

Both branches merge into a unified timeline and are saved as 6 output files
for downstream RAG consumption.

EasyOCR and pix2tex have been removed entirely.
The standalone OCR pipeline (pipeline.py) handles all on-screen text and equations.
"""

import csv
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Internal utilities ────────────────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent.parent))

from utils.configs import (
    OUTPUT_DIR,
    LOGS_DIR,
    TEMP_DIR,
    GROQ_API_KEY_VIDEO,
    SUPPORTED_VIDEO_FORMATS,
    MAX_VIDEO_SIZE,
    FRAME_EXTRACTION_FPS,
    MAX_FRAMES_PER_VIDEO,
    SCENE_CHANGE_THRESHOLD,
    OCR_PIPELINE_DIR,
    CNN_MODEL_PATH,
    CLASSIFIER_DEVICE,
    VLM_MODEL,
    VLM_BASE_URL,
    VLM_API_KEY,
)
from utils.error_handler import ErrorHandler
from utils.text_cleaner import TextCleaner
from utils.video_processor import VideoProcessor


class VideoExtractor:
    """
    Extract text from video files using audio transcription and the
    CCA → CNN → VLM standalone OCR pipeline.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.text_cleaner    = TextCleaner()
        self.base_output_dir = OUTPUT_DIR
        self.base_logs_dir   = LOGS_DIR
        self.temp_dir        = TEMP_DIR

        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.base_logs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.video_processor = VideoProcessor()
        self.api_key         = api_key or GROQ_API_KEY_VIDEO

        # Inject OCR pipeline directory into sys.path once at init time so
        # pipeline.py and its sibling modules resolve correctly at import.
        if OCR_PIPELINE_DIR and OCR_PIPELINE_DIR not in sys.path:
            sys.path.insert(0, OCR_PIPELINE_DIR)

    # ─────────────────────────────────────────────────────────────────────────
    # Resource / directory helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _create_resource_name(self, filename: str) -> str:
        name = Path(filename).stem.lower()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        name = name.strip('_')
        return name[:50] or "unnamed_video"

    def _setup_resource_directories(self, resource_name: str) -> tuple:
        out_dir = self.base_output_dir / resource_name
        log_dir = self.base_logs_dir   / resource_name
        out_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        return out_dir, log_dir

    def _validate_video_file(self, video_path: Path, error_handler: ErrorHandler) -> bool:
        if not video_path.exists():
            error_handler.log_error(FileNotFoundError(f"Video not found: {video_path}"))
            return False
        if video_path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
            error_handler.log_error(ValueError(f"Unsupported format: {video_path.suffix}"))
            return False
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_VIDEO_SIZE:
            error_handler.log_error(ValueError(f"File too large: {size_mb:.2f} MB"))
            return False
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Timestamp helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _format_timestamp(self, seconds: float) -> str:
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def _timestamp_to_seconds(self, ts: str) -> float:
        parts = list(map(int, ts.split(':')))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0.0

    def _seconds_to_timestamp(self, seconds: float) -> str:
        s   = int(seconds)
        h   = s // 3600
        m   = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

    # ─────────────────────────────────────────────────────────────────────────
    # Audio branch
    # ─────────────────────────────────────────────────────────────────────────

    def _transcribe_with_timestamps(
        self, audio_path: str, error_handler: ErrorHandler
    ) -> List[Dict]:
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            with open(audio_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(Path(audio_path).name, f.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            segments = []
            if hasattr(transcription, 'segments') and transcription.segments:
                for seg in transcription.segments:
                    if isinstance(seg, dict):
                        segments.append({
                            'start': seg.get('start', 0),
                            'end':   seg.get('end',   0),
                            'text':  seg.get('text',  '').strip(),
                        })
                    else:
                        segments.append({
                            'start': seg.start,
                            'end':   seg.end,
                            'text':  seg.text.strip(),
                        })
            else:
                text = getattr(transcription, 'text', str(transcription))
                segments.append({'start': 0, 'end': 0, 'text': text})

            return segments

        except Exception as e:
            error_handler.log_error(e, context="Audio transcription")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Frame branch — OCR pipeline helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _deduplicate_frames(
        self, frame_paths: List[str], error_handler: ErrorHandler
    ) -> List[str]:
        """
        Remove near-duplicate consecutive frames using perceptual hashing (phash).

        Keeps the FIRST frame from each group of visually similar frames so we
        don't run the expensive OCR pipeline on repeated static slides.

        Falls back to returning all frames unchanged if imagehash is not installed.
        Requires: pip install imagehash Pillow
        """
        try:
            import imagehash
            from PIL import Image
        except ImportError:
            error_handler.log_error(
                ImportError("imagehash not installed — skipping deduplication. "
                            "Run: pip install imagehash"),
                context="Frame deduplication",
            )
            return frame_paths  # graceful: all frames kept

        if not frame_paths:
            return []

        unique    = [frame_paths[0]]
        prev_hash = imagehash.phash(Image.open(frame_paths[0]))

        for path in frame_paths[1:]:
            try:
                curr_hash = imagehash.phash(Image.open(path))
                if (curr_hash - prev_hash) >= SCENE_CHANGE_THRESHOLD:
                    unique.append(path)
                    prev_hash = curr_hash
            except Exception as e:
                # Keep frame on error — safer than silently dropping content
                error_handler.log_error(e, context=f"Hashing frame {path}")
                unique.append(path)

        error_handler.log_info(
            f"Deduplication: {len(frame_paths)} → {len(unique)} unique frames",
            metadata={"dropped": len(frame_paths) - len(unique)},
        )
        return unique

    def _merge_csvs(self, csv_paths: List[str], output_path: str) -> str:
        """
        Row-append all per-frame CSVs into one shared CSV.

        Writes the header once (taken from the first file), then appends data
        rows from every file. Deletes each per-frame CSV after its rows are merged
        so temporary files don't pile up.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        header_written = False
        writer         = None

        with open(output_path, 'w', newline='', encoding='utf-8') as out_f:
            for csv_path in csv_paths:
                if not Path(csv_path).is_file():
                    continue
                with open(csv_path, 'r', newline='', encoding='utf-8') as in_f:
                    reader = csv.DictReader(in_f)
                    if not header_written:
                        writer = csv.DictWriter(out_f, fieldnames=reader.fieldnames)
                        writer.writeheader()
                        header_written = True
                    for row in reader:
                        writer.writerow(row)
                # Delete per-frame CSV now that its rows are safely written
                try:
                    Path(csv_path).unlink()
                except OSError:
                    pass

        return str(output_path)

    def _clean_ocr_text(self, text: str) -> str:
        """
        Strip VLM leakage artifacts injected by the transcription prompt.

        Removes:
          - "LABEL:<type>\\n" prefix lines
          - "[NO_CONTENT]" markers for empty crops
          - Leftover blank lines
        """
        if not text:
            return ""
        text = re.sub(r'^LABEL:\S+\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\[NO_CONTENT\]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _latex_to_readable(self, latex: str) -> str:
        """
        Convert a LaTeX equation string to human-readable plain text.

        Strips $$ / $ delimiters first, then uses pylatexenc.
        Falls back to returning the stripped raw string if conversion fails.

        Requires: pip install pylatexenc
        """
        clean = latex.strip()
        clean = re.sub(r'^\$\$|\$\$$', '', clean).strip()
        clean = re.sub(r'^\$|\$$',     '', clean).strip()

        try:
            from pylatexenc.latex2text import LatexNodes2Text
            return LatexNodes2Text().latex_to_text(clean).strip()
        except Exception:
            return clean  # fallback: delimiter-stripped raw string

    def _cleanup_pipeline_files(
        self, frame_paths: List[str], error_handler: ErrorHandler
    ) -> None:
        """Delete extracted frame PNGs after all OCR outputs are safely written."""
        deleted = 0
        for path in frame_paths:
            try:
                Path(path).unlink(missing_ok=True)
                deleted += 1
            except OSError as e:
                error_handler.log_error(e, context=f"Deleting frame PNG: {path}")
        error_handler.log_info(f"Deleted {deleted} frame PNG(s)")

    def _run_ocr_pipeline(
        self,
        unique_frames:     List[str],
        timestamp_map:     Dict[str, float],  # frame_path → timestamp in seconds
        model_path:        str,
        api_key:           str,
        vlm_model:         str,
        vlm_base_url:      str,
        classifier_device: str,
        work_dir:          Path,
        error_handler:     ErrorHandler,
        debug:             bool = False,
    ) -> List[Dict]:
        """
        Run CCA → CNN → VLM → JSON on deduplicated frames and return frames_data.

        Each entry in frames_data:
            {timestamp, frame_number, path, text, equations}

        Graceful degradation:
        - model_path missing/not found → skip OCR, return frames with empty text.
        - Per-frame CCA failure        → that frame is skipped, others continue.
        - CNN classifier failure       → logged, VLM still runs (labels may be wrong).
        - VLM failure                  → logged, returns empty list.
        """
        if not unique_frames:
            return []

        # ── Guard: CNN model must exist ───────────────────────────────────────
        if not model_path or not Path(model_path).exists():
            error_handler.log_error(
                FileNotFoundError(f"CNN model not found: {model_path} — skipping OCR"),
                context="OCR pipeline guard",
            )
            # Return skeleton entries so the timeline still has frame timestamps
            return [
                {
                    'timestamp':    timestamp_map.get(p, 0.0),
                    'frame_number': i + 1,
                    'path':         p,
                    'text':         '',
                    'equations':    '',
                }
                for i, p in enumerate(unique_frames)
            ]

        # ── Import pipeline stages ────────────────────────────────────────────
        # OCR_PIPELINE_DIR was injected into sys.path in __init__
        try:
            from OCR.pipeline import (
                run_cca_pipeline,
                run_classifier_stage,
                run_vlm_stage,
                run_txt_stage,
            )
        except ImportError as e:
            error_handler.log_error(
                e, context="Importing OCR pipeline — is OCR_PIPELINE_DIR set correctly?"
            )
            return []

        # ── Stages 1-6: CCA per frame → crop PNGs + per-frame CSV ────────────
        crops_dir = work_dir / "crops"
        crops_dir.mkdir(parents=True, exist_ok=True)

        csv_paths: List[str] = []

        for frame_path in unique_frames:
            try:
                _, _, _, _, _, csv_path = run_cca_pipeline(
                    image_path=frame_path,
                    output_dir=str(crops_dir),
                )
                if csv_path and Path(csv_path).is_file():
                    csv_paths.append(csv_path)
                else:
                    error_handler.log_error(
                        RuntimeError(f"CCA returned no CSV for frame {Path(frame_path).name}"),
                        context="CCA pipeline",
                    )
            except Exception as e:
                error_handler.log_error(
                    e, context=f"CCA pipeline on frame {Path(frame_path).name}"
                )

        if debug:
            error_handler.log_info(
                f"[DEBUG] CCA stage: {len(csv_paths)}/{len(unique_frames)} frames produced CSVs",
                metadata={"csv_paths": csv_paths}
            )

        if not csv_paths:
            error_handler.log_error(
                RuntimeError("CCA stage produced no CSVs — all frames failed"),
                context="OCR pipeline",
            )
            return []

        # ── Merge all per-frame CSVs into one shared CSV ──────────────────────
        merged_csv = str(work_dir / "merged_crops.csv")
        try:
            merged_csv = self._merge_csvs(csv_paths, merged_csv)
        except Exception as e:
            error_handler.log_error(e, context="CSV merge")
            return []

        # ── Stage 7: CNN classification ───────────────────────────────────────
        if debug:
            try:
                with open(merged_csv, newline='', encoding='utf-8') as _f:
                    _rows = list(csv.DictReader(_f))
                error_handler.log_info(
                    f"[DEBUG] Merged CSV: {len(_rows)} rows, "
                    f"columns: {list(_rows[0].keys()) if _rows else 'EMPTY'}"
                )
                if _rows:
                    error_handler.log_info(
                        f"[DEBUG] First row sample: {dict(list(_rows[0].items())[:4])}"
                    )
            except Exception as _e:
                error_handler.log_info(f"[DEBUG] Could not read merged CSV: {_e}")

        try:
            merged_csv = run_classifier_stage(merged_csv, model_path, classifier_device)
        except Exception as e:
            # Non-fatal: VLM can still run even without confident labels
            error_handler.log_error(e, context="CNN classification stage")

        if debug:
            try:
                with open(merged_csv, newline='', encoding='utf-8') as _f:
                    _rows = list(csv.DictReader(_f))
                _labels = [r.get('label','?') for r in _rows]
                error_handler.log_info(f"[DEBUG] After CNN: {len(_rows)} rows, labels={_labels[:10]}")
            except Exception as _e:
                error_handler.log_info(f"[DEBUG] Could not read CSV after CNN: {_e}")

        # ── Stage 8: VLM transcription ────────────────────────────────────────
        try:
            merged_csv = run_vlm_stage(merged_csv, api_key, vlm_model, vlm_base_url)
        except Exception as e:
            error_handler.log_error(e, context="VLM transcription stage")
            return []

        if debug:
            try:
                with open(merged_csv, newline='', encoding='utf-8') as _f:
                    _rows = list(csv.DictReader(_f))
                _transcriptions = [r.get('transcription', '')[:60] for r in _rows]
                error_handler.log_info(
                    f"[DEBUG] After VLM: {len(_rows)} rows"
                )
                for _i, _t in enumerate(_transcriptions[:5]):
                    error_handler.log_info(f"[DEBUG]   row {_i}: transcription='{_t}'")
            except Exception as _e:
                error_handler.log_info(f"[DEBUG] Could not read CSV after VLM: {_e}")

        # ── Stage 9: JSON assembly ────────────────────────────────────────────
        try:
            docs, _ = run_txt_stage(merged_csv, str(work_dir))
        except Exception as e:
            error_handler.log_error(e, context="TXT assembly stage")
            return []

        if debug:
            error_handler.log_info(f"[DEBUG] TXT stage: {len(docs)} doc(s)")
            for _d in docs[:3]:
                error_handler.log_info(
                    f"[DEBUG]   source_image='{_d.get('source_image')}' "
                    f"text_len={len(_d.get('text',''))}"
                )
            error_handler.log_info(f"[DEBUG] unique_frames paths (first 3): {unique_frames[:3]}")
            error_handler.log_info(
                f"[DEBUG] doc_map keys will be built from source_image — "
                f"check above that they match unique_frames paths exactly"
            )

        # ── Post-process docs → frames_data ──────────────────────────────────
        # source_image in each doc = the original frame PNG path
        doc_map: Dict[str, Dict] = {str(Path(d['source_image']).resolve()): d for d in docs}

        if debug:
            error_handler.log_info(
                f"[DEBUG] doc_map has {len(doc_map)} entries. "
                f"Keys (first 3): {list(doc_map.keys())[:3]}"
            )

        frames_data: List[Dict] = []

        for i, frame_path in enumerate(unique_frames):
            doc      = doc_map.get(frame_path, {})
            if debug:
                hit = frame_path in doc_map
                error_handler.log_info(
                    f"[DEBUG] frame {i}: path='{frame_path}' → doc_map hit={hit} "
                    f"text_len={len(doc.get('text',''))}"
                )
            raw_text = doc.get('text', '')

            # 1. Clean VLM leakage
            clean_txt = self._clean_ocr_text(raw_text)

            # 2. Extract $$...$$ patterns, convert to readable, replace inline
            eq_patterns  = re.findall(r'\$\$.+?\$\$', clean_txt, re.DOTALL)
            readable_eqs = []
            for eq in eq_patterns:
                readable = self._latex_to_readable(eq)
                readable_eqs.append(readable)
                clean_txt = clean_txt.replace(eq, readable, 1)

            frames_data.append({
                'timestamp':    timestamp_map.get(frame_path, 0.0),
                'frame_number': i + 1,
                'path':         frame_path,
                'text':         clean_txt,
                'equations':    '\n'.join(readable_eqs),
            })

        # ── Delete crop PNGs (frames deleted by _cleanup_pipeline_files) ──────
        deleted_crops = 0
        try:
            with open(merged_csv, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    crop = row.get('crop_path', '').strip()
                    if crop and Path(crop).is_file():
                        Path(crop).unlink()
                        deleted_crops += 1
        except Exception as e:
            error_handler.log_error(e, context="Crop PNG cleanup")

        error_handler.log_info(
            f"OCR pipeline complete",
            metadata={
                "frames_processed": len(frames_data),
                "crops_deleted":    deleted_crops,
            },
        )
        return frames_data

    def _process_frames(
        self,
        video_path:        str,
        resource_name:     str,
        fps:               float,
        max_frames:        int,
        model_path:        str,
        api_key:           str,
        vlm_model:         str,
        vlm_base_url:      str,
        classifier_device: str,
        work_dir:          Path,
        error_handler:     ErrorHandler,
        debug:             bool = False,
    ) -> List[Dict]:
        """
        Full frame branch coordinator:
            extract frames → deduplicate → run OCR pipeline → delete frame PNGs

        Returns frames_data ready for timeline merge.
        """
        # ── Extract frames via FFmpeg ─────────────────────────────────────────
        try:
            frame_paths = self.video_processor.extract_frames(
                video_path,
                str(self.temp_dir / f"{resource_name}_frames"),
                fps=fps,
                max_frames=max_frames,
            )
        except Exception as e:
            error_handler.log_error(e, context="Frame extraction")
            return []

        if not frame_paths:
            return []

        # ── Rename frames to short sequential names ───────────────────────────
        # Windows MAX_PATH is 260 chars. The original video filename is often
        # very long, and crop_extractor.py appends "{stem}_regions/{stem}_N.png"
        # which pushes paths past 260 chars and causes silent write failures.
        # Renaming to f00000.png, f00001.png etc. keeps every downstream path short.
        short_paths = []
        frames_dir  = Path(frame_paths[0]).parent
        for i, original in enumerate(frame_paths):
            short = frames_dir / f"f{i:05d}.png"
            try:
                Path(original).rename(short)
                short_paths.append(str(short))
            except OSError:
                short_paths.append(original)   # keep original on rename failure
        frame_paths = short_paths

        # ── Build timestamp map: frame_path → seconds ─────────────────────────
        interval      = 1.0 / fps
        timestamp_map = {path: i * interval for i, path in enumerate(frame_paths)}

        # ── Deduplicate via phash ─────────────────────────────────────────────
        unique_frames = self._deduplicate_frames(frame_paths, error_handler)

        # ── Run CCA → CNN → VLM → JSON pipeline ──────────────────────────────
        frames_data = self._run_ocr_pipeline(
            unique_frames     = unique_frames,
            timestamp_map     = timestamp_map,
            model_path        = model_path,
            api_key           = api_key,
            vlm_model         = vlm_model,
            vlm_base_url      = vlm_base_url,
            classifier_device = classifier_device,
            work_dir          = work_dir,
            error_handler     = error_handler,
            debug             = debug,
        )

        # ── Delete all extracted frame PNGs ───────────────────────────────────
        self._cleanup_pipeline_files(frame_paths, error_handler)

        return frames_data

    # ─────────────────────────────────────────────────────────────────────────
    # Timeline helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _organize_by_timeline(
        self,
        audio_segments: List[Dict],
        frames_data:    List[Dict],
        error_handler:  ErrorHandler,
    ) -> List[Dict]:
        timeline = []

        if not audio_segments and not frames_data:
            return timeline

        if audio_segments and not frames_data:
            for seg in audio_segments:
                timeline.append({
                    'start': seg['start'], 'end': seg['end'],
                    'audio': seg['text'],  'frames': [],
                })
            return timeline

        if frames_data and not audio_segments:
            for f in frames_data:
                timeline.append({
                    'start': f['timestamp'], 'end': f['timestamp'] + 1,
                    'audio': '',             'frames': [f],
                })
            return timeline

        # Both branches have data — match frames to their audio segment
        for seg in audio_segments:
            s, e     = seg['start'], seg['end']
            matching = [f for f in frames_data if s <= f['timestamp'] <= e]
            timeline.append({
                'start': s, 'end': e,
                'audio': seg['text'], 'frames': matching,
            })

        return timeline

    def _format_main_output(self, timeline: List[Dict]) -> str:
        """
        Format the timeline as a clean synchronized transcript — the primary output.

        Format per segment:
            [MM:SS – MM:SS]
            Spoken:  <audio transcription>
            On screen:
            - <line from frame OCR>
            - <line from frame OCR>

        Rules:
        - Segments with neither audio nor on-screen text are skipped.
        - Screen text is split on newlines; each non-trivial line becomes a bullet.
        - Duplicate bullets within the same segment are suppressed.
        - The "(no significant on-screen text)" placeholder is omitted — clean silence.
        """
        lines = []

        for segment in timeline:
            audio  = segment.get('audio', '').strip()
            frames = segment.get('frames', [])
            start  = segment['start']
            end    = segment['end']

            # ── Collect unique, meaningful screen-text lines ──────────────────
            screen_bullets: List[str] = []
            for frame in frames:
                raw = frame.get('text', '').strip()
                if not raw:
                    continue
                for line in raw.split('\n'):
                    line = line.strip()
                    # Skip trivial lines (too short, pure punctuation, etc.)
                    if len(line) < 5:
                        continue
                    if line not in screen_bullets:
                        screen_bullets.append(line)

            # Skip completely empty segments
            if not audio and not screen_bullets:
                continue

            start_str = self._format_timestamp(start)
            end_str   = self._format_timestamp(end)
            lines.append(f"[{start_str} – {end_str}]")

            if audio:
                lines.append(f"Spoken:  {audio}")

            if screen_bullets:
                lines.append("On screen:")
                for bullet in screen_bullets:
                    lines.append(f"- {bullet}")

            lines.append("")   # blank line between segments

        return '\n'.join(lines).strip()

    def _format_timeline_output(self, timeline: List[Dict]) -> tuple:
        """
        Returns (combined_text, equations_text, audio_text, ocr_text) —
        four separate strings for writing to different output files.
        """
        combined_parts = []
        all_equations  = []
        all_audio      = []
        all_ocr        = []

        for i, segment in enumerate(timeline, 1):
            start_ts = self._format_timestamp(segment['start'])
            end_ts   = self._format_timestamp(segment['end'])

            combined_parts.append(
                f"\n{'='*70}\nSEGMENT {i} - [{start_ts} → {end_ts}]\n{'='*70}\n\n"
            )

            if segment['audio']:
                combined_parts.append(f"🎤 AUDIO TRANSCRIPTION:\n{segment['audio']}\n\n")
                all_audio.append(f"[{start_ts}] {segment['audio']}")

            for frame in segment['frames']:
                frame_ts = self._format_timestamp(frame['timestamp'])
                if frame['text']:
                    combined_parts.append(
                        f"📺 SCREEN TEXT (Frame {frame['frame_number']} at {frame_ts}):\n"
                        f"{frame['text']}\n\n"
                    )
                    all_ocr.append(f"[{frame_ts}] {frame['text']}")
                if frame['equations']:
                    combined_parts.append(
                        f"📐 EQUATIONS (Frame {frame['frame_number']} at {frame_ts}):\n"
                        f"{frame['equations']}\n\n"
                    )
                    all_equations.append(f"[{frame_ts}] {frame['equations']}")

        return (
            ''.join(combined_parts),
            '\n\n'.join(all_equations) if all_equations else "",
            '\n\n'.join(all_audio)     if all_audio     else "",
            '\n\n'.join(all_ocr)       if all_ocr       else "",
        )

    def _format_clean_transcript(self, timeline: List[Dict]) -> str:
        """Audio-only clean transcript — paragraphs with timestamps, no OCR noise."""
        paragraphs = []
        current    = []
        last_end   = 0.0

        for segment in timeline:
            audio = segment.get('audio', '').strip()
            if not audio or len(audio) < 15:
                continue

            start = segment['start']
            if start - last_end > 5.0 and current:
                paragraphs.append(" ".join(current))
                current = []

            cleaned = re.sub(r'\s+', ' ', audio)
            cleaned = re.sub(r'\s+([.,!?])', r'\1', cleaned).strip()
            if cleaned:
                current.append(cleaned)

            last_end = segment['end']

        if current:
            paragraphs.append(" ".join(current))

        full = "\n\n".join(paragraphs)
        full = re.sub(r'\s+', ' ', full).strip()
        return full.replace(' . ', '. ').replace(' , ', ', ')

    # ─────────────────────────────────────────────────────────────────────────
    # Synchronized view helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_audio_transcript_file(self, file_path: Path) -> List[Dict]:
        entries = []
        pattern = r'\[(\d{2}:\d{2}(?::\d{2})?)\]\s*(.+)'
        if not file_path.is_file():
            return entries
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                match = re.match(pattern, line.strip())
                if match:
                    ts_str, text = match.groups()
                    entries.append({
                        'start_sec': self._timestamp_to_seconds(ts_str),
                        'end_sec':   None,
                        'text':      text.strip(),
                    })
        return entries

    def _parse_screen_text_file(self, file_path: Path) -> List[Dict]:
        entries = []
        pattern = r'\[(\d{2}:\d{2})\]\s*(.+)'
        if not file_path.is_file():
            return entries
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                match = re.match(pattern, line.strip())
                if match:
                    ts_str, text = match.groups()
                    entries.append({
                        'timestamp_sec': self._timestamp_to_seconds(ts_str),
                        'text':          text.strip(),
                    })
        return entries

    def _assign_end_times(self, audio_entries: List[Dict]) -> None:
        for i in range(len(audio_entries) - 1):
            audio_entries[i]['end_sec'] = audio_entries[i + 1]['start_sec']
        if audio_entries:
            audio_entries[-1]['end_sec'] = audio_entries[-1]['start_sec'] + 6.0

    def _format_synchronized_view(
        self, timeline: List[Dict], output_dir: Path, resource_name: str
    ) -> str:
        lines     = []
        has_audio = any(bool(seg.get('audio', '').strip()) for seg in timeline)

        if has_audio:
            # Primary path: build from in-memory timeline
            for seg in timeline:
                spoken = seg.get('audio', '').strip()
                if not spoken:
                    continue
                start_str = self._format_timestamp(seg['start'])
                end_str   = self._format_timestamp(seg['end'])

                lines.append(f"[{start_str} – {end_str}]")
                lines.append(f"Spoken:  {spoken}")
                lines.append("")

                screen_set = {
                    f['text'].strip() for f in seg['frames']
                    if len(f['text'].strip()) >= 10
                }
                if screen_set:
                    lines.append("On screen:")
                    for txt in sorted(screen_set):
                        lines.append(f"- {txt}")
                else:
                    lines.append("(no significant on-screen text)")
                lines.append("")

        else:
            # Fallback path: read already-saved output files
            audio_file  = output_dir / f"{resource_name}_audio_transcript.txt"
            screen_file = output_dir / f"{resource_name}_screen_text.txt"

            if not audio_file.is_file() and not screen_file.is_file():
                return "No audio or screen text files found for synchronization."

            audio_data  = self._parse_audio_transcript_file(audio_file)
            screen_data = self._parse_screen_text_file(screen_file)

            if audio_data:
                self._assign_end_times(audio_data)
                screen_sorted = sorted(screen_data, key=lambda x: x['timestamp_sec'])

                for entry in audio_data:
                    start = entry['start_sec']
                    end   = entry.get('end_sec', start + 8.0)
                    lines.append(
                        f"[{self._seconds_to_timestamp(start)} – {self._seconds_to_timestamp(end)}]"
                    )
                    lines.append(f"Spoken:  {entry['text']}")
                    lines.append("")

                    visible = {
                        s['text'].strip() for s in screen_sorted
                        if start <= s['timestamp_sec'] < end and len(s['text'].strip()) >= 10
                    }
                    if visible:
                        lines.append("On screen:")
                        for txt in sorted(visible):
                            lines.append(f"- {txt}")
                    else:
                        lines.append("(no significant on-screen text)")
                    lines.append("")

            elif screen_data:
                lines.append("No spoken audio detected. Grouping by screen text changes.")
                screen_sorted = sorted(screen_data, key=lambda x: x['timestamp_sec'])
                current_text  = None
                block_start   = None
                block_texts: List[str] = []

                for entry in screen_sorted:
                    txt = entry['text'].strip()
                    if len(txt) < 10:
                        continue
                    t = entry['timestamp_sec']

                    if txt != current_text:
                        if current_text is not None and block_start is not None:
                            s_str = self._seconds_to_timestamp(block_start)
                            e_str = self._seconds_to_timestamp(t)
                            lines += [f"[{s_str} – {e_str}]", "(no spoken audio)", ""]
                            lines.append("On screen:")
                            for bt in sorted(set(block_texts)):
                                lines.append(f"- {bt}")
                            lines.append("")
                        block_start  = t
                        block_texts  = [txt]
                        current_text = txt
                    else:
                        if txt not in block_texts:
                            block_texts.append(txt)

                # Flush last block
                if current_text is not None and block_start is not None:
                    s_str = self._seconds_to_timestamp(block_start)
                    e_str = self._seconds_to_timestamp(
                        screen_sorted[-1]['timestamp_sec'] + 5
                    )
                    lines += [f"[{s_str} – {e_str}]", "(no spoken audio)", ""]
                    lines.append("On screen:")
                    for bt in sorted(set(block_texts)):
                        lines.append(f"- {bt}")
                    lines.append("")

            else:
                lines.append("No usable audio or screen text content found.")

        return "\n".join(lines) if lines else "No synchronized content available."

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    def extract(
        self,
        video_path:        str,
        resource_id:       Optional[str]   = None,
        clean_text:        bool            = True,
        extract_audio:     bool            = True,
        extract_frames:    bool            = True,
        fps:               Optional[float] = None,
        max_frames:        Optional[int]   = None,
        # ── OCR pipeline params — default to configs.py values ────────────
        model_path:        Optional[str]   = None,
        vlm_model:         Optional[str]   = None,
        vlm_base_url:      Optional[str]   = None,
        vlm_api_key:       Optional[str]   = None,
        classifier_device: Optional[str]   = None,
        debug:             bool            = False,
    ) -> Dict[str, Any]:
        """
        Extract text from a video file.

        Audio branch  → Groq Whisper → timestamped segments
        Frame branch  → phash dedup → CCA→CNN→VLM→JSON → frames_data

        All OCR params default to values in configs.py.
        Pass them explicitly here to override on a per-call basis.

        Returns a dict with keys:
            success, resource_name, text_file, clean_transcript_file,
            synchronized_file, equations_file, audio_transcript_file,
            screen_text_file, metadata_file, metadata,
            extracted_text, audio_text, ocr_text, equations_text, timeline
        """
        start_time = time.time()
        video_path = Path(video_path)

        resource_name        = self._create_resource_name(video_path.name)
        output_dir, logs_dir = self._setup_resource_directories(resource_name)

        error_handler          = ErrorHandler(f"video_{resource_name}")
        error_handler.log_file = logs_dir / "extraction.log"
        error_handler.logger   = error_handler._setup_logger()

        if not self._validate_video_file(video_path, error_handler):
            return self._create_error_result(
                resource_name, "Validation failed", output_dir, video_path.name
            )

        # ── Resolve OCR params: per-call override → config default ────────────
        _model_path        = model_path        or CNN_MODEL_PATH
        _vlm_model         = vlm_model         or VLM_MODEL
        _vlm_base_url      = vlm_base_url      or VLM_BASE_URL
        _vlm_api_key       = vlm_api_key       or VLM_API_KEY
        _classifier_device = classifier_device or CLASSIFIER_DEVICE

        file_size = video_path.stat().st_size

        try:
            video_info     = self.video_processor.get_video_info(str(video_path))
            audio_segments = []
            frames_data    = []

            # ── Audio branch ──────────────────────────────────────────────────
            if extract_audio:
                audio_path = self.video_processor.extract_audio(
                    str(video_path),
                    str(self.temp_dir / f"{resource_name}_audio.wav"),
                )
                audio_segments = self._transcribe_with_timestamps(audio_path, error_handler)
                Path(audio_path).unlink(missing_ok=True)

            # ── Frame branch ──────────────────────────────────────────────────
            if extract_frames:
                fps_val  = fps        or FRAME_EXTRACTION_FPS
                max_f    = max_frames or MAX_FRAMES_PER_VIDEO
                work_dir = self.temp_dir / f"{resource_name}_ocr_work"
                work_dir.mkdir(parents=True, exist_ok=True)

                frames_data = self._process_frames(
                    video_path        = str(video_path),
                    resource_name     = resource_name,
                    fps               = fps_val,
                    max_frames        = max_f,
                    model_path        = _model_path,
                    api_key           = _vlm_api_key,
                    vlm_model         = _vlm_model,
                    vlm_base_url      = _vlm_base_url,
                    classifier_device = _classifier_device,
                    work_dir          = work_dir,
                    error_handler     = error_handler,
                    debug             = debug,
                )

            # ── Merge into timeline ───────────────────────────────────────────
            timeline = self._organize_by_timeline(audio_segments, frames_data, error_handler)

            if not timeline:
                raise ValueError("No content extracted from audio or frames")

            # ── Primary output: clean synchronized transcript ────────────────
            main_text = self._format_main_output(timeline)

            # ── Sub-file content: equations / audio-only / ocr-only ───────────
            _, equations_text, audio_text, ocr_text = \
                self._format_timeline_output(timeline)

            # ── Save output files ─────────────────────────────────────────────
            text_file = output_dir / f"{resource_name}_text.txt"
            text_file.write_text(main_text, encoding='utf-8')

            equations_file = audio_file = ocr_file = None

            # if equations_text and equations_text.strip():
            #     equations_file = output_dir / f"{resource_name}_equations.txt"
            #     equations_file.write_text(equations_text, encoding='utf-8')

            # if audio_text and audio_text.strip():
            #     audio_file = output_dir / f"{resource_name}_audio_transcript.txt"
            #     audio_file.write_text(audio_text, encoding='utf-8')

            # if ocr_text and ocr_text.strip():
            #     ocr_file = output_dir / f"{resource_name}_screen_text.txt"
            #     ocr_file.write_text(ocr_text, encoding='utf-8')

            # ── Metadata ──────────────────────────────────────────────────────
            metadata = {
                "resource_name":           resource_name,
                "resource_id":             resource_id or resource_name,
                "filename":                video_path.name,
                "source_type":             "video",
                "video_format":            video_path.suffix.lower(),
                "upload_date":             datetime.now().isoformat(),
                "extraction_timestamp":    datetime.now().isoformat(),
                "file_size_bytes":         file_size,
                "processing_time_seconds": round(time.time() - start_time, 2),
                "status":                  "success",
                "error_message":           None,
                "video_info":              video_info,
                "timeline_segments":       len(timeline),
                "audio_segments":          len(audio_segments),
                "frames_processed":        len(frames_data),
                "ocr_model":               _model_path,
                "vlm_model":               _vlm_model,
                # "extracted_text_path":     str(text_file),
                # "audio_transcript_path":   str(audio_file)     if audio_file     else None,
                # "screen_text_path":        str(ocr_file)       if ocr_file       else None,
                # "equations_file_path":     str(equations_file) if equations_file else None,
            }

            metadata_file = output_dir / f"{resource_name}_metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            metadata["metadata_file"] = str(metadata_file)

            return {
                "success":               True,
                "resource_name":         resource_name,
                "text_file":             str(text_file),
                
                "equations_file":        str(equations_file) if equations_file else None,
                "audio_transcript_file": str(audio_file)     if audio_file     else None,
                "screen_text_file":      str(ocr_file)       if ocr_file       else None,
                "metadata_file":         str(metadata_file),
                "metadata":              metadata,
                "extracted_text":        main_text,
                
                
                "audio_text":            audio_text,
                "ocr_text":              ocr_text,
                "equations_text":        equations_text,
                "timeline":              timeline,
            }

        except Exception as e:
            processing_time = time.time() - start_time
            error_handler.log_error(e, context="Video extraction")
            return self._create_error_result(
                resource_name, str(e), output_dir,
                video_path.name, file_size, processing_time,
            )

    def _create_error_result(
        self,
        resource_name:   str,
        error_message:   str,
        output_dir:      Path,
        filename:        str   = "unknown",
        file_size:       int   = 0,
        processing_time: float = 0,
    ) -> Dict[str, Any]:
        metadata = {
            "resource_name":           resource_name,
            "filename":                filename,
            "source_type":             "video",
            "upload_date":             datetime.now().isoformat(),
            "extraction_timestamp":    datetime.now().isoformat(),
            "file_size_bytes":         file_size,
            "processing_time_seconds": round(processing_time, 2),
            "status":                  "failed",
            "error_message":           error_message,
        }
        metadata_file = output_dir / f"{resource_name}_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

        return {
            "success":       False,
            "resource_name": resource_name,
            "metadata_file": str(metadata_file),
            "metadata":      metadata,
            "error":         error_message,
        }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from utils.file_picker import FilePicker

    print("=== Testing Video Extractor (CCA → CNN → VLM pipeline) ===\n")

    extractor  = VideoExtractor()
    picker     = FilePicker()
    print("Select a video file...")
    test_video = picker.pick_video()
    picker.close()

    if test_video:
        print(f"\nProcessing: {Path(test_video).name}")
        result = extractor.extract(
            video_path     = test_video,
            clean_text     = True,
            extract_audio  = True,
            extract_frames = True,
            debug          = True,   # ← set False to silence OCR stage logs
        )

        if result['success']:
            meta = result['metadata']
            print("\n✓ Extraction complete")
            print(f"  Text file:        {result['text_file']}")
            if result.get('equations_file'):
                print(f"  Equations:        {result['equations_file']}")
            if result.get('audio_transcript_file'):
                print(f"  Audio transcript: {result['audio_transcript_file']}")
            if result.get('screen_text_file'):
                print(f"  Screen text:      {result['screen_text_file']}")
            print(f"  Frames processed: {meta['frames_processed']}")
            print(f"  Audio segments:   {meta['audio_segments']}")
            print(f"  Time:             {meta['processing_time_seconds']}s")
        else:
            print(f"\n✗ Failed: {result['error']}")
    else:
        print("No file selected.")


        