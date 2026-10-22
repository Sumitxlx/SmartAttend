import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, ClassGroup, Department,
    MarkMethod, SessionStatus, Student, Subject, Teacher, TeachingAssignment, User, UserRole,
)
from app.services.student_service import goal

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email, role, name=None):
    u = User(email=email, password_hash=hash_password(PASSWORD), full_name=name or email, role=role)
    db.add(u)
    db.commit()
    return u


def login(client, email):
    client.post("/auth/logout")
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


def add_session(db, assignment_id, day, status=SessionStatus.finalized):
    from datetime import date
    s = AttendanceSession(
        teaching_assignment_id=assignment_id,
        session_date=date(2026, 9, day),
        status=status,
    )
    db.add(s)
    db.flush()
    return s


def mark(db, session, student, status):
    db.add(AttendanceRecord(
        session_id=session.id, student_id=student.id,
        status=status, method=MarkMethod.manual,
    ))
    db.flush()


@pytest.fixture()
def world(db_session):
    """Student S1 is in class A. Subject CS501 and subject CS502 are both taught to class A.
    A second student S2 is in class A too, to prove data is not mixed up."""
    dept = Department(code="CSE", name="Computer Science")
    db_session.add(dept)
    db_session.flush()
    cls = ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    cs501 = Subject(code="CS501", name="DBMS", department_id=dept.id, semester=5)
    cs502 = Subject(code="CS502", name="OS", department_id=dept.id, semester=5)
    db_session.add_all([cls, cs501, cs502])
    db_session.flush()

    u_teacher = make_user(db_session, "t@x.com", UserRole.teacher, "Teacher")
    teacher = Teacher(user_id=u_teacher.id, department_id=dept.id, employee_id="E1")
    db_session.add(teacher)
    db_session.flush()
    ta501 = TeachingAssignment(teacher_id=teacher.id, subject_id=cs501.id, class_id=cls.id)
    ta502 = TeachingAssignment(teacher_id=teacher.id, subject_id=cs502.id, class_id=cls.id)
    db_session.add_all([ta501, ta502])
    db_session.flush()

    u1 = make_user(db_session, "s1@x.com", UserRole.student, "Student One")
    s1 = Student(user_id=u1.id, class_id=cls.id, roll_number="R1")
    u2 = make_user(db_session, "s2@x.com", UserRole.student, "Student Two")
    s2 = Student(user_id=u2.id, class_id=cls.id, roll_number="R2")
    db_session.add_all([s1, s2])
    db_session.flush()

    db_session.commit()
    return {"s1": s1, "s2": s2, "ta501": ta501.id, "ta502": ta502.id}


def build_history_for_s1(db, world):
    """CS501: 4 finalized sessions, S1 present 3 times -> 75%.
    CS502: 2 finalized sessions, S1 present 0 times -> 0%.
    One ACTIVE session with S1 present must be ignored."""
    s_a = [add_session(db, world["ta501"], d) for d in (1, 2, 3, 4)]
    for session, status in zip(s_a, [AttendanceStatus.present] * 3 + [AttendanceStatus.absent]):
        mark(db, session, world["s1"], status)
    mark(db, s_a[0], world["s2"], AttendanceStatus.absent)

    s_b = [add_session(db, world["ta502"], d) for d in (1, 2)]
    for session in s_b:
        mark(db, session, world["s1"], AttendanceStatus.absent)

    active = add_session(db, world["ta501"], 9, status=SessionStatus.active)
    mark(db, active, world["s1"], AttendanceStatus.present)
    db.commit()


# ---------- permissions ----------
def test_anonymous_gets_401(client):
    assert client.get("/student/summary").status_code == 401


@pytest.mark.parametrize("role", [UserRole.teacher, UserRole.admin])
def test_non_students_forbidden(client, db_session, role):
    make_user(db_session, "x@x.com", role)
    login(client, "x@x.com")
    assert client.get("/student/summary").status_code == 403
    assert client.get("/student/history").status_code == 403


# ---------- summary ----------
def test_summary_counts_only_finalized_sessions(client, db_session, world):
    build_history_for_s1(db_session, world)
    login(client, "s1@x.com")
    body = client.get("/student/summary").json()

    assert body["overall"]["present"] == 3
    assert body["overall"]["total"] == 6
    assert body["overall"]["percentage"] == 50.0
    assert body["overall"]["low"] is True

    by_code = {s["subject_code"]: s for s in body["subjects"]}
    assert by_code["CS501"]["percentage"] == 75.0
    assert by_code["CS501"]["low"] is False  # exactly 75 is not below the threshold
    assert by_code["CS502"]["percentage"] == 0.0
    assert by_code["CS502"]["low"] is True


def test_summary_with_no_sessions_has_no_percentage(client, world, db_session):
    login(client, "s1@x.com")
    body = client.get("/student/summary").json()
    assert body["overall"]["percentage"] is None
    assert body["overall"]["low"] is False
    assert body["subjects"] == []


def test_student_sees_only_own_records(client, db_session, world):
    build_history_for_s1(db_session, world)
    login(client, "s2@x.com")
    body = client.get("/student/summary").json()
    # S2 has exactly one finalized record (absent, CS501 session 1). S1's 6 records must not appear.
    assert body["overall"]["total"] == 1
    assert body["overall"]["present"] == 0


# ---------- history ----------
def test_history_is_newest_first_and_finalized_only(client, db_session, world):
    build_history_for_s1(db_session, world)
    login(client, "s1@x.com")
    rows = client.get("/student/history").json()
    assert len(rows) == 6
    dates = [r["session_date"] for r in rows]
    assert dates == sorted(dates, reverse=True)
    assert all(r["status"] in ("present", "absent") for r in rows)


# ---------- goal calculator ----------
def test_goal_reports_current_and_classes_needed(db_session, world):
    build_history_for_s1(db_session, world)
    student = db_session.get(Student, world["s1"].id)
    # 3 present out of 6 = 50%. To reach 75%: (3+x)/(6+x) >= 0.75 -> x >= 6.
    result = goal(db_session, student, target=75, future_classes=0)
    assert result["current_percentage"] == 50.0
    assert result["classes_needed"] == 6


def test_goal_already_met_needs_zero(db_session, world):
    build_history_for_s1(db_session, world)
    student = db_session.get(Student, world["s1"].id)
    assert goal(db_session, student, target=40, future_classes=0)["classes_needed"] == 0


def test_goal_projection_if_all_future_attended(db_session, world):
    build_history_for_s1(db_session, world)
    student = db_session.get(Student, world["s1"].id)
    # 3+4 present out of 6+4 total = 70%
    result = goal(db_session, student, target=75, future_classes=4)
    assert result["projected_percentage"] == 70.0


def test_goal_target_100_is_unreachable_after_any_absence(db_session, world):
    build_history_for_s1(db_session, world)
    student = db_session.get(Student, world["s1"].id)
    assert goal(db_session, student, target=100, future_classes=0)["classes_needed"] is None


def test_goal_endpoint_rejects_bad_target(client, world):
    login(client, "s1@x.com")
    assert client.get("/student/goal?target=150").status_code == 422