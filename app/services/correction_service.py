"""Correction rules. Routers call these; no rules live in the router."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, CorrectionRequest, CorrectionStatus,
    SessionStatus, Student, Subject, Teacher, TeachingAssignment, User,
)
from app.schemas.corrections import CorrectionCreate
from app.services.audit import record_audit


def _base_query():
    return (
        select(CorrectionRequest, AttendanceRecord, AttendanceSession, Subject, Student, User)
        .join(AttendanceRecord, CorrectionRequest.attendance_record_id == AttendanceRecord.id)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .join(TeachingAssignment, AttendanceSession.teaching_assignment_id == TeachingAssignment.id)
        .join(Subject, TeachingAssignment.subject_id == Subject.id)
        .join(Student, CorrectionRequest.student_id == Student.id)
        .join(User, Student.user_id == User.id)
    )


def _to_out(row) -> dict:
    req, record, session, subject, student, user = row
    return {
        "id": req.id,
        "attendance_record_id": record.id,
        "session_date": session.session_date,
        "subject_code": subject.code,
        "student_name": user.full_name,
        "roll_number": student.roll_number,
        "current_status": record.status.value,
        "requested_status": req.requested_status.value,
        "reason": req.reason,
        "status": req.status.value,
        "created_at": req.created_at,
    }


def get_out(db: Session, correction_id: int) -> dict:
    row = db.execute(_base_query().where(CorrectionRequest.id == correction_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Correction not found")
    return _to_out(row)


def create_correction(db: Session, user: User, student: Student, payload: CorrectionCreate) -> int:
    record = db.get(AttendanceRecord, payload.attendance_record_id)
    if record is None or record.student_id != student.id:
        raise HTTPException(status_code=404, detail="Record not found")

    session = db.get(AttendanceSession, record.session_id)
    if session.status != SessionStatus.finalized:
        raise HTTPException(status_code=409, detail="Only finalized attendance can be corrected")

    requested = AttendanceStatus(payload.requested_status)
    if record.status == requested:
        raise HTTPException(status_code=422, detail="That is already the recorded status")

    pending = db.scalar(
        select(CorrectionRequest.id).where(
            CorrectionRequest.attendance_record_id == record.id,
            CorrectionRequest.status == CorrectionStatus.pending,
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=409,
            detail="A correction for this record is already waiting for review",
        )

    req = CorrectionRequest(
        attendance_record_id=record.id,
        student_id=student.id,
        requested_status=requested,
        reason=payload.reason,
        status=CorrectionStatus.pending,
    )
    db.add(req)
    db.flush()
    record_audit(db, user, "correction.requested", "correction_request", req.id, f"record={record.id}")
    db.commit()
    return req.id


def list_for_student(db: Session, student: Student) -> list[dict]:
    rows = db.execute(
        _base_query()
        .where(CorrectionRequest.student_id == student.id)
        .order_by(CorrectionRequest.id.desc())
    ).all()
    return [_to_out(r) for r in rows]


def list_pending_for_teacher(db: Session, teacher: Teacher) -> list[dict]:
    rows = db.execute(
        _base_query()
        .where(
            TeachingAssignment.teacher_id == teacher.id,
            CorrectionRequest.status == CorrectionStatus.pending,
        )
        .order_by(CorrectionRequest.id)
    ).all()
    return [_to_out(r) for r in rows]


def decide(db: Session, user: User, teacher: Teacher, correction_id: int, approve: bool) -> None:
    req = db.get(CorrectionRequest, correction_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Correction not found")

    record = db.get(AttendanceRecord, req.attendance_record_id)
    session = db.get(AttendanceSession, record.session_id)
    assignment = db.get(TeachingAssignment, session.teaching_assignment_id)
    if assignment.teacher_id != teacher.id:
        # Same answer as a missing request, so other teachers' requests stay hidden.
        raise HTTPException(status_code=404, detail="Correction not found")

    if req.status != CorrectionStatus.pending:
        raise HTTPException(status_code=409, detail="This request has already been decided")

    now = utcnow()
    if approve:
        record.status = req.requested_status
        record.method = record.method  # unchanged; the teacher's decision is recorded below
        record.marked_by_user_id = user.id
        record.marked_at = now

    req.status = CorrectionStatus.approved if approve else CorrectionStatus.rejected
    req.reviewed_by_user_id = user.id
    req.reviewed_at = now

    action = "correction.approved" if approve else "correction.rejected"
    record_audit(
        db, user, action, "correction_request", req.id,
        f"record={record.id} requested={req.requested_status.value}",
    )
    db.commit()