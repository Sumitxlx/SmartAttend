import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import ClassGroup, Department, FaceEmbedding, Student, User, UserRole
from app.services import face_service
from app.services.face_embedding import PhotoReport

PASSWORD = "correct-horse-battery"


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
    db.commit()
    return u


def login(client, email):
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


@pytest.fixture()
def student(db_session):
    make_user(db_session, "admin@x.com", UserRole.admin)
    dept = Department(code="CSE", name="Computer Science")
    db_session.add(dept)
    db_session.flush()
    cls = ClassGroup(name="A", department_id=dept.id, semester=5, academic_year="2026-2027")
    db_session.add(cls)
    db_session.flush()
    u = make_user(db_session, "s1@x.com", UserRole.student)
    s = Student(user_id=u.id, class_id=cls.id, roll_number="R1")
    db_session.add(s)
    db_session.commit()
    return s


def fake_photos(count=5):
    return [
        ("photos", (f"p{i}.jpg", io.BytesIO(b"\xff\xd8fake"), "image/jpeg"))
        for i in range(count)
    ]


def fake_evaluate(reports):
    """Returns a fixed list of PhotoReports, replacing the real DeepFace call."""
    def _fn(paths):
        return reports
    return _fn


GOOD = PhotoReport(True, None, [1.0, 0.0, 0.0])
BAD = PhotoReport(False, "The photo is too dark. Try better lighting.", None)


def test_anonymous_and_non_admin_are_refused(client, db_session, student):
    r = client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    assert r.status_code == 401
    login(client, "s1@x.com")
    r = client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    assert r.status_code == 403


def test_wrong_photo_count_is_422(client, db_session, student, monkeypatch):
    login(client, "admin@x.com")
    r = client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos(3))
    assert r.status_code == 422


def test_enrollment_stores_template_when_enough_good_photos(client, db_session, student, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] * 4 + [BAD]))
    login(client, "admin@x.com")
    r = client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    assert r.status_code == 200
    body = r.json()
    assert body["enrolled"] is True
    assert body["accepted_count"] == 4
    assert body["rejected_count"] == 1
    assert "embedding" not in r.text  # never return vectors
    assert db_session.scalar(select(FaceEmbedding).where(FaceEmbedding.student_id == student.id)) is not None


def test_enrollment_refused_when_too_few_usable(client, db_session, student, monkeypatch):
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] + [BAD] * 4))
    login(client, "admin@x.com")
    r = client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    body = r.json()
    assert body["enrolled"] is False
    assert db_session.scalar(select(FaceEmbedding)) is None


def test_re_enrollment_replaces_old_template(client, db_session, student, monkeypatch):
    login(client, "admin@x.com")
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] * 5))
    client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] * 5))
    client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    count = len(db_session.scalars(select(FaceEmbedding)).all())
    assert count == 1


def test_failed_re_enrollment_keeps_old_template(client, db_session, student, monkeypatch):
    login(client, "admin@x.com")
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] * 5))
    client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([BAD] * 5))
    client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    assert len(db_session.scalars(select(FaceEmbedding)).all()) == 1


def test_enrollment_is_audited(client, db_session, student, monkeypatch):
    from app.models import AuditLog
    monkeypatch.setattr(face_service, "evaluate_photos", fake_evaluate([GOOD] * 5))
    login(client, "admin@x.com")
    client.post(f"/admin/students/{student.id}/face-enrollment", files=fake_photos())
    assert "face.enrolled" in [l.action for l in db_session.scalars(select(AuditLog)).all()]