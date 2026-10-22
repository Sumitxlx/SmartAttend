import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AttendanceRecord, AuditLog, ClassGroup, Department, Student, Subject,
    Teacher, TeachingAssignment, User, UserRole,
)

PASSWORD = "correct-horse-battery"


def make_user(db, email, role, name=None):
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=name or email,
        role=role,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email):
    client.post("/auth/logout")
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


@pytest.fixture()
def world(db_session):
    """Two teachers in one department. Teacher 1 teaches class A. Teacher 2 teaches class B.
    Class A has students R1 and R2. Class B has student R3."""
    u_t1 = make_user(db_session, "t1@x.com", UserRole.teacher, "Teacher One")
    u_t2 = make_user(db_session, "t2@x.com", UserRole.teacher, "Teacher Two")

    dept = Department(code="CSE", name="Computer Science")
    db_session.add(dept)
    db_session.flush()

    cls_a = ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    cls_b = ClassGroup(name="B", department_id=dept.id, semester=5, academic_year="2026-2027")
    subject = Subject(code="CS501", name="DBMS", department_id=dept.id, semester=5)
    db_session.add_all([cls_a, cls_b, subject])
    db_session.flush()

    t1 = Teacher(user_id=u_t1.id, department_id=dept.id, employee_id="E1")
    t2 = Teacher(user_id=u_t2.id, department_id=dept.id, employee_id="E2")
    db_session.add_all([t1, t2])
    db_session.flush()

    ta1 = TeachingAssignment(teacher_id=t1.id, subject_id=subject.id, class_id=cls_a.id)
    ta2 = TeachingAssignment(teacher_id=t2.id, subject_id=subject.id, class_id=cls_b.id)
    db_session.add_all([ta1, ta2])

    students = []
    for email, roll, cls in [
        ("s1@x.com", "R1", cls_a), ("s2@x.com", "R2", cls_a), ("s3@x.com", "R3", cls_b),
    ]:
        u = make_user(db_session, email, UserRole.student, roll)
        s = Student(user_id=u.id, class_id=cls.id, roll_number=roll)
        db_session.add(s)
        students.append(s)
    db_session.flush()
    db_session.commit()

    return {
        "ta1": ta1.id,
        "ta2": ta2.id,
        "s1": students[0].id,
        "s2": students[1].id,
        "s3": students[2].id,
    }


def start(client, assignment_id):
    return client.post("/teacher/sessions", json={"teaching_assignment_id": assignment_id})


# ---------- permissions ----------
def test_anonymous_cannot_use_teacher_routes(client):
    assert client.get("/teacher/assignments").status_code == 401


@pytest.mark.parametrize("role", [UserRole.student, UserRole.admin])
def test_non_teachers_are_forbidden(client, db_session, role):
    make_user(db_session, "other@x.com", role)
    login(client, "other@x.com")
    assert client.get("/teacher/assignments").status_code == 403
    assert start(client, 1).status_code == 403


# ---------- starting sessions ----------
def test_teacher_sees_only_own_assignments(client, world):
    login(client, "t1@x.com")
    rows = client.get("/teacher/assignments").json()
    assert [r["id"] for r in rows] == [world["ta1"]]
    assert rows[0]["class_name"] == "A"


def test_start_session_lists_class_students_unmarked(client, world):
    login(client, "t1@x.com")
    r = start(client, world["ta1"])
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert sorted(s["roll_number"] for s in body["students"]) == ["R1", "R2"]
    assert all(s["status"] is None for s in body["students"])


def test_cannot_start_session_for_another_teachers_assignment(client, world):
    login(client, "t1@x.com")
    assert start(client, world["ta2"]).status_code == 404


def test_second_session_same_day_is_409(client, world):
    login(client, "t1@x.com")
    assert start(client, world["ta1"]).status_code == 201
    assert start(client, world["ta1"]).status_code == 409


# ---------- marking ----------
def mark(client, session_id, student_id, status):
    return client.put(
        f"/teacher/sessions/{session_id}/students/{student_id}",
        json={"status": status},
    )


def test_mark_then_change_keeps_one_record(client, db_session, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]

    r = mark(client, sid, world["s1"], "present")
    assert r.status_code == 200
    assert next(s for s in r.json()["students"] if s["student_id"] == world["s1"])["status"] == "present"

    r = mark(client, sid, world["s1"], "absent")
    assert next(s for s in r.json()["students"] if s["student_id"] == world["s1"])["status"] == "absent"

    count = db_session.scalar(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.session_id == sid, AttendanceRecord.student_id == world["s1"]
        )
    )
    assert count == 1


def test_uncertain_cannot_be_set_manually(client, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]
    assert mark(client, sid, world["s1"], "uncertain").status_code == 422


def test_cannot_mark_student_from_another_class(client, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]
    assert mark(client, sid, world["s3"], "present").status_code == 422


def test_another_teachers_session_is_hidden(client, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]
    login(client, "t2@x.com")
    assert client.get(f"/teacher/sessions/{sid}").status_code == 404
    assert mark(client, sid, world["s1"], "present").status_code == 404


# ---------- finalizing ----------
def test_finalize_marks_unmarked_absent_and_locks(client, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]
    mark(client, sid, world["s1"], "present")

    r = client.post(f"/teacher/sessions/{sid}/finalize")
    assert r.status_code == 200
    body = r.json()
    assert body["auto_marked_absent"] == 1
    assert body["session"]["status"] == "finalized"
    statuses = {s["roll_number"]: s["status"] for s in body["session"]["students"]}
    assert statuses == {"R1": "present", "R2": "absent"}

    assert mark(client, sid, world["s2"], "present").status_code == 409
    assert client.post(f"/teacher/sessions/{sid}/finalize").status_code == 409


def test_audit_records_start_and_finalize(client, db_session, world):
    login(client, "t1@x.com")
    sid = start(client, world["ta1"]).json()["id"]
    client.post(f"/teacher/sessions/{sid}/finalize")
    actions = [log.action for log in db_session.scalars(select(AuditLog)).all()]
    assert "attendance_session.started" in actions
    assert "attendance_session.finalized" in actions

def test_today_session_lookup_is_owner_only(client, world):
    login(client, "t1@x.com")
    url = f"/teacher/assignments/{world['ta1']}/today"
    assert client.get(url).status_code == 404
    sid = start(client, world["ta1"]).json()["id"]
    r = client.get(url)
    assert r.status_code == 200
    assert r.json()["id"] == sid
    login(client, "t2@x.com")
    assert client.get(url).status_code == 404