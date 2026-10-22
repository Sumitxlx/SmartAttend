from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import ClassGroup, Department, Subject, User, UserRole
from app.schemas.academic import (
    ClassCreate,
    ClassOut,
    DepartmentCreate,
    DepartmentOut,
    SubjectCreate,
    SubjectOut,
)
from app.services.audit import record_audit

admin_only = require_roles(UserRole.admin)

# The role check covers every route in this file.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_only)])


# ---------- helpers ----------
def _get_or_404(db: Session, model, object_id: int, label: str):
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


def _require_department(db: Session, department_id: int) -> None:
    if db.get(Department, department_id) is None:
        raise HTTPException(status_code=422, detail="Department does not exist")


def _flush_or_conflict(db: Session, message: str) -> None:
    """Send pending changes to the database; turn a rule violation into a 409."""
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def _delete(db: Session, obj, admin: User, entity_type: str, in_use_message: str) -> None:
    entity_id = obj.id
    db.delete(obj)
    _flush_or_conflict(db, in_use_message)
    record_audit(db, admin, f"{entity_type}.deleted", entity_type, entity_id)
    db.commit()


# ---------- departments ----------
@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.scalars(select(Department).order_by(Department.code)).all()


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    dept = Department(code=payload.code, name=payload.name)
    db.add(dept)
    _flush_or_conflict(db, "A department with that code or name already exists")
    record_audit(db, admin, "department.created", "department", dept.id, f"code={dept.code}")
    db.commit()
    return dept


@router.put("/departments/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    dept = _get_or_404(db, Department, department_id, "Department")
    dept.code = payload.code
    dept.name = payload.name
    _flush_or_conflict(db, "A department with that code or name already exists")
    record_audit(db, admin, "department.updated", "department", dept.id, f"code={dept.code}")
    db.commit()
    return dept


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    dept = _get_or_404(db, Department, department_id, "Department")
    _delete(db, dept, admin, "department", "Department is still in use and cannot be deleted")


# ---------- classes ----------
@router.get("/classes", response_model=list[ClassOut])
def list_classes(department_id: int | None = None, db: Session = Depends(get_db)):
    query = select(ClassGroup).order_by(
        ClassGroup.department_id, ClassGroup.semester, ClassGroup.name
    )
    if department_id is not None:
        query = query.where(ClassGroup.department_id == department_id)
    return db.scalars(query).all()


@router.post("/classes", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    _require_department(db, payload.department_id)
    cls = ClassGroup(**payload.model_dump())
    db.add(cls)
    _flush_or_conflict(db, "That class already exists")
    record_audit(
        db, admin, "class.created", "class", cls.id,
        f"{cls.name} sem {cls.semester} {cls.academic_year}",
    )
    db.commit()
    return cls


@router.put("/classes/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    payload: ClassCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    cls = _get_or_404(db, ClassGroup, class_id, "Class")
    _require_department(db, payload.department_id)
    cls.name = payload.name
    cls.department_id = payload.department_id
    cls.semester = payload.semester
    cls.academic_year = payload.academic_year
    _flush_or_conflict(db, "That class already exists")
    record_audit(db, admin, "class.updated", "class", cls.id)
    db.commit()
    return cls


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    cls = _get_or_404(db, ClassGroup, class_id, "Class")
    _delete(db, cls, admin, "class", "Class is still in use and cannot be deleted")


# ---------- subjects ----------
@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(department_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Subject).order_by(Subject.department_id, Subject.semester, Subject.code)
    if department_id is not None:
        query = query.where(Subject.department_id == department_id)
    return db.scalars(query).all()


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    _require_department(db, payload.department_id)
    subject = Subject(**payload.model_dump())
    db.add(subject)
    _flush_or_conflict(db, "A subject with that code already exists")
    record_audit(db, admin, "subject.created", "subject", subject.id, f"code={subject.code}")
    db.commit()
    return subject


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    subject = _get_or_404(db, Subject, subject_id, "Subject")
    _require_department(db, payload.department_id)
    subject.code = payload.code
    subject.name = payload.name
    subject.department_id = payload.department_id
    subject.semester = payload.semester
    _flush_or_conflict(db, "A subject with that code already exists")
    record_audit(db, admin, "subject.updated", "subject", subject.id, f"code={subject.code}")
    db.commit()
    return subject


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    subject = _get_or_404(db, Subject, subject_id, "Subject")
    _delete(db, subject, admin, "subject", "Subject is still in use and cannot be deleted")