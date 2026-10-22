# AI Handoff

## Project
SmartAttend: college attendance web app with face recognition. Portals: Admin, Teacher, Student.

## Stack
Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite, Argon2, PyJWT.
Frontend: plain HTML/CSS/JS in app/static. JSON API under /admin, /teacher, /student. HTML screens under /manage, /teach, /portal.
Planned: OpenCV + DeepFace (ArcFace).

## Done (automated tests passing)
- M1 health; M2 schema (13 tables); M3 auth and roles; M4 login page and theme.
- M5a departments, classes, subjects API (smoke script 9/9, audit verified).
- M5b teachers, students, assignments API.
- M6a-d admin screens (departments and classes add/edit/delete verified in browser).
- M7 manual attendance API; M7b teacher attendance screen.
- M8a student summary, history, goal API; M8b corrections API.
- M8c student and teacher correction screens (last pytest count: about 141).

## Not yet verified in browser
- M4: reload keeps session, theme toggle, narrow screen.
- M6a: sidebar, sign-out, narrow screen.
- M5b: /docs walkthrough (teacher create, assignment, teacher 403).
- M6c/M6d: teacher and student add, assignment dropdown, class filter.
- M7b: reload keeps the mark on an active session.
- M8c: student dashboard and teacher correction approve/reject in browser.

## Next
- M9: face enrollment and live recognition (DeepFace + ArcFace), with uncertain-match review and manual fallback.
- M10: reports and audit viewer.
- M11: face-recognition evaluation on real photos (accuracy, false accepts and rejects, threshold choice).
- M12: security review, deployment, demo script.

## Known gaps
- Teachers and students cannot be edited or deleted.
- Lists are not paginated.
- Sessions use the server's local date.
- Uncertain attendance status is not produced yet; it arrives with M9.
- TestClient deprecation warning (harmless).
- Admin recovery: `python -m scripts.create_admin`, `python -m scripts.reset_password`.

## Unverified as of M9e
- M9b real ArcFace enrollment on real photos: NOT yet tested (fake-embedding tests only). Deferred by choice.
- M9c/M9d live matching with a real camera: NOT yet tested.
- /teach/review browser check: not yet confirmed.
- Recognition thresholds 0.32 / 0.25: starting values, to be measured in M11.
