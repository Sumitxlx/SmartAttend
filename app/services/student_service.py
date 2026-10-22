"""Attendance rules for students. Routers call these; no rules live in the router."""
import math

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, SessionStatus, Student, Subject,
    TeachingAssignment, User,
)

LOW_ATTENDANCE_THRESHOLD = 75.0  # percent


def get_student_profile(db: Session, user: User) -> Student:
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        raise HTTPException(status_code=403, detail="No student profile for this account")
    return student


def _percentage(present: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(present * 100 / total, 2)


def _is_low(percentage: float | None) -> bool:
    return percentage is not None and percentage < LOW_ATTENDANCE_THRESHOLD


def _finalized_rows(db: Session, student: Student):
    """Every finalized record for this student, with its session and subject. Sorted by date."""
    return db.execute(
        select(AttendanceRecord, AttendanceSession, Subject)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .join(TeachingAssignment, AttendanceSession.teaching_assignment_id == TeachingAssignment.id)
        .join(Subject, TeachingAssignment.subject_id == Subject.id)
        .where(
            AttendanceRecord.student_id == student.id,
            AttendanceSession.status == SessionStatus.finalized,
        )
        .order_by(AttendanceSession.session_date, AttendanceRecord.id)
    ).all()


def summary(db: Session, student: Student) -> dict:
    rows = _finalized_rows(db, student)

    per_subject: dict[int, dict] = {}
    overall_present = 0
    overall_total = 0
    for record, _session, subject in rows:
        entry = per_subject.setdefault(
            subject.id,
            {"subject_id": subject.id, "subject_code": subject.code,
             "subject_name": subject.name, "present": 0, "total": 0},
        )
        entry["total"] += 1
        overall_total += 1
        if record.status == AttendanceStatus.present:
            entry["present"] += 1
            overall_present += 1

    subjects = []
    for entry in sorted(per_subject.values(), key=lambda e: e["subject_code"]):
        pct = _percentage(entry["present"], entry["total"])
        subjects.append({**entry, "percentage": pct, "low": _is_low(pct)})

    overall_pct = _percentage(overall_present, overall_total)
    return {
        "overall": {
            "present": overall_present,
            "total": overall_total,
            "percentage": overall_pct,
            "low": _is_low(overall_pct),
            "threshold": LOW_ATTENDANCE_THRESHOLD,
        },
        "subjects": subjects,
    }


def history(db: Session, student: Student) -> list[dict]:
    rows = _finalized_rows(db, student)
    return [
        {
            "session_date": session.session_date,
            "subject_code": subject.code,
            "subject_name": subject.name,
            "status": record.status.value,
        }
        for record, session, subject in reversed(rows)  # newest first
    ]


def goal(db: Session, student: Student, target: float, future_classes: int) -> dict:
    """Pure calculation. Reads the student's totals and changes nothing."""
    rows = _finalized_rows(db, student)
    present = sum(1 for record, _, _ in rows if record.status == AttendanceStatus.present)
    total = len(rows)
    current = _percentage(present, total)

    # Projected: attend all of the next `future_classes`.
    projected = _percentage(present + future_classes, total + future_classes)

    # Classes needed in a row to reach the target: solve (p+x)/(t+x) >= target/100.
    # Attending x more classes gives (p+x)/(t+x). If target is already met, the answer is 0.
    needed: int | None
    if total == 0:
        needed = 0 if target == 0 else None
    elif current is not None and current >= target:
        needed = 0
    elif target >= 100:
        # Only possible if every future class is attended and the student is already at 100.
        needed = None
    else:
        t = target / 100
        # (p + x) >= t * (total + x)  ->  x * (1 - t) >= t * total - p
        x = math.ceil((t * total - present) / (1 - t))
        needed = max(x, 0)

    return {
        "present": present,
        "total": total,
        "target": target,
        "current_percentage": current,
        "classes_needed": needed,
        "projected_percentage": projected,
    }