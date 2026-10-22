import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models import AuditLog, User, UserRole

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def add_user(db, email, role):
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=f"{role.value} user",
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def login(client, email):
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


@pytest.fixture()
def admin_client(client, db_session):
    add_user(db_session, "admin@example.com", UserRole.admin)
    login(client, "admin@example.com")
    return client


@pytest.fixture()
def structure(admin_client):
    """Two departments, a CSE class and a CSE subject, all in semester 5."""
    c = admin_client
    cse = c.post("/admin/departments", json={"code": "CSE", "name": "Computer Science"}).json()
    ece = c.post("/admin/departments", json={"code": "ECE", "name": "Electronics"}).json()
    cls = c.post(
        "/admin/classes",
        json={"name": "A", "department_id": cse["id"], "semester": 5, "academic_year": "2026-2027"},
    ).json()
    subj = c.post(
        "/admin/subjects",
        json={"code": "CS501", "name": "DBMS", "department_id": cse["id"], "semester": 5},
    ).json()
    return {"cse": cse["id"], "ece": ece["id"], "class": cls["id"], "subject": subj["id"]}


def teacher_body(dept_id, **overrides):
    body = {
        "email": "t1@example.com",
        "password": PASSWORD,
        "full_name": "Teacher One",
        "employee_id": "EMP1",
        "department_id": dept_id,
    }
    body.update(overrides)
    return body


def student_body(class_id, **overrides):
    body = {
        "email": "s1@example.com",
        "password": PASSWORD,
        "full_name": "Student One",
        "roll_number": "R001",
        "class_id": class_id,
    }
    body.update(overrides)
    return body


# ---------- permissions ----------
@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/admin/teachers"),
        ("POST", "/admin/teachers"),
        ("GET", "/admin/students"),
        ("POST", "/admin/students"),
        ("GET", "/admin/teaching-assignments"),
        ("POST", "/admin/teaching-assignments"),
    ],
)
def test_anonymous_gets_401(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_teacher_cannot_use_admin_routes(admin_client, structure, client, db_session):
    admin_client.post("/admin/teachers", json=teacher_body(structure["cse"]))
    admin_client.post("/auth/logout")
    login(client, "t1@example.com")
    assert client.get("/admin/teachers").status_code == 403
    assert client.post("/admin/students", json={}).status_code == 403


# ---------- teachers ----------
def test_created_teacher_can_log_in_and_password_is_hashed(admin_client, structure, db_session):
    r = admin_client.post("/admin/teachers", json=teacher_body(structure["cse"]))
    assert r.status_code == 201
    assert "password" not in r.json() and "password_hash" not in r.json()

    user = db_session.scalar(select(User).where(User.email == "t1@example.com"))
    assert user.role == UserRole.teacher
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)

    admin_client.post("/auth/logout")
    login(admin_client, "t1@example.com")
    assert admin_client.get("/auth/me").json()["role"] == "teacher"


def test_duplicate_teacher_email_is_409_and_leaves_no_orphan(admin_client, structure, db_session):
    admin_client.post("/admin/teachers", json=teacher_body(structure["cse"]))
    r = admin_client.post(
        "/admin/teachers",
        json=teacher_body(structure["cse"], employee_id="EMP2"),
    )
    assert r.status_code == 409
    assert db_session.scalar(select(func.count(User.id))) == 2  # admin + one teacher


def test_duplicate_employee_id_rolls_back_the_user_too(admin_client, structure, db_session):
    admin_client.post("/admin/teachers", json=teacher_body(structure["cse"]))
    r = admin_client.post(
        "/admin/teachers",
        json=teacher_body(structure["cse"], email="t2@example.com"),
    )
    assert r.status_code == 409
    # The second user must not have been saved when its profile failed.
    assert db_session.scalar(select(func.count(User.id))) == 2


def test_teacher_validation(admin_client, structure):
    r = admin_client.post(
        "/admin/teachers", json=teacher_body(structure["cse"], password="short")
    )
    assert r.status_code == 422
    r = admin_client.post(
        "/admin/teachers", json=teacher_body(structure["cse"], email="not-an-email")
    )
    assert r.status_code == 422


# ---------- students ----------
def test_create_student_and_list_by_class(admin_client, structure):
    r = admin_client.post("/admin/students", json=student_body(structure["class"]))
    assert r.status_code == 201
    assert r.json()["class_id"] == structure["class"]
    assert "password" not in r.json()

    listed = admin_client.get(f"/admin/students?class_id={structure['class']}").json()
    assert [s["roll_number"] for s in listed] == ["R001"]


def test_student_needs_existing_class(admin_client):
    r = admin_client.post("/admin/students", json=student_body(999))
    assert r.status_code == 422


def test_duplicate_roll_number_is_409(admin_client, structure):
    admin_client.post("/admin/students", json=student_body(structure["class"]))
    r = admin_client.post(
        "/admin/students",
        json=student_body(structure["class"], email="s2@example.com"),
    )
    assert r.status_code == 409


# ---------- teaching assignments ----------
def test_assignment_created_and_duplicate_rejected(admin_client, structure):
    t = admin_client.post("/admin/teachers", json=teacher_body(structure["cse"])).json()
    body = {"teacher_id": t["id"], "subject_id": structure["subject"], "class_id": structure["class"]}
    assert admin_client.post("/admin/teaching-assignments", json=body).status_code == 201
    assert admin_client.post("/admin/teaching-assignments", json=body).status_code == 409


def test_assignment_rejects_teacher_from_other_department(admin_client, structure):
    t = admin_client.post(
        "/admin/teachers",
        json=teacher_body(structure["ece"], email="ece@example.com", employee_id="E9"),
    ).json()
    body = {"teacher_id": t["id"], "subject_id": structure["subject"], "class_id": structure["class"]}
    assert admin_client.post("/admin/teaching-assignments", json=body).status_code == 422


def test_assignment_rejects_semester_mismatch(admin_client, structure):
    t = admin_client.post("/admin/teachers", json=teacher_body(structure["cse"])).json()
    sem3 = admin_client.post(
        "/admin/classes",
        json={"name": "B", "department_id": structure["cse"], "semester": 3, "academic_year": "2026-2027"},
    ).json()
    body = {"teacher_id": t["id"], "subject_id": structure["subject"], "class_id": sem3["id"]}
    r = admin_client.post("/admin/teaching-assignments", json=body)
    assert r.status_code == 422
    assert "semester" in r.json()["detail"]


def test_delete_assignment(admin_client, structure):
    t = admin_client.post("/admin/teachers", json=teacher_body(structure["cse"])).json()
    body = {"teacher_id": t["id"], "subject_id": structure["subject"], "class_id": structure["class"]}
    a = admin_client.post("/admin/teaching-assignments", json=body).json()
    assert admin_client.delete(f"/admin/teaching-assignments/{a['id']}").status_code == 204
    assert admin_client.get("/admin/teaching-assignments").json() == []
    assert admin_client.delete(f"/admin/teaching-assignments/{a['id']}").status_code == 404


# ---------- audit ----------
def test_audit_records_people_and_never_passwords(admin_client, structure, db_session):
    t = admin_client.post("/admin/teachers", json=teacher_body(structure["cse"])).json()
    admin_client.post("/admin/students", json=student_body(structure["class"]))
    admin_client.post(
        "/admin/teaching-assignments",
        json={"teacher_id": t["id"], "subject_id": structure["subject"], "class_id": structure["class"]},
    )
    actions = [log.action for log in db_session.scalars(select(AuditLog)).all()]
    assert "teacher.created" in actions
    assert "student.created" in actions
    assert "teaching_assignment.created" in actions
    for log in db_session.scalars(select(AuditLog)).all():
        assert PASSWORD not in (log.details or "")