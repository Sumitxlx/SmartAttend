# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Frontend: plain HTML/CSS/JS in app/static. Planned: OpenCV + DeepFace (ArcFace).
Dev machine: macOS, VS Code, GitHub repo Sumitxlx/SmartAttend.

## Done and verified (seen working)
- M1: /health ok; pushed.
- M2: 13 tables via migration 0d15a82347ea; model tests passed.
- M3: auth, role guard; tests passed; admin login verified in browser (200, then logout 200).
- M4: login page and design tokens; 29 tests passed. Reload/theme/responsive checks not yet confirmed.
- M5a: departments, classes, subjects API; 72 tests passed; smoke script all 9 PASS; audit log verified.

## Milestone 5b (teachers, students, teaching assignments): written, awaiting verification
- Update after pytest (expected about 88 passed) and the /docs checks.

## Revised roadmap
- M5b: people and assignments (current)
- M6: admin screens for the above
- M7: teacher attendance session, manual marking, finalize (working attendance site, no camera)
- M8: student portal
- M9: face enrollment and live recognition
- M10: corrections, reports, audit viewer
- M11: face-recognition evaluation
- M12: security review, deployment, demo

## Known issues
- httpx/starlette TestClient deprecation warning (harmless).
- Lists are not paginated.
- First admin: `python -m scripts.create_admin`; forgotten password: `python -m scripts.reset_password`.
