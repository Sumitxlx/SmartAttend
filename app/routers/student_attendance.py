from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.student import GoalOut, GoalQuery, HistoryItem, SummaryOut
from app.services import student_service as svc
from fastapi import Query

student_only = require_roles(UserRole.student)

# The role check covers every route. The student is always the signed-in user, never a URL parameter.
router = APIRouter(prefix="/student", tags=["student attendance"], dependencies=[Depends(student_only)])


@router.get("/summary", response_model=SummaryOut)
def my_summary(db: Session = Depends(get_db), user: User = Depends(student_only)):
    return svc.summary(db, svc.get_student_profile(db, user))


@router.get("/history", response_model=list[HistoryItem])
def my_history(db: Session = Depends(get_db), user: User = Depends(student_only)):
    return svc.history(db, svc.get_student_profile(db, user))


@router.get("/goal", response_model=GoalOut)
def my_goal(
    target: float = Query(ge=0, le=100),
    future_classes: int = Query(default=0, ge=0, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    return svc.goal(db, svc.get_student_profile(db, user), target, future_classes)