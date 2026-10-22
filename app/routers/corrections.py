from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.corrections import CorrectionCreate, CorrectionOut
from app.services import correction_service as corr
from app.services.attendance_service import get_teacher_profile
from app.services.student_service import get_student_profile

student_only = require_roles(UserRole.student)
teacher_only = require_roles(UserRole.teacher)

student_router = APIRouter(
    prefix="/student/corrections", tags=["corrections"], dependencies=[Depends(student_only)]
)
teacher_router = APIRouter(
    prefix="/teacher/corrections", tags=["corrections"], dependencies=[Depends(teacher_only)]
)


@student_router.post("", response_model=CorrectionOut, status_code=201)
def request_correction(
    payload: CorrectionCreate, db: Session = Depends(get_db), user: User = Depends(student_only)
):
    student = get_student_profile(db, user)
    correction_id = corr.create_correction(db, user, student, payload)
    return corr.get_out(db, correction_id)


@student_router.get("", response_model=list[CorrectionOut])
def my_corrections(db: Session = Depends(get_db), user: User = Depends(student_only)):
    return corr.list_for_student(db, get_student_profile(db, user))


@teacher_router.get("/pending", response_model=list[CorrectionOut])
def pending_for_me(db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    return corr.list_pending_for_teacher(db, get_teacher_profile(db, user))


@teacher_router.post("/{correction_id}/approve", response_model=CorrectionOut)
def approve(correction_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    corr.decide(db, user, get_teacher_profile(db, user), correction_id, approve=True)
    return corr.get_out(db, correction_id)


@teacher_router.post("/{correction_id}/reject", response_model=CorrectionOut)
def reject(correction_id: int, db: Session = Depends(get_db), user: User = Depends(teacher_only)):
    corr.decide(db, user, get_teacher_profile(db, user), correction_id, approve=False)
    return corr.get_out(db, correction_id)