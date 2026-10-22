from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.attendance import (
    FinalizeOut, MarkIn, MyAssignmentOut, SessionOut, SessionStart,
)
from app.services import attendance_service as svc

teacher_only = require_roles(UserRole.teacher)

# The role check covers every route in this file.
router = APIRouter(prefix="/teacher", tags=["teacher attendance"], dependencies=[Depends(teacher_only)])


@router.get("/assignments", response_model=list[MyAssignmentOut])
def my_assignments(db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    return svc.list_my_assignments(db, svc.get_teacher_profile(db, user))


@router.post("/sessions", response_model=SessionOut, status_code=201)
def start_session(
    payload: SessionStart, db: Session = Depends(get_db), user: User = Depends(teacher_only)
):
    teacher = svc.get_teacher_profile(db, user)
    session = svc.start_session(db, user, teacher, payload.teaching_assignment_id)
    return svc.build_session_out(db, session)


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    teacher = svc.get_teacher_profile(db, user)
    session, _ = svc.get_owned_session(db, teacher, session_id)
    return svc.build_session_out(db, session)


@router.put("/sessions/{session_id}/students/{student_id}", response_model=SessionOut)
def mark_student(
    session_id: int,
    student_id: int,
    payload: MarkIn,
    db: Session = Depends(get_db),
    user: User = Depends(teacher_only),
):
    teacher = svc.get_teacher_profile(db, user)
    session = svc.mark_student(db, user, teacher, session_id, student_id, payload.status)
    return svc.build_session_out(db, session)


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeOut)
def finalize_session(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)
):
    teacher = svc.get_teacher_profile(db, user)
    auto_absent = svc.finalize_session(db, user, teacher, session_id)
    session, _ = svc.get_owned_session(db, teacher, session_id)
    return FinalizeOut(
        session=svc.build_session_out(db, session),
        auto_marked_absent=auto_absent,
    )