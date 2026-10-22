import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models as m


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def make_student_and_session(db):
    dept = m.Department(code="CSE", name="Computer Science")
    db.add(dept)
    db.flush()

    cls = m.ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    t_user = m.User(email="t@x.com", password_hash="h", full_name="T", role=m.UserRole.teacher)
    s_user = m.User(email="s@x.com", password_hash="h", full_name="S", role=m.UserRole.student)
    subject = m.Subject(code="CS501", name="DBMS", department_id=dept.id, semester=5)
    db.add_all([cls, t_user, s_user, subject])
    db.flush()

    teacher = m.Teacher(user_id=t_user.id, department_id=dept.id, employee_id="E1")
    student = m.Student(user_id=s_user.id, class_id=cls.id, roll_number="R1")
    db.add_all([teacher, student])
    db.flush()

    ta = m.TeachingAssignment(teacher_id=teacher.id, subject_id=subject.id, class_id=cls.id)
    db.add(ta)
    db.flush()

    session = m.AttendanceSession(teaching_assignment_id=ta.id, session_date=date.today())
    db.add(session)
    db.flush()
    return student, session


def test_duplicate_email_is_rejected(db):
    db.add(m.User(email="a@x.com", password_hash="h", full_name="A", role=m.UserRole.admin))
    db.commit()
    db.add(m.User(email="a@x.com", password_hash="h", full_name="B", role=m.UserRole.admin))
    with pytest.raises(IntegrityError):
        db.commit()


def test_one_attendance_record_per_student_per_session(db):
    student, session = make_student_and_session(db)
    db.add(m.AttendanceRecord(
        session_id=session.id, student_id=student.id,
        status=m.AttendanceStatus.present, method=m.MarkMethod.manual,
    ))
    db.commit()

    db.add(m.AttendanceRecord(
        session_id=session.id, student_id=student.id,
        status=m.AttendanceStatus.absent, method=m.MarkMethod.manual,
    ))
    with pytest.raises(IntegrityError):
        db.commit()