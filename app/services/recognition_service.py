"""Live matching rules. Compares faces in one frame with templates of the session's class."""
import numpy as np
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    AttendanceRecord, AttendanceStatus, FaceEmbedding, MarkMethod, SessionStatus, Student, User,
)
from app.services import face_service
from app.services.attendance_service import get_owned_session
from app.services.face_matcher import classify, cosine_similarity

from app.services.audit import record_audit

def _enrolled_templates(db: Session, class_id: int) -> dict[int, list[float]]:
    rows = db.execute(
        select(FaceEmbedding.student_id, FaceEmbedding.embedding)
        .join(Student, FaceEmbedding.student_id == Student.id)
        .where(Student.class_id == class_id)
    ).all()
    return {sid: np.frombuffer(blob, dtype=np.float32).tolist() for sid, blob in rows}


def _write_mark(db: Session, user: User, session_id: int, student_id: int, status: str, score: float) -> bool:
    """Returns True if the record was written. A manual mark is never overwritten."""
    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    if record is None:
        db.add(AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status=AttendanceStatus(status),
            method=MarkMethod.face,
            confidence=score,
            marked_by_user_id=user.id,
            marked_at=utcnow(),
        ))
        return True
    if record.method == MarkMethod.manual:
        return False
    record.status = AttendanceStatus(status)
    record.confidence = score
    record.marked_by_user_id = user.id
    record.marked_at = utcnow()
    return True


def recognize_frame(db: Session, user: User, teacher, session_id: int, photo_path: str) -> dict:
    session, assignment = get_owned_session(db, teacher, session_id)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=409, detail="This session is finalized and can no longer be changed")

    templates = _enrolled_templates(db, assignment.class_id)
    faces = face_service.embed_all_faces(photo_path)

    # For each student, keep the best score across all faces in the frame.
    best: dict[int, float] = {}
    unrecognized = 0
    for face in faces:
        scores = {sid: cosine_similarity(face, t) for sid, t in templates.items()}
        top = max(scores.values(), default=0.0)
        if classify(top) == "unknown":
            unrecognized += 1
        for sid, score in scores.items():
            best[sid] = max(best.get(sid, -1.0), score)

    results = []
    for student_id, score in sorted(best.items()):
        status = classify(score)
        if status == "unknown":
            continue
        student = db.get(Student, student_id)
        user_row = db.get(User, student.user_id)
        written = _write_mark(db, user, session.id, student_id, status, round(score, 4))
        results.append({
            "student_id": student_id,
            "roll_number": student.roll_number,
            "full_name": user_row.full_name,
            "status": status,
            "score": round(score, 4),
            "written": written,
        })

    db.commit()
    return {
        "session_id": session.id,
        "faces_found": len(faces),
        "unrecognized_faces": unrecognized,
        "results": results,
    }



def list_uncertain(db: Session, teacher, session_id: int) -> list[dict]:
    session, _ = get_owned_session(db, teacher, session_id)
    rows = db.execute(
        select(AttendanceRecord, Student, User)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.status == AttendanceStatus.uncertain,
        )
        .order_by(Student.roll_number)
    ).all()
    return [
        {
            "record_id": record.id,
            "student_id": student.id,
            "roll_number": student.roll_number,
            "full_name": user.full_name,
            "score": record.confidence,
        }
        for record, student, user in rows
    ]


def resolve_uncertain(db: Session, user, teacher, session_id: int, record_id: int, status_value: str) -> None:
    session, _ = get_owned_session(db, teacher, session_id)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=409, detail="This session is finalized and can no longer be changed")

    record = db.get(AttendanceRecord, record_id)
    if record is None or record.session_id != session.id:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.status != AttendanceStatus.uncertain:
        raise HTTPException(status_code=409, detail="Only uncertain records can be resolved")

    record.status = AttendanceStatus(status_value)
    record.method = MarkMethod.manual
    record.marked_by_user_id = user.id
    record.marked_at = utcnow()
    record_audit(db, user, "attendance.resolved", "attendance_record", record.id, f"status={status_value}")
    db.commit()