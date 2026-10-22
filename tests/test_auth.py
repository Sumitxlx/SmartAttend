from datetime import timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import (
    ACCESS_COOKIE_NAME,
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.time import utcnow
from app.models import User, UserRole
from app.routers import auth as auth_router

# A small app just for testing: the real auth router plus two protected routes.
auth_test_app = FastAPI()
auth_test_app.include_router(auth_router.router)


@auth_test_app.get("/admin-only")
def admin_only(user: User = Depends(require_roles(UserRole.admin))):
    return {"ok": True}


@auth_test_app.get("/teacher-or-admin")
def teacher_or_admin(user: User = Depends(require_roles(UserRole.teacher, UserRole.admin))):
    return {"ok": True}


PASSWORD = "correct-horse-battery"
EMAIL = "u@example.com"


def make_user(db, email=EMAIL, role=UserRole.student, password=PASSWORD, active=True):
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name="Test User",
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    auth_test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(auth_test_app) as c:
        yield c
    auth_test_app.dependency_overrides.clear()


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def cookie_header(token: str) -> dict:
    return {"Cookie": f"{ACCESS_COOKIE_NAME}={token}"}


def test_password_hash_roundtrip():
    hashed = hash_password("my-secret-password")
    assert hashed != "my-secret-password"
    assert hashed.startswith("$argon2")
    assert verify_password("my-secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_login_success_sets_cookie_and_hides_hash(client, db_session):
    make_user(db_session)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == EMAIL
    assert "password" not in body
    assert "password_hash" not in body
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_login_wrong_password(client, db_session):
    make_user(db_session)
    r = login(client, password="wrong-password")
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_gives_same_message(client, db_session):
    make_user(db_session)
    wrong_pw = login(client, password="wrong-password")
    unknown = login(client, email="nobody@example.com")
    assert unknown.status_code == 401
    assert unknown.json() == wrong_pw.json()


def test_login_inactive_user_rejected(client, db_session):
    make_user(db_session, active=False)
    assert login(client).status_code == 401


def test_login_email_is_case_insensitive(client, db_session):
    make_user(db_session)
    assert login(client, email="  U@Example.COM ").status_code == 200


def test_me_requires_login(client):
    assert client.get("/auth/me").status_code == 401


def test_me_after_login(client, db_session):
    make_user(db_session, role=UserRole.teacher)
    login(client)
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"


def test_logout_clears_session(client, db_session):
    make_user(db_session)
    login(client)
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401


def test_tampered_token_rejected(client, db_session):
    user = make_user(db_session)
    token = create_access_token(user.id)
    r = client.get("/auth/me", headers=cookie_header(token + "x"))
    assert r.status_code == 401


def test_expired_token_rejected(client, db_session):
    user = make_user(db_session)
    expired = jwt.encode(
        {"sub": str(user.id), "exp": utcnow() - timedelta(minutes=1)},
        settings.secret_key,
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers=cookie_header(expired)).status_code == 401


def test_valid_token_of_deactivated_user_rejected(client, db_session):
    user = make_user(db_session)
    token = create_access_token(user.id)
    assert client.get("/auth/me", headers=cookie_header(token)).status_code == 200
    user.is_active = False
    db_session.commit()
    assert client.get("/auth/me", headers=cookie_header(token)).status_code == 401


def test_protected_route_without_login_is_401(client):
    assert client.get("/admin-only").status_code == 401


@pytest.mark.parametrize(
    "role, path, expected",
    [
        (UserRole.admin, "/admin-only", 200),
        (UserRole.teacher, "/admin-only", 403),
        (UserRole.student, "/admin-only", 403),
        (UserRole.teacher, "/teacher-or-admin", 200),
        (UserRole.admin, "/teacher-or-admin", 200),
        (UserRole.student, "/teacher-or-admin", 403),
    ],
)
def test_role_enforcement(client, db_session, role, path, expected):
    make_user(db_session, role=role)
    assert login(client).status_code == 200
    assert client.get(path).status_code == expected