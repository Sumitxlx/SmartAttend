import io
from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    AttendanceRecord, AttendanceSession, AttendanceStatus, ClassGroup, Department,
    FaceEmbedding, MarkMethod, SessionStatus, Student, Subject, Teacher,
    TeachingAssignment, User, UserRole,
)
from app.services import face_service
from app.services.face_matcher import classify, cosine_similarity

PASSWORD = "correct-horse-battery"


# ---------- pure matching rules ----------
def test_identical_vectors_have_similarity_one():
    assert cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_zero():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_zero_vector_gives_zero_not_error():
    assert cosine_similarity([0, 0], [1, 0]) == 0.0


@pytest.mark.parametrize(
    "score, expected",
    [(0.9, "present"), (0.32, "present"), (0.30, "uncertain"), (0.25, "uncertain"), (0.10, "unknown")],
)
def test_classify_bands(score, expected):
    assert classify(score) == expected


# ---------- live recognition ----------
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
    db.flush()
    return u


def login(client, email):
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def enroll(db, student, vector):
    db.add(FaceEmbedding(
        student_id=student.id,
        embedding=np.array(vector, dtype=np.float32).tobytes(),
        model_name="ArcFace",
    ))


@pytest.fixture()
def world(db_session):
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
    db.add(ta1)
    db.flush()

    students = {}
    for key, email, cls in [("s1", "s1@x.com", cls_a), ("s2", "s2@x.com", cls_a), ("s3", "s3@x.com", cls_b)]:
        u = make_user(db, email, UserRole.student, key)
        st = Student(user_id=u.id, class_id=cls.id, roll_number=key.upper())
        db.add(st)
        db.flush()
        students[key] = st

    enroll(db, students["s1"], [1, 0, 0])
    enroll(db, students["s2"], [0, 1, 0])
    enroll(db, students["s3"], [0, 0, 1])  # class B student: must never be matched in class A

    active = AttendanceSession(teaching_assignment_id=ta1.id, session_date=date(2026, 9, 2),
                               status=SessionStatus.active)
    finalized = AttendanceSession(teaching_assignment_id=ta1.id, session_date=date(2026, 9, 3),
                                  status=SessionStatus.finalized)
    db.add_all([active, finalized])
    db.commit()
    return {
        "s1": students["s1"].id,
        "active": active.id,
        "finalized": finalized.id,
    }


def recognize(client, session_id):
    return client.post(
        f"/teacher/sessions/{session_id}/recognize",
        files={"photo": ("frame.jpg", io.BytesIO(b"\xff\xd8frame"), "image/jpeg")},
    )


def fake_faces(monkeypatch, vectors):
    monkeypatch.setattr(face_service, "embed_all_faces", lambda path: vectors)


def records_for(db, session_id, student_id):
    return db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    ).all()


def test_confident_face_is_marked_present(client, db_session, world, monkeypatch):
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "t1@x.com")
    r = recognize(client, world["active"])
    assert r.status_code == 200
    body = r.json()
    assert [(x["roll_number"], x["status"]) for x in body["results"]] == [("S1", "present")]
    assert body["unrecognized_faces"] == 0
    record = records_for(db_session, world["active"], world["s1"])[0]
    assert record.status == AttendanceStatus.present
    assert record.method == MarkMethod.face


def test_borderline_face_is_marked_uncertain(client, db_session, world, monkeypatch):
    # Cosine similarity with s1 is 0.28, which is in the uncertain band.
    fake_faces(monkeypatch, [[0.28, 0, 0.96]])
    login(client, "t1@x.com")
    body = recognize(client, world["active"]).json()
    assert body["results"][0]["status"] == "uncertain"
    record = records_for(db_session, world["active"], world["s1"])[0]
    assert record.status == AttendanceStatus.uncertain


def test_unknown_face_is_counted_not_marked(client, db_session, world, monkeypatch):
    # Matches only the class B student, who must be ignored in class A.
    fake_faces(monkeypatch, [[0, 0, 1]])
    login(client, "t1@x.com")
    body = recognize(client, world["active"]).json()
    assert body["results"] == []
    assert body["unrecognized_faces"] == 1
    assert db_session.scalars(select(AttendanceRecord)).all() == []


def test_manual_mark_is_never_overwritten(client, db_session, world, monkeypatch):
    db_session.add(AttendanceRecord(
        session_id=world["active"], student_id=world["s1"],
        status=AttendanceStatus.absent, method=MarkMethod.manual,
    ))
    db_session.commit()
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "t1@x.com")
    body = recognize(client, world["active"]).json()
    assert body["results"][0]["written"] is False
    record = records_for(db_session, world["active"], world["s1"])[0]
    assert record.status == AttendanceStatus.absent
    assert record.method == MarkMethod.manual


def test_later_frame_updates_single_record(client, db_session, world, monkeypatch):
    login(client, "t1@x.com")
    fake_faces(monkeypatch, [[1, 0, 0]])
    recognize(client, world["active"])
    fake_faces(monkeypatch, [[0.28, 0, 0.96]])
    recognize(client, world["active"])
    records = records_for(db_session, world["active"], world["s1"])
    assert len(records) == 1
    assert records[0].status == AttendanceStatus.uncertain


def test_finalized_session_is_refused(client, world, monkeypatch):
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "t1@x.com")
    assert recognize(client, world["finalized"]).status_code == 409


def test_other_teacher_cannot_recognize(client, world, monkeypatch):
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "t2@x.com")
    assert recognize(client, world["active"]).status_code == 404


def test_students_cannot_recognize(client, world, monkeypatch):
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "s1@x.com")
    assert recognize(client, world["active"]).status_code == 403


def test_response_never_contains_embeddings(client, world, monkeypatch):
    fake_faces(monkeypatch, [[1, 0, 0]])
    login(client, "t1@x.com")
    assert "embedding" not in recognize(client, world["active"]).text