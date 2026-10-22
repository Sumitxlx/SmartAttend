"""Photo-quality rules, applied before any face embedding is computed. Pure logic, easy to test."""
from dataclasses import dataclass

MIN_BRIGHTNESS = 50.0    # mean gray level 0-255; below this the photo is too dark
MAX_BRIGHTNESS = 205.0   # above this the photo is washed out
MIN_SHARPNESS = 100.0    # variance of the Laplacian; below this the photo is too blurry
MIN_FACE_PIXELS = 80     # shortest side of the detected face box, in pixels


@dataclass(frozen=True)
class QualityResult:
    accepted: bool
    reason: str | None


def check_photo(brightness: float, sharpness: float, face_count: int, face_min_side: int) -> QualityResult:
    """Decides whether one enrollment photo is usable. Inputs come from image measurements."""
    if face_count == 0:
        return QualityResult(False, "No face was found. Use a photo where your face is clearly visible.")
    if face_count > 1:
        return QualityResult(False, "More than one face was found. Use a photo with only you in it.")
    if brightness < MIN_BRIGHTNESS:
        return QualityResult(False, "The photo is too dark. Try better lighting.")
    if brightness > MAX_BRIGHTNESS:
        return QualityResult(False, "The photo is too bright or washed out.")
    if sharpness < MIN_SHARPNESS:
        return QualityResult(False, "The photo is too blurry. Hold the camera still.")
    if face_min_side < MIN_FACE_PIXELS:
        return QualityResult(False, "Your face is too small in the photo. Move closer.")
    return QualityResult(True, None)