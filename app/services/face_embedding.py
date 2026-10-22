"""Turns photos into one stored face template per student.

DeepFace is imported lazily, inside the function that needs it, so the rest of the app and
the test suite never load TensorFlow unless recognition is actually used.
"""
from dataclasses import dataclass
from typing import Callable

import numpy as np

MODEL_NAME = "ArcFace"
REQUIRED_PHOTOS = 5
MIN_USABLE_PHOTOS = 3


@dataclass(frozen=True)
class PhotoReport:
    accepted: bool
    reason: str | None
    embedding: list[float] | None


def average_template(embeddings: list[list[float]]) -> list[float]:
    """Average the accepted embeddings, then normalise to unit length so comparisons are fair."""
    if len(embeddings) < MIN_USABLE_PHOTOS:
        raise ValueError(f"At least {MIN_USABLE_PHOTOS} usable photos are needed")
    mean = np.mean(np.array(embeddings, dtype=np.float32), axis=0)
    norm = np.linalg.norm(mean)
    return (mean / norm).tolist()


def build_template(
    photo_reports: list[PhotoReport],
) -> tuple[list[float] | None, str | None]:
    """Combine per-photo results into one template. Returns (template, error_message)."""
    usable = [r.embedding for r in photo_reports if r.accepted and r.embedding is not None]
    if len(usable) < MIN_USABLE_PHOTOS:
        return None, (
            f"Only {len(usable)} of {len(photo_reports)} photos were usable. "
            f"At least {MIN_USABLE_PHOTOS} are needed. Please upload clearer photos."
        )
    return average_template(usable), None


def embed_image_file(path: str) -> list[float]:
    """Real ArcFace embedding for one image. Used by the app; NOT used by the tests."""
    from deepface import DeepFace  # imported here on purpose

    result = DeepFace.represent(
        img_path=path,
        model_name=MODEL_NAME,
        enforce_detection=True,
    )
    if len(result) != 1:
        raise ValueError("Expected exactly one face in the photo")
    return result[0]["embedding"]


def embedding_from_fn(
    path: str, embedder: Callable[[str], list[float]]
) -> list[float]:
    """Indirection that lets tests pass a fake embedder instead of DeepFace."""
    return embedder(path)