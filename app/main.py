from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import admin_academic, admin_people, auth, teacher_attendance

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="SmartAttend", version="0.1.0")

app.include_router(auth.router)
app.include_router(admin_academic.router)
app.include_router(admin_people.router)
app.include_router(teacher_attendance.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health_check():
    """Simple endpoint to confirm the server is running."""
    return {"status": "ok", "app": "SmartAttend"}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/admin", include_in_schema=False)
def admin_dashboard():
    return FileResponse(STATIC_DIR / "admin" / "dashboard.html")


@app.get("/manage/departments", include_in_schema=False)
def manage_departments():
    return FileResponse(STATIC_DIR / "admin" / "departments.html")


@app.get("/manage/classes", include_in_schema=False)
def manage_classes():
    return FileResponse(STATIC_DIR / "admin" / "classes.html")


@app.get("/manage/subjects", include_in_schema=False)
def manage_subjects():
    return FileResponse(STATIC_DIR / "admin" / "subjects.html")


@app.get("/manage/assignments", include_in_schema=False)
def manage_assignments():
    return FileResponse(STATIC_DIR / "admin" / "assignments.html")


@app.get("/manage/teachers", include_in_schema=False)
def manage_teachers():
    return FileResponse(STATIC_DIR / "admin" / "teachers.html")


@app.get("/manage/students", include_in_schema=False)
def manage_students():
    return FileResponse(STATIC_DIR / "admin" / "students.html")

@app.get("/teach/attendance", include_in_schema=False)
def teacher_attendance_page():
    return FileResponse(STATIC_DIR / "teacher" / "attendance.html")