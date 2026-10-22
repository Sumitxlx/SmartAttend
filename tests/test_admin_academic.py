import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import AuditLog, Department, User, UserRole

PASSWORD = "correct-horse-battery"

DEPT_BODY = {"code": "ECE", "name": "Electronics"}
SUBJECT_BODY = {"code": "EC101", "name": "Circuits", "department_id": 1, "semester": 3}

# (method, path, body) for a sample of protected routes
PROTECTED = [
    ("GET", "/admin/departments", None),
    ("POST", "/admin/departments", DEPT_BODY),
    ("PUT", "/admin/departments/1", DEPT_BODY),
    ("DELETE", "/admin/departments/1", None),
    ("GET", "/admin/classes", None),
    ("GET", "/admin/subjects", None),
    ("POST", "/admin/subjects", SUBJECT_BODY),
]


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login_as(client, db, role, email=None):
    email = email or f"{role.value}@example.com"
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=f"Test {role.value}",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    return user


@pytest.fixture()
def admin(client, db_session):
    """Logs the test client in as an admin and returns that user."""
    return login_as(client, db_session, UserRole.admin)


def make_dept(client, code="CSE", name="Computer Science"):
    r = client.post("/admin/departments", json={"code": code, "name": name})
    assert r.status_code == 201, r.text
    return r.json()


def class_body(dept_id, **overrides):
    body = {"name": "A", "department_id": dept_id, "semester": 5, "academic_year": "2026-2027"}
    body.update(overrides)
    return body


# ---------- permissions ----------
@pytest.mark.parametrize("method, path, body", PROTECTED)
def test_unauthenticated_gets_401(client, method, path, body):
    assert client.request(method, path, json=body).status_code == 401


@pytest.mark.parametrize("role", [UserRole.teacher, UserRole.student])
@pytest.mark.parametrize("method, path, body", PROTECTED)
def test_non_admin_gets_403(client, db_session, role, method, path, body):
    login_as(client, db_session, role)
    assert client.request(method, path, json=body).status_code == 403


def test_forbidden_post_creates_nothing(client, db_session):
    login_as(client, db_session, UserRole.teacher)
    client.post("/admin/departments", json=DEPT_BODY)
    assert db_session.scalars(select(Department)).all() == []


# ---------- departments ----------
def test_admin_creates_department_and_code_is_uppercased(client, admin):
    r = client.post("/admin/departments", json={"code": " cse ", "name": " Computer Science "})
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "CSE"
    assert body["name"] == "Computer Science"
    assert isinstance(body["id"], int)


def test_duplicate_department_code_is_409(client, admin):
    make_dept(client)
    r = client.post("/admin/departments", json={"code": "cse", "name": "Something Else"})
    assert r.status_code == 409


def test_duplicate_department_name_is_409(client, admin):
    make_dept(client)
    r = client.post("/admin/departments", json={"code": "ECE", "name": "Computer Science"})
    assert r.status_code == 409


@pytest.mark.parametrize(
    "body",
    [{"code": "C", "name": "Computer Science"}, {"code": "CSE", "name": " "}],
)
def test_department_validation_is_422(client, admin, body):
    assert client.post("/admin/departments", json=body).status_code == 422


def test_list_departments(client, admin):
    make_dept(client, "ECE", "Electronics")
    make_dept(client, "CSE", "Computer Science")
    r = client.get("/admin/departments")
    assert r.status_code == 200
    assert [d["code"] for d in r.json()] == ["CSE", "ECE"]  # sorted by code


def test_update_department(client, admin):
    dept = make_dept(client)
    r = client.put(
        f"/admin/departments/{dept['id']}",
        json={"code": "CSE", "name": "Computer Science and Engineering"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Computer Science and Engineering"

    other = make_dept(client, "ECE", "Electronics")
    clash = client.put(
        f"/admin/departments/{other['id']}", json={"code": "CSE", "name": "Electronics"}
    )
    assert clash.status_code == 409


def test_update_missing_department_is_404(client, admin):
    assert client.put("/admin/departments/999", json=DEPT_BODY).status_code == 404


def test_delete_department(client, admin):
    dept = make_dept(client)
    assert client.delete(f"/admin/departments/{dept['id']}").status_code == 204
    assert client.delete(f"/admin/departments/{dept['id']}").status_code == 404
    assert client.get("/admin/departments").json() == []


def test_delete_department_in_use_is_409(client, admin):
    dept = make_dept(client)
    assert client.post("/admin/classes", json=class_body(dept["id"])).status_code == 201
    assert client.delete(f"/admin/departments/{dept['id']}").status_code == 409
    assert len(client.get("/admin/departments").json()) == 1


# ---------- classes ----------
def test_class_requires_existing_department(client, admin):
    assert client.post("/admin/classes", json=class_body(999)).status_code == 422


@pytest.mark.parametrize("year", ["2026-2028", "2026", "abcd-efgh"])
def test_class_academic_year_must_be_consecutive(client, admin, year):
    dept = make_dept(client)
    r = client.post("/admin/classes", json=class_body(dept["id"], academic_year=year))
    assert r.status_code == 422


@pytest.mark.parametrize("semester", [0, 13])
def test_class_semester_must_be_1_to_12(client, admin, semester):
    dept = make_dept(client)
    r = client.post("/admin/classes", json=class_body(dept["id"], semester=semester))
    assert r.status_code == 422


def test_duplicate_class_is_409(client, admin):
    dept = make_dept(client)
    assert client.post("/admin/classes", json=class_body(dept["id"])).status_code == 201
    assert client.post("/admin/classes", json=class_body(dept["id"])).status_code == 409


def test_list_classes_filter_by_department(client, admin):
    cse = make_dept(client)
    ece = make_dept(client, "ECE", "Electronics")
    client.post("/admin/classes", json=class_body(cse["id"]))
    client.post("/admin/classes", json=class_body(ece["id"]))
    assert len(client.get("/admin/classes").json()) == 2
    only_cse = client.get(f"/admin/classes?department_id={cse['id']}").json()
    assert len(only_cse) == 1
    assert only_cse[0]["department_id"] == cse["id"]


# ---------- subjects ----------
def test_subject_create_and_duplicate_code(client, admin):
    dept = make_dept(client)
    body = {"code": "cs501", "name": "DBMS", "department_id": dept["id"], "semester": 5}
    r = client.post("/admin/subjects", json=body)
    assert r.status_code == 201
    assert r.json()["code"] == "CS501"
    assert client.post("/admin/subjects", json=body).status_code == 409


def test_subject_requires_existing_department(client, admin):
    body = {"code": "CS501", "name": "DBMS", "department_id": 999, "semester": 5}
    assert client.post("/admin/subjects", json=body).status_code == 422


# ---------- audit log ----------
def test_audit_log_records_changes(client, db_session, admin):
    dept = make_dept(client)
    client.put(
        f"/admin/departments/{dept['id']}",
        json={"code": "CSE", "name": "Computer Science and Engineering"},
    )
    client.delete(f"/admin/departments/{dept['id']}")

    logs = db_session.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    assert [log.action for log in logs] == [
        "department.created",
        "department.updated",
        "department.deleted",
    ]
    assert all(log.user_id == admin.id for log in logs)