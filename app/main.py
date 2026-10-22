
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import admin_academic, auth

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="SmartAttend", version="0.1.0")
app.include_router(auth.router)
app.include_router(admin_academic.router)
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
