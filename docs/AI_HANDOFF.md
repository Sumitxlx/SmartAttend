# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Frontend: plain HTML/CSS/JS in app/static (JSON API under /admin/..., HTML screens under /manage/...).
Planned: OpenCV + DeepFace (ArcFace).
Dev machine: macOS, VS Code, GitHub repo Sumitxlx/SmartAttend.

## Done and verified
- M1: /health ok; pushed.
- M2: 13 tables via migration 0d15a82347ea; model tests passed.
- M3: auth, role guard; tests passed; admin login verified (200, logout 200).
- M4: login page and design tokens; tests passed. Reload/theme/responsive checks not confirmed.
- M5a: departments, classes, subjects API; 72 tests passed; smoke script all 9 PASS; audit log verified.
- M5b: teachers, students, teaching assignments API; 91 tests passed. Browser /docs checks skipped by choice.
- M6a: admin layout, shared table and toast helpers; 92 tests passed.
- M6b: departments and classes screens; 94 tests passed; add/edit/delete verified in browser.

## Not yet verified in browser
- M4 reload keeps session, theme toggle, narrow screen.
- M6a sidebar/sign-out/narrow-screen checks (user skipped).
- M5b /docs walkthrough (teacher create, assignment create, teacher 403).

## Next
- M6c: subjects screen and teaching assignments screen.
- M6d: teachers and students screens.
- M6e: role-based redirects after login.
- M7: teacher attendance session, manual marking, finalize.
- M8: student portal.
- M9: face enrollment and live recognition.
- M10: corrections, reports, audit viewer.
- M11: face-recognition evaluation.
- M12: security review, deployment, demo.

## Known issues
- httpx/starlette TestClient deprecation warning (harmless).
- Lists are not paginated.
- Subjects, teachers, students and assignments nav links return 404 until their screens exist.
- First admin: `python -m scripts.create_admin`; forgotten password: `python -m scripts.reset_password`.
