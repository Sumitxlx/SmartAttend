import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_redirects_to_login():
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/login"


def test_login_page_is_served():
    r = client.get("/login")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<form" in r.text
    assert "<script>" not in r.text  # no inline scripts, keeps a strict CSP possible later


@pytest.mark.parametrize(
    "path",
    [
        "/static/css/tokens.css",
        "/static/css/base.css",
        "/static/js/theme.js",
        "/static/js/api.js",
        "/static/js/login.js",
    ],
)
def test_static_assets_are_served(path):
    assert client.get(path).status_code == 200

def test_admin_dashboard_is_served_without_inline_scripts():
    r = client.get("/admin")
    assert r.status_code == 200
    assert "<script>" not in r.text
    assert "admin-dashboard.js" in r.text

@pytest.mark.parametrize("path", ["/manage/departments", "/manage/classes"])
def test_admin_management_pages_served_without_inline_scripts(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<script>" not in r.text

@pytest.mark.parametrize("path", ["/manage/subjects", "/manage/assignments"])
def test_subject_and_assignment_pages_served_without_inline_scripts(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<script>" not in r.text

@pytest.mark.parametrize("path", ["/manage/teachers", "/manage/students"])
def test_teacher_and_student_pages_served_without_inline_scripts(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<script>" not in r.text

def test_teacher_attendance_page_served_without_inline_scripts():
    r = client.get("/teach/attendance")
    assert r.status_code == 200
    assert "<script>" not in r.text
    assert "teacher-attendance.js" in r.text

@pytest.mark.parametrize("path", ["/portal/student", "/teach/corrections"])
def test_portal_pages_served_without_inline_scripts(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<script>" not in r.text

def test_review_page_served_without_inline_scripts():
    r = client.get("/teach/review")
    assert r.status_code == 200
    assert "<script>" not in r.text
    assert "teacher-review.js" in r.text

def test_camera_test_page_served_without_inline_scripts():
    r = client.get("/teach/camera-test")
    assert r.status_code == 200
    assert "<script>" not in r.text
    assert "camera-test.js" in r.text