"""Rules for taking attendance. Routers call these functions and contain no rules of their own."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, ClassGroup, MarkMethod,
    SessionStatus, Student, Subject, Teacher, TeachingAssignment, User,
)
from app.schemas.attendance import SessionOut, StudentRowOut
from app.services.audit import record_audit


def get_teacher_profile(db: Session, user: User) -> Teacher:
    teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id))
    if teacher is None:
        raise HTTPException(status_code=403, detail="No teacher profile for this account")
    return teacher


def list_my_assignments(db: Session, teacher: Teacher) -> list[dict]:
    rows = db.execute(
        select(TeachingAssignment, Subject, ClassGroup)
        .join(Subject, TeachingAssignment.subject_id == Subject.id)
        .join(ClassGroup, TeachingAssignment.class_id == ClassGroup.id)
        .where(TeachingAssignment.teacher_id == teacher.id)
        .order_by(Subject.code, ClassGroup.name)
    ).all()
    return [
        {
            "id": ta.id,
            "subject_id": subject.id,
            "subject_code": subject.code,
            "subject_name": subject.name,
            "class_id": cls.id,
            "class_name": cls.name,
            "semester": cls.semester,
            "academic_year": cls.academic_year,
        }
        for ta, subject, cls in rows
    ]


def get_owned_session(db: Session, teacher: Teacher, session_id: int):
    """Returns (session, assignment). Sessions owned by other teachers look exactly like missing ones."""
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    assignment = db.get(TeachingAssignment, session.teaching_assignment_id)
    if assignment is None or assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session, assignment


def start_session(db: Session, user: User, teacher: Teacher, assignment_id: int) -> AttendanceSession:
    assignment = db.get(TeachingAssignment, assignment_id)
    if assignment is None or assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Uses the server's local date, which is the college's date when the server runs locally.
    today = date.today()
    already = db.scalar(
        select(AttendanceSession.id).where(
            AttendanceSession.teaching_assignment_id == assignment.id,
            AttendanceSession.session_date == today,
        )
    )
    if already is not None:
        raise HTTPException(
            status_code=409,
            detail="A session for this class and subject already exists today",
        )

    session = AttendanceSession(
        teaching_assignment_id=assignment.id,
        session_date=today,
        started_at=utcnow(),
        status=SessionStatus.active,
    )
    db.add(session)
    db.flush()
    record_audit(
        db, user, "attendance_session.started", "attendance_session", session.id,
        f"assignment={assignment.id}",
    )
    db.commit()
    return session


def mark_student(
    db: Session, user: User, teacher: Teacher, session_id: int, student_id: int, status_value: str
) -> AttendanceSession:
    session, assignment = get_owned_session(db, teacher, session_id)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=409, detail="This session is finalized and can no longer be changed")

    student = db.get(Student, student_id)
    if student is None or student.class_id != assignment.class_id:
        raise HTTPException(status_code=422, detail="That student is not in this class")

    new_status = AttendanceStatus(status_value)
    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if record is None:
        db.add(
            AttendanceRecord(
                session_id=session.id,
                student_id=student.id,
                status=new_status,
                method=MarkMethod.manual,
                marked_by_user_id=user.id,
                marked_at=utcnow(),
            )
        )
    else:
        # Changing a mark updates the existing row, so a student never has two records.
        record.status = new_status
        record.method = MarkMethod.manual
        record.marked_by_user_id = user.id
        record.marked_at = utcnow()
    db.commit()
    return session


def finalize_session(db: Session, user: User, teacher: Teacher, session_id: int) -> int:
    session, assignment = get_owned_session(db, teacher, session_id)
    if session.status == SessionStatus.finalized:
        raise HTTPException(status_code=409, detail="Session is already finalized")

    enrolled = db.scalars(select(Student).where(Student.class_id == assignment.class_id)).all()
    marked = set(
        db.scalars(
            select(AttendanceRecord.student_id).where(AttendanceRecord.session_id == session.id)
        ).all()
    )

    auto_absent = 0
    for student in enrolled:
        if student.id not in marked:
            db.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status=AttendanceStatus.absent,
                    method=MarkMethod.manual,
                    marked_by_user_id=user.id,
                    marked_at=utcnow(),
                )
            )
            auto_absent += 1

    session.status = SessionStatus.finalized
    session.finalized_at = utcnow()
    record_audit(
        db, user, "attendance_session.finalized", "attendance_session", session.id,
        f"auto_absent={auto_absent}",
    )
    db.commit()
    return auto_absent


def build_session_out(db: Session, session: AttendanceSession) -> SessionOut:
    assignment = db.get(TeachingAssignment, session.teaching_assignment_id)
    students = db.scalars(
        select(Student).where(Student.class_id == assignment.class_id).order_by(Student.roll_number)
    ).all()
    records = {
        r.student_id: r
        for r in db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)
        ).all()
    }

    rows = []
    for student in students:
        user = db.get(User, student.user_id)
        record = records.get(student.id)
        rows.append(
            StudentRowOut(
                student_id=student.id,
                roll_number=student.roll_number,
                full_name=user.full_name,
                status=record.status.value if record else None,
            )
        )

    return SessionOut(
        id=session.id,
        teaching_assignment_id=session.teaching_assignment_id,
        session_date=session.session_date,
        status=session.status.value,
        started_at=session.started_at,
        finalized_at=session.finalized_at,
        students=rows,
    )