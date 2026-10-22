# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Frontend: plain HTML/CSS/JS in app/static (JSON API under /admin/... and /teacher/..., HTML screens under /manage/...).
Planned: OpenCV + DeepFace (ArcFace).
Dev machine: macOS, VS Code, GitHub repo Sumitxlx/SmartAttend.

## Done and verified (automated tests)
- M1: /health ok.
- M2: 13 tables via migration 0d15a82347ea; model tests passed.
- M3: auth, role guard; admin login verified in browser.
- M4: login page and design tokens; tests passed.
- M5a: departments, classes, subjects API; 72 tests; smoke script 9/9 PASS; audit log verified.
- M5b: teachers, students, assignments API; 91 tests passed.
- M6a: admin layout, shared table/toast; 92 tests passed.
- M6b: departments and classes screens; 94 tests; add/edit/delete verified in browser.
- M6c: subjects and assignments screens; 96 tests passed.
- M6d: teachers and students screens; 98 tests passed.
- M7: manual attendance session API (rules in attendance_service.py); 111 tests passed.

## Not yet verified
- M4: reload keeps session, theme toggle, narrow screen.
- M6a: sidebar, sign-out, narrow-screen checks.
- M5b: /docs walkthrough (teacher create, assignment create, teacher 403).
- M6c/M6d: browser add/filter checks for teachers, students and assignments.
- M7: /docs walkthrough of sessions (start, mark, finalize, 409 on repeat).

## Next
- M7b: teacher attendance screen (pick assignment, start session, mark students, finalize).
- M8: student portal (percentages, history, goal calculator, correction requests).
- M9: face enrollment and live recognition, with uncertain-match handling.
- M10: corrections, reports, audit viewer.
- M11: face-recognition evaluation on real photos.
- M12: security review, deployment, demo.

## Known gaps
- Teachers and students cannot be edited or deleted yet (API and screens).
- Lists are not paginated.
- Sessions use the server's local date.
- httpx/starlette TestClient deprecation warning (harmless).
- First admin: `python -m scripts.create_admin`; forgotten password: `python -m scripts.reset_password`.

## Verification update
- M7: 111 tests passed. Verified.
- M7b: 113 tests passed (includes the today-session lookup). Browser reload check not yet confirmed.
- Known UI issue: the screen's Class/Semester form error was vague; fixed in api.js to name the field.
