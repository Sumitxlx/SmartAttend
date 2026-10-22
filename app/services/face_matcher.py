"""Compares a face vector with enrolled templates. Pure Python, no model needed."""
import math

PRESENT_MIN = 0.32    # cosine similarity; equals ArcFace cosine distance 0.68
UNCERTAIN_MIN = 0.25  # below this is unknown


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def classify(score: float) -> str:
    if score >= PRESENT_MIN:
        return "present"
    if score >= UNCERTAIN_MIN:
        return "uncertain"
    return "unknown"