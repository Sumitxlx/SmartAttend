import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AuditLog, ClassGroup, Department, FaceEmbedding, Student, Subject, Teacher,
    TeachingAssignment, User, UserRole,
)
from app.services import face_service
from app.services.face_embedding import PhotoReport

PASSWORD = "correct-horse-battery"
GOOD = PhotoReport(True, None, [1.0, 0.0, 0.0])
BAD = PhotoReport(False, "The photo is too dark. Try better lighting.", None)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email, role):
    u = User(email=email, password_hash=hash_password(PASSWORD), full_name=email, role=role)
    db.add(u)
    db.flush()
    return u


def login(client, email):
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


@pytest.fixture()
def world(db_session):
    """Teacher t1 teaches class A only. Student sA is in class A, student sB is in class B."""
    db = db_session
    dept = Department(code="CSE", name="Computer Science")
    db.add(dept)
    db.flush()
    cls_a = ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    cls_b = ClassGroup(name="B", department_id=dept.id, semester=5, academic_year="2026-2027")
    subj = Subject(code="CS501", name="DBMS", department_id=dept.id, semester=5)
    db.add_all([cls_a, cls_b, subj])
    db.flush()

    t1 = Teacher(user_id=make_user(db, "t1@x.com", UserRole.teacher).id,
                 department_id=dept.id, employee_id="E1")
    db.add(t1)
    db.flush()
    db.add(TeachingAssignment(teacher_id=t1.id, subject_id=subj.id, class_id=cls_a.id))

    sa = Student(user_id=make_user(db, "sa@x.com", UserRole.student).id, class_id=cls_a.id, roll_number="RA")
    sb = Student(user_id=make_user(db, "sb@x.com", UserRole.student).id, class_id=cls_b.id, roll_number="RB")
    db.add_all([sa, sb])
    db.commit()
    return {"sa": sa.id, "sb": sb.id}


def photos(count=5):
    return [
        ("photos", (f"p{i}.jpg", io.BytesIO(b"\xff\xd8fake"), "image/jpeg"))
        for i in range(count)
    ]


def url(student_id):
    return f"/teacher/students/{student_id}/face-enrollment"


def test_anonymous_gets_401(client, world):
    assert client.post(url(world["sa"]), files=photos()).status_code == 401


def test_student_gets_403(client, db_session, world):
    login(client, "sa@x.com")
    assert client.post(url(world["sa"]), files=photos()).status_code == 403


def test_teacher_can_enroll_student_in_own_class(client, db_session, world, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", lambda paths: [GOOD] * 5)
    login(client, "t1@x.com")
    r = client.post(url(world["sa"]), files=photos())
    assert r.status_code == 200
    body = r.json()
    assert body["enrolled"] is True
    assert body["accepted_count"] == 5
    assert "embedding" not in r.text
    assert db_session.scalar(
        select(FaceEmbedding).where(FaceEmbedding.student_id == world["sa"])
    ) is not None


def test_teacher_cannot_enroll_student_from_another_class(client, db_session, world, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", lambda paths: [GOOD] * 5)
    login(client, "t1@x.com")
    r = client.post(url(world["sb"]), files=photos())
    assert r.status_code == 404
    assert db_session.scalar(select(FaceEmbedding)) is None


def test_wrong_photo_count_is_422(client, world):
    login(client, "t1@x.com")
    assert client.post(url(world["sa"]), files=photos(4)).status_code == 422


def test_too_few_usable_photos_stores_nothing(client, db_session, world, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", lambda paths: [GOOD] + [BAD] * 4)
    login(client, "t1@x.com")
    body = client.post(url(world["sa"]), files=photos()).json()
    assert body["enrolled"] is False
    assert db_session.scalar(select(FaceEmbedding)) is None


def test_re_enrollment_replaces_template(client, db_session, world, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", lambda paths: [GOOD] * 5)
    login(client, "t1@x.com")
    client.post(url(world["sa"]), files=photos())
    client.post(url(world["sa"]), files=photos())
    assert len(db_session.scalars(select(FaceEmbedding)).all()) == 1


def test_enrollment_is_audited_with_teacher_as_actor(client, db_session, world, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", lambda paths: [GOOD] * 5)
    login(client, "t1@x.com")
    client.post(url(world["sa"]), files=photos())
    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "face.enrolled")).all()
    assert len(logs) == 1
    teacher_user = db_session.scalar(select(User).where(User.email == "t1@x.com"))
    assert logs[0].user_id == teacher_user.id