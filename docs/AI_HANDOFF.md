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

cat > docs/AI_HANDOFF.md << 'EOF'
# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Frontend: plain HTML/CSS/JS in app/static. Planned: OpenCV + DeepFace (ArcFace).
Dev machine: macOS, VS Code, GitHub repo Sumitxlx/SmartAttend.

## Done and verified (seen working)
- M1: /health returns ok; pushed to GitHub.
- M2: 13 tables via Alembic migration 0d15a82347ea; model tests passed.
- M3: auth (Argon2, HttpOnly cookie, role guard); tests passed; admin created.
- M4: design tokens, light/dark theme, login page. 29 tests passed. Browser login 200 and logout 200 seen in server log. Not yet confirmed: reload keeps session, theme toggle, responsive layout.

## Milestone 5a (admin API: departments, classes, subjects): written, awaiting verification
- Update after pytest (expected about 72 passed) and the /docs walkthrough.

## Next
- M5b: admin API for teachers, students (create user + profile), teaching assignments.
- M6: admin screens.

## Known issues
- httpx/starlette TestClient deprecation warning (harmless).
- First admin is created with `python -m scripts.create_admin`; scripts.reset_password exists if forgotten.
- Lists are not paginated yet.
EOF