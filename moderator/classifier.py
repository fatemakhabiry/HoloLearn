"""
Input Classifier for HoloLearn Moderator
Identifies the type of each user input (file path or URL).
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.append(str(Path(__file__).parent.parent))

from extractors import get_type_for_extension
from utils.configs import MAX_PDF_SIZE, MAX_VIDEO_SIZE, MAX_AUDIO_SIZE

# File size limits in MB, keyed by input type
_SIZE_LIMITS_MB = {
    "pdf": MAX_PDF_SIZE,
    "docx": MAX_PDF_SIZE,
    "pptx": MAX_PDF_SIZE,
    "video": MAX_VIDEO_SIZE,
    "audio": MAX_AUDIO_SIZE,
}


def classify_input(raw_input: str) -> Dict[str, Any]:
    """
    Classify a single raw input string.

    Args:
        raw_input: A file path or URL string.

    Returns:
        {
            "input": str,
            "type": "pdf"|"docx"|"pptx"|"video"|"audio"|"url"|"unknown",
            "valid": bool,
            "reason": str
        }
    """
    if not raw_input or not isinstance(raw_input, str):
        return {
            "input": str(raw_input) if raw_input is not None else "",
            "type": "unknown",
            "valid": False,
            "reason": "Empty or invalid input",
        }

    cleaned = raw_input.strip()

    # --- URL detection ---
    if cleaned.startswith(("http://", "https://")):
        return {
            "input": cleaned,
            "type": "url",
            "valid": True,
            "reason": "Detected as URL",
        }

    # --- File path detection ---
    path = Path(cleaned)
    ext = path.suffix.lower()

    if not ext:
        return {
            "input": cleaned,
            "type": "unknown",
            "valid": False,
            "reason": "No file extension found",
        }

    input_type = get_type_for_extension(ext)

    if input_type == "unknown":
        return {
            "input": cleaned,
            "type": "unknown",
            "valid": False,
            "reason": f"Unsupported file extension: {ext}",
        }

    if not path.exists():
        return {
            "input": cleaned,
            "type": input_type,
            "valid": False,
            "reason": f"File not found: {cleaned}",
        }

    # Check file size against type-specific limits
    max_size = _SIZE_LIMITS_MB.get(input_type)
    if max_size:
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size:
            return {
                "input": cleaned,
                "type": input_type,
                "valid": False,
                "reason": f"File too large: {file_size_mb:.1f}MB (max {max_size}MB for {input_type})",
            }

    return {
        "input": cleaned,
        "type": input_type,
        "valid": True,
        "reason": f"Valid {input_type} file",
    }


def classify_inputs(raw_inputs: List[str]) -> List[Dict[str, Any]]:
    """
    Classify a list of raw input strings.

    Args:
        raw_inputs: List of file paths and/or URLs.

    Returns:
        List of classification dicts (same shape as classify_input).
    """
    return [classify_input(inp) for inp in raw_inputs]
