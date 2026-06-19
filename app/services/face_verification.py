"""
Standalone, testable face verification module for HoloLearn.

Wraps DeepFace + ArcFace to:
  1. Extract a 512-dim face embedding from an image.
  2. Compare two embeddings using cosine distance.
  3. Decide pass/fail against the project's agreed threshold.

This module has ZERO dependency on FastAPI, SQLModel, or the database —
it's meant to be tested in isolation first (see test_face_verification.py),
then imported into the backend once it behaves correctly on real photos.

Threshold convention (ported directly from the Colab notebook):
    - We use cosine DISTANCE, not similarity.
    - distance = 1 - cosine_similarity
    - MATCH  if distance <  THRESHOLD   (faces are similar enough)
    - REJECT if distance >= THRESHOLD
    - THRESHOLD = 0.6  (same value already used for ArcFace in the
      separate student-recognition system — kept consistent on purpose)

Difference from the notebook: enforce_detection=True by default.
The notebook used enforce_detection=False, which means "no face found"
silently falls through to an embedding computed from the whole image
instead of raising. That's fine for exploratory testing, but wrong for
a check that gates a real action — here we want a loud, specific error
instead of a meaningless embedding that might accidentally pass.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from deepface import DeepFace
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)

MODEL_NAME = "ArcFace"
DISTANCE_THRESHOLD = 0.6
EMBEDDING_DIM = 512


class FaceVerificationError(Exception):
    """Base class for any failure in this module the caller should handle."""


class NoFaceDetectedError(FaceVerificationError):
    """No face was found in the image."""


class MultipleFacesDetectedError(FaceVerificationError):
    """More than one face was found in the image."""


@dataclass
class VerificationResult:
    distance: float
    threshold: float
    passed: bool

    def to_dict(self) -> dict:
        return {
            "distance": round(self.distance, 4),
            "threshold": self.threshold,
            "passed": self.passed,
        }


def extract_embedding(image_path: str, enforce_detection: bool = True) -> list[float]:
    """
    Extract a 512-dim ArcFace embedding from an image on disk.

    Raises:
        NoFaceDetectedError: no face found in the image.
        MultipleFacesDetectedError: more than one face found.
        FaceVerificationError: any other extraction failure (corrupt file,
            unreadable image, unexpected DeepFace error, etc).
    """
    path = Path(image_path)
    if not path.exists():
        raise FaceVerificationError(f"Image not found on disk: {image_path}")

    try:
        results = DeepFace.represent(
            img_path=str(path),
            model_name=MODEL_NAME,
            enforce_detection=enforce_detection,
        )
    except ValueError as e:
        # DeepFace raises ValueError with "Face could not be detected" when
        # enforce_detection=True and no face is found in the image.
        if "could not be detected" in str(e).lower():
            raise NoFaceDetectedError(f"No face detected in {image_path}") from e
        raise FaceVerificationError(str(e)) from e
    except Exception as e:  # noqa: BLE001 — DeepFace can raise various backend errors
        raise FaceVerificationError(f"Embedding extraction failed: {e}") from e

    if not results:
        raise NoFaceDetectedError(f"No face detected in {image_path}")

    if len(results) > 1:
        raise MultipleFacesDetectedError(
            f"{len(results)} faces detected in {image_path}; expected exactly 1"
        )

    embedding = results[0]["embedding"]

    if len(embedding) != EMBEDDING_DIM:
        logger.warning(
            "Unexpected embedding size %d (expected %d) for %s — "
            "model_name may not match stored embeddings.",
            len(embedding), EMBEDDING_DIM, image_path,
        )

    return embedding


def cosine_distance(embedding_a: list[float], embedding_b: list[float]) -> float:
    """Cosine distance between two embeddings. 0.0 = identical, 1.0 = orthogonal."""
    return float(cosine(np.asarray(embedding_a), np.asarray(embedding_b)))


def verify(
    embedding_a: list[float],
    embedding_b: list[float],
    threshold: float = DISTANCE_THRESHOLD,
) -> VerificationResult:
    """Compare two embeddings and decide pass/fail against the project threshold."""
    distance = cosine_distance(embedding_a, embedding_b)
    return VerificationResult(
        distance=distance,
        threshold=threshold,
        passed=distance < threshold,
    )


def embedding_to_json(embedding: list[float]) -> str:
    """Serialize an embedding for storage in Teacher.reference_embedding (TEXT column)."""
    return json.dumps(embedding)


def embedding_from_json(raw: str) -> list[float]:
    """Deserialize an embedding loaded back from Teacher.reference_embedding."""
    return json.loads(raw)