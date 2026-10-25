"""Connects real photos to the M9a rules. OpenCV and DeepFace are imported lazily."""
import cv2
import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import FaceEmbedding, Student
from app.services.face_embedding import (
    MODEL_NAME, PhotoReport, build_template,
)
from app.services.face_quality import check_photo


def measure_photo(path: str) -> dict:
    """Reads one image and returns the numbers the quality rules need."""
    image = cv2.imread(path)
    if image is None:
        raise ValueError("The file could not be read as an image")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    from deepface import DeepFace  # lazy: loads TensorFlow only when a photo is measured

    try:
        faces = DeepFace.extract_faces(
            img_path=path, detector_backend="opencv", enforce_detection=False
        )
    except ValueError:
        faces = []
    real_faces = [f for f in faces if f.get("confidence", 1) > 0 and f["facial_area"]["w"] > 0]
    face_count = len(real_faces)
    face_min_side = (
        min(real_faces[0]["facial_area"]["w"], real_faces[0]["facial_area"]["h"])
        if face_count == 1 else 0
    )
    return {
        "brightness": brightness,
        "sharpness": sharpness,
        "face_count": face_count,
        "face_min_side": face_min_side,
    }


def embed_photo(path: str) -> list[float]:
    """Real ArcFace embedding. Only called after the quality check passes."""
    from deepface import DeepFace

    result = DeepFace.represent(img_path=path, model_name=MODEL_NAME, enforce_detection=True)
    return result[0]["embedding"]


def evaluate_photos(paths: list[str]) -> list[PhotoReport]:
    reports = []
    for path in paths:
        try:
            m = measure_photo(path)
        except ValueError as error:
            reports.append(PhotoReport(False, str(error), None))
            continue
        quality = check_photo(
            brightness=m["brightness"], sharpness=m["sharpness"],
            face_count=m["face_count"], face_min_side=m["face_min_side"],
        )
        if not quality.accepted:
            reports.append(PhotoReport(False, quality.reason, None))
        else:
            reports.append(PhotoReport(True, None, embed_photo(path)))
    return reports


def store_template(db: Session, student: Student, template: list[float]) -> None:
    """Replaces any earlier template for this student. The caller commits."""
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.student_id == student.id))
    db.add(FaceEmbedding(
        student_id=student.id,
        embedding=np.array(template, dtype=np.float32).tobytes(),
        model_name=MODEL_NAME,
    ))

def embed_all_faces(path: str) -> list[list[float]]:
    """Embeds every face found in one frame. Used by live matching, not by enrollment."""
    from deepface import DeepFace

    try:
        result = DeepFace.represent(
            img_path=path,
            model_name=MODEL_NAME,
            enforce_detection=False,
            detector_backend="opencv",
        )
    except ValueError:
        return []
    # Drop whole-image fallbacks that have no real face behind them.
    return [r["embedding"] for r in result if r.get("face_confidence", 0) > 0]


def teacher_teaches_student(db: Session, teacher, student: Student) -> bool:
    """True if the teacher has an assignment for the student's class."""
    from app.models import TeachingAssignment

    found = db.scalar(
        select(TeachingAssignment.id).where(
            TeachingAssignment.teacher_id == teacher.id,
            TeachingAssignment.class_id == student.class_id,
        )
    )
    return found is not None
