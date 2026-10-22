from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, AuditLog, ClassGroup, Department,
    MarkMethod, SessionStatus, Student, Subject, Teacher, TeachingAssignment, User, UserRole,
)

PASSWORD = "correct-horse-battery"
REASON = "I was present but the teacher missed my name"


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


@pytest.fixture()
def world(db_session):
    """Class A has students s1 and s2 and teacher t1. Teacher t2 teaches class B only.
    Session 1 is finalized (s1 absent, s2 present). Session 2 is still active (s1 absent)."""
    db = db_session
    dept = Department(code="CSE", name="Computer Science")
    db.add(dept)
    db.flush()
    cls_a = ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    cls_b = ClassGroup(name="B", department_id=dept.id, semester=5, academic_year="2026-2027")
    subj = Subject(code="CS501", name="DBMS", department_id=dept.id, semester=5)
    db.add_all([cls_a, cls_b, subj])
    db.flush()

    t1 = Teacher(user_id=make_user(db, "t1@x.com", UserRole.teacher, "Teacher One").id,
                 department_id=dept.id, employee_id="E1")
    t2 = Teacher(user_id=make_user(db, "t2@x.com", UserRole.teacher, "Teacher Two").id,
                 department_id=dept.id, employee_id="E2")
    db.add_all([t1, t2])
    db.flush()

    ta1 = TeachingAssignment(teacher_id=t1.id, subject_id=subj.id, class_id=cls_a.id)
    ta2 = TeachingAssignment(teacher_id=t2.id, subject_id=subj.id, class_id=cls_b.id)
    db.add_all([ta1, ta2])
    db.flush()

    s1 = Student(user_id=make_user(db, "s1@x.com", UserRole.student, "Student One").id,
                 class_id=cls_a.id, roll_number="R1")
    s2 = Student(user_id=make_user(db, "s2@x.com", UserRole.student, "Student Two").id,
                 class_id=cls_a.id, roll_number="R2")
    db.add_all([s1, s2])
    db.flush()

    finalized = AttendanceSession(teaching_assignment_id=ta1.id, session_date=date(2026, 9, 1),
                                  status=SessionStatus.finalized)
    active = AttendanceSession(teaching_assignment_id=ta1.id, session_date=date(2026, 9, 2),
                               status=SessionStatus.active)
    db.add_all([finalized, active])
    db.flush()

    r_s1 = AttendanceRecord(session_id=finalized.id, student_id=s1.id,
                            status=AttendanceStatus.absent, method=MarkMethod.manual)
    r_s2 = AttendanceRecord(session_id=finalized.id, student_id=s2.id,
                            status=AttendanceStatus.present, method=MarkMethod.manual)
    r_active = AttendanceRecord(session_id=active.id, student_id=s1.id,
                                status=AttendanceStatus.absent, method=MarkMethod.manual)
    db.add_all([r_s1, r_s2, r_active])
    db.commit()
    return {"s1_absent": r_s1.id, "s2_present": r_s2.id, "active": r_active.id}


def request_fix(client, record_id, requested="present", reason=REASON):
    return client.post("/student/corrections", json={
        "attendance_record_id": record_id,
        "requested_status": requested,
        "reason": reason,
    })


# ---------- permissions ----------
def test_anonymous_gets_401(client, world):
    assert client.get("/student/corrections").status_code == 401
    assert client.get("/teacher/corrections/pending").status_code == 401


def test_roles_are_separated(client, db_session, world):
    login(client, "t1@x.com")
    assert client.get("/student/corrections").status_code == 403
    login(client, "s1@x.com")
    assert client.get("/teacher/corrections/pending").status_code == 403


# ---------- student requests ----------
def test_student_request_is_pending_and_visible_to_teacher(client, world):
    login(client, "s1@x.com")
    r = request_fix(client, world["s1_absent"])
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["current_status"] == "absent"
    assert body["requested_status"] == "present"

    login(client, "t1@x.com")
    pending = client.get("/teacher/corrections/pending").json()
    assert [p["id"] for p in pending] == [body["id"]]


def test_student_cannot_correct_another_students_record(client, world):
    login(client, "s2@x.com")
    assert request_fix(client, world["s1_absent"]).status_code == 404


def test_cannot_correct_an_active_session(client, world):
    login(client, "s1@x.com")
    assert request_fix(client, world["active"]).status_code == 409


def test_requested_status_must_differ_from_recorded(client, world):
    login(client, "s1@x.com")
    assert request_fix(client, world["s1_absent"], requested="absent").status_code == 422


def test_only_one_pending_request_per_record(client, world):
    login(client, "s1@x.com")
    assert request_fix(client, world["s1_absent"]).status_code == 201
    assert request_fix(client, world["s1_absent"]).status_code == 409


def test_reason_must_be_meaningful(client, world):
    login(client, "s1@x.com")
    assert request_fix(client, world["s1_absent"], reason="sorry").status_code == 422


def test_student_sees_only_own_requests(client, world):
    login(client, "s1@x.com")
    request_fix(client, world["s1_absent"])
    assert len(client.get("/student/corrections").json()) == 1
    login(client, "s2@x.com")
    assert client.get("/student/corrections").json() == []


# ---------- teacher decisions ----------
def test_approve_changes_record_and_is_audited(client, db_session, world):
    login(client, "s1@x.com")
    cid = request_fix(client, world["s1_absent"]).json()["id"]

    login(client, "t1@x.com")
    r = client.post(f"/teacher/corrections/{cid}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    record = db_session.get(AttendanceRecord, world["s1_absent"])
    db_session.refresh(record)
    assert record.status == AttendanceStatus.present
    assert "correction.approved" in [log.action for log in db_session.scalars(select(AuditLog))]


def test_reject_leaves_record_unchanged(client, db_session, world):
    login(client, "s1@x.com")
    cid = request_fix(client, world["s1_absent"]).json()["id"]

    login(client, "t1@x.com")
    r = client.post(f"/teacher/corrections/{cid}/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    record = db_session.get(AttendanceRecord, world["s1_absent"])
    db_session.refresh(record)
    assert record.status == AttendanceStatus.absent


def test_other_teacher_cannot_see_or_decide(client, world):
    login(client, "s1@x.com")
    cid = request_fix(client, world["s1_absent"]).json()["id"]

    login(client, "t2@x.com")
    assert client.get("/teacher/corrections/pending").json() == []
    assert client.post(f"/teacher/corrections/{cid}/approve").status_code == 404


def test_decision_is_final(client, world):
    login(client, "s1@x.com")
    cid = request_fix(client, world["s1_absent"]).json()["id"]

    login(client, "t1@x.com")
    assert client.post(f"/teacher/corrections/{cid}/approve").status_code == 200
    assert client.post(f"/teacher/corrections/{cid}/reject").status_code == 409
    assert client.post(f"/teacher/corrections/{cid}/approve").status_code == 409