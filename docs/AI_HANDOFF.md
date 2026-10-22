# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Planned: HTML/CSS/vanilla JS frontend served by FastAPI; OpenCV + DeepFace (ArcFace).
Dev machine: macOS, VS Code, GitHub repo Sumitxlx/SmartAttend.

## Done and verified (seen working)
- M1: /health returns ok; test passed; pushed to GitHub.
- M2: 13 tables created by Alembic migration 0d15a82347ea; model tests passed.

## Milestone 3 (auth): written, awaiting verification
- Update this section only after pytest and the manual /docs check results are seen.

## Next
- M4: UI design system foundation + login page.

## Known issues
- httpx/starlette TestClient deprecation warning (harmless).
- No admin-management API yet; the first admin is created with `python -m scripts.create_admin`.