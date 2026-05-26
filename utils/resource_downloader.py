"""
resource_downloader.py

A single downloading class for HoloLearn that handles all remote resource types:
  - Video URLs  (via yt-dlp, falls back to direct stream)
  - Direct video files (.mp4, .webm, …)
  - PDF URLs
  - PPTX / PPT URLs
  - Generic direct-stream fallback for anything else

Usage
-----
    downloader = ResourceDownloader()
    local_path = downloader.download("https://youtu.be/xxx")
    # … process local_path …
    downloader.cleanup(local_path)          # delete when done

    # Or use as a context manager for automatic cleanup:
    with downloader.download_ctx("https://example.com/slides.pptx") as local_path:
        result = pptx_extractor.extract(local_path)
"""

import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Extensions that yt-dlp can handle (video / audio platforms)
_YTDLP_EXTENSIONS = {".mp4", ".webm", ".avi", ".mov", ".mkv", ".mpeg", ".mpg", ".ogg", ".flv"}

# Known video-hosting domains — always route through yt-dlp
_VIDEO_DOMAINS = {
    "youtube.com", "www.youtube.com",
    "youtu.be",
    "vimeo.com", "player.vimeo.com",
    "dailymotion.com", "www.dailymotion.com",
    "twitch.tv", "www.twitch.tv",
    "ted.com", "www.ted.com",
    "wistia.com", "fast.wistia.net",
    "loom.com", "www.loom.com",
}

# Map file extension → default suffix for the temp file
_EXTENSION_MAP = {
    ".pdf":  ".pdf",
    ".pptx": ".pptx",
    ".ppt":  ".ppt",
    ".mp4":  ".mp4",
    ".webm": ".webm",
    ".avi":  ".avi",
    ".mov":  ".mov",
    ".mkv":  ".mkv",
    ".mpeg": ".mpeg",
    ".mpg":  ".mpg",
    ".ogg":  ".ogg",
    ".flv":  ".flv",
}


def _url_extension(url: str) -> str:
    """Return the lowercase file extension from the URL path, e.g. '.pdf'."""
    return Path(urlparse(url).path).suffix.lower()


def _is_video_platform(url: str) -> bool:
    return urlparse(url).netloc.lower() in _VIDEO_DOMAINS


def _sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*#%]', "", name)
    name = name.replace(" ", "_")
    if len(name) > 200:
        stem, ext = os.path.splitext(name)
        name = stem[: 200 - len(ext)] + ext
    return name or "download"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ResourceDownloader:
    """
    Downloads a remote resource to a local temp file and returns its Path.

    The caller is responsible for deleting the file afterwards — either by
    calling ``cleanup(path)`` or by using ``download_ctx()`` which handles
    cleanup automatically.
    """

    def __init__(self, tmp_dir: Optional[str] = None):
        """
        Args:
            tmp_dir: Directory for temporary files.  Defaults to the system
                     temp directory.
        """
        self.tmp_dir = Path(tmp_dir) if tmp_dir else Path(tempfile.gettempdir())
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def download(self, url: str, filename_hint: Optional[str] = None) -> Path:
        """
        Download *url* to a local temp file and return its ``Path``.

        Routing order:
          1. Known video platform domain → yt-dlp
          2. Direct video file extension  → yt-dlp (handles redirected CDN links too)
          3. PDF / PPTX extension         → streaming GET
          4. Anything else                → streaming GET

        Args:
            url:           The remote URL to download.
            filename_hint: Optional filename to use instead of auto-detecting.

        Returns:
            ``Path`` to the downloaded local file.

        Raises:
            ValueError:  If ``url`` does not look like a URL.
            RuntimeError: If the download fails after all attempts.
        """
        if not self._is_url(url):
            raise ValueError(f"Not a valid URL: {url!r}")

        ext = _url_extension(url)

        if _is_video_platform(url) or ext in _YTDLP_EXTENSIONS:
            return self._download_with_ytdlp(url, filename_hint)

        # PDF, PPTX, or generic direct link
        suffix = _EXTENSION_MAP.get(ext, ext or ".bin")
        return self._download_stream(url, suffix, filename_hint)

    def cleanup(self, path: Path) -> None:
        """Delete *path* if it exists.  Silently ignores missing files."""
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            print(f"[ResourceDownloader] Warning: could not delete {path}: {exc}")

    @contextmanager
    def download_ctx(self, url: str, filename_hint: Optional[str] = None):
        """
        Context manager that downloads *url*, yields the local ``Path``,
        then deletes the file on exit — even if an exception is raised.

        Example::

            with downloader.download_ctx("https://example.com/deck.pptx") as p:
                result = pptx_extractor.extract(str(p))
        """
        path = self.download(url, filename_hint)
        try:
            yield path
        finally:
            self.cleanup(path)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_url(value: str) -> bool:
        try:
            r = urlparse(value)
            return bool(r.scheme and r.netloc)
        except Exception:
            return False

    # ── yt-dlp branch ──────────────────────────────────────────────────

    def _download_with_ytdlp(
        self, url: str, filename_hint: Optional[str] = None
    ) -> Path:
        """Download via yt-dlp into an isolated temp directory."""
        print(f"[ResourceDownloader] yt-dlp ← {url}")

        safe_hint = _sanitize_filename(filename_hint or "video")

        # Create isolated temp folder for this download
        download_dir = Path(tempfile.mkdtemp(dir=self.tmp_dir))

        output_template = str(download_dir / f"{safe_hint}.%(ext)s")

        cmd = [
            "yt-dlp",
            "-f", "best",
            "-o", output_template,
            "--no-playlist",
            "--no-warnings",
            url,
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )

            # Find all files created in isolated directory
            files = [p for p in download_dir.iterdir() if p.is_file()]

            if not files:
                raise RuntimeError("yt-dlp succeeded but no files were created")

            # Pick newest/largest file
            best = max(
                files,
                key=lambda p: (p.stat().st_size, p.stat().st_mtime),
            )

            print(f"[ResourceDownloader] Downloaded → {best.name}")

            return best

        except FileNotFoundError:
            print("[ResourceDownloader] yt-dlp not found — falling back to direct stream")
            return self._download_stream(url, ".mp4", filename_hint)

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            print(f"[ResourceDownloader] yt-dlp failed: {stderr[:500]}")
            print("[ResourceDownloader] Falling back to direct stream")
            return self._download_stream(url, ".mp4", filename_hint)
    # # ── Streaming GET branch ────────────────────────────────────────────

    def _download_stream(
        self,
        url: str,
        suffix: str,
        filename_hint: Optional[str] = None,
    ) -> Path:
        """Download via requests streaming GET into a named temp file."""
        print(f"[ResourceDownloader] Streaming ← {url}")

        # Try to get a real filename from Content-Disposition
        suffix = self._resolve_suffix(url, suffix)

        if filename_hint:
            dest = self.tmp_dir / _sanitize_filename(filename_hint)
        else:
            # NamedTemporaryFile gives us a unique path; delete=False so we own it
            with tempfile.NamedTemporaryFile(
                suffix=suffix, dir=self.tmp_dir, delete=False
            ) as tmp:
                dest = Path(tmp.name)

        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest, "wb") as fh:
                for chunk in response.iter_content(chunk_size=65_536):
                    if chunk:
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded / total * 100
                            print(f"\r[ResourceDownloader] {pct:.1f}%", end="", flush=True)

            if total:
                print()  # newline after progress

            print(f"[ResourceDownloader] Downloaded → {dest.name}")
            return dest

        except requests.RequestException as exc:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"Stream download failed for {url}: {exc}") from exc

    def _resolve_suffix(self, url: str, default_suffix: str) -> str:
        """
        Issue a lightweight HEAD request to check Content-Disposition for a
        real filename, then fall back to the URL extension or *default_suffix*.
        """
        try:
            head = requests.head(url, timeout=10, allow_redirects=True)
            cd = head.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                raw = cd.split("filename=")[-1].strip(' "\'')
                ext = Path(raw).suffix.lower()
                if ext:
                    return ext
        except Exception:
            pass

        ext = _url_extension(url)
        return ext if ext else default_suffix
