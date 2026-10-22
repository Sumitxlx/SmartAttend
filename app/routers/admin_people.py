from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_password
from app.models import (
    ClassGroup, Department, Student, Subject, Teacher, TeachingAssignment, User, UserRole,
)
from app.schemas.people import (
    AssignmentCreate, AssignmentOut, StudentCreate, StudentOut, TeacherCreate, TeacherOut,
)
from app.services.audit import record_audit

admin_only = require_roles(UserRole.admin)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_only)])


# ---------- helpers ----------
def _save_or_409(db: Session, message: str) -> None:
    """Send pending changes to the database; turn a rule violation into a 409 and undo the whole transaction."""
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def _require(db: Session, model, object_id: int, label: str):
    """For IDs sent in a request body: a missing reference is a bad request (422)."""
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=422, detail=f"{label} does not exist")
    return obj


def _find(db: Session, model, object_id: int, label: str):
    """For IDs in the URL: a missing record is 404."""
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def _teacher_out(teacher: Teacher, user: User) -> TeacherOut:
    return TeacherOut(
        id=teacher.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        department_id=teacher.department_id,
        employee_id=teacher.employee_id,
    )


def _student_out(student: Student, user: User) -> StudentOut:
    return StudentOut(
        id=student.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        class_id=student.class_id,
        roll_number=student.roll_number,
    )


# ---------- teachers ----------
@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Teacher, User).join(User, Teacher.user_id == User.id).order_by(User.full_name)
    ).all()
    return [_teacher_out(teacher, user) for teacher, user in rows]


@router.post("/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    _require(db, Department, payload.department_id, "Department")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.teacher,
    )
    db.add(user)
    _save_or_409(db, "That email is already in use")
    teacher = Teacher(
        user_id=user.id, department_id=payload.department_id, employee_id=payload.employee_id
    )
    db.add(teacher)
    _save_or_409(db, "That employee ID is already in use")
    record_audit(db, admin, "teacher.created", "teacher", teacher.id, f"email={user.email}")
    db.commit()
    return _teacher_out(teacher, user)


# ---------- students ----------
@router.get("/students", response_model=list[StudentOut])
def list_students(class_id: int | None = None, db: Session = Depends(get_db)):
    query = (
        select(Student, User)
        .join(User, Student.user_id == User.id)
        .order_by(Student.class_id, Student.roll_number)
    )
    if class_id is not None:
        query = query.where(Student.class_id == class_id)
    return [_student_out(student, user) for student, user in db.execute(query).all()]


@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    _require(db, ClassGroup, payload.class_id, "Class")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.student,
    )
    db.add(user)
    _save_or_409(db, "That email is already in use")
    student = Student(user_id=user.id, class_id=payload.class_id, roll_number=payload.roll_number)
    db.add(student)
    _save_or_409(db, "That roll number is already in use")
    record_audit(db, admin, "student.created", "student", student.id, f"email={user.email}")
    db.commit()
    return _student_out(student, user)


# ---------- teaching assignments ----------
@router.get("/teaching-assignments", response_model=list[AssignmentOut])
def list_assignments(db: Session = Depends(get_db)):
    return db.scalars(select(TeachingAssignment).order_by(TeachingAssignment.id)).all()


@router.post(
    "/teaching-assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED
)
def create_assignment(
    payload: AssignmentCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    teacher = _require(db, Teacher, payload.teacher_id, "Teacher")
    subject = _require(db, Subject, payload.subject_id, "Subject")
    cls = _require(db, ClassGroup, payload.class_id, "Class")

    if teacher.department_id != subject.department_id:
        raise HTTPException(422, "Teacher and subject must belong to the same department")
    if cls.department_id != subject.department_id:
        raise HTTPException(422, "Class and subject must belong to the same department")
    if cls.semester != subject.semester:
        raise HTTPException(422, "Subject semester must match the class semester")

    assignment = TeachingAssignment(
        teacher_id=payload.teacher_id, subject_id=payload.subject_id, class_id=payload.class_id
    )
    db.add(assignment)
    _save_or_409(db, "This teacher is already assigned to that subject and class")
    record_audit(
        db, admin, "teaching_assignment.created", "teaching_assignment", assignment.id,
        f"teacher={teacher.id} subject={subject.id} class={cls.id}",
    )
    db.commit()
    return assignment


@router.delete("/teaching-assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    assignment = _find(db, TeachingAssignment, assignment_id, "Assignment")
    entity_id = assignment.id
    db.delete(assignment)
    # Once attendance sessions exist, the database will refuse this delete, and we return 409.
    _save_or_409(db, "This assignment has attendance records and cannot be deleted")
    record_audit(db, admin, "teaching_assignment.deleted", "teaching_assignment", entity_id)
    db.commit()