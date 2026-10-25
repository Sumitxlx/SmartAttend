# Architecture

FastAPI app (app/main.py) with routers per area. Current routers: auth.

Layers: routers (HTTP) -> services (business logic) -> models (SQLAlchemy).
Shared code in app/core: config, database, security (hashing, tokens), deps (current user, role guard).
Auth flow: POST /auth/login sets an HttpOnly cookie; get_current_user reads it on each request.

cat >> docs/ARCHITECTURE.md << 'EOF'

## Admin API (M5a)
app/routers/admin_academic.py: departments, classes, subjects (list, create, update, delete) under /admin.
Role guard applied router-wide (admin only). app/services/audit.py writes an audit_logs row in the same transaction as each change.
Rule violations (duplicates, in-use deletes) are caught from database constraints and returned as 409.
EOF

cat >> docs/SECURITY.md << 'EOF'
- Admin routes: backend-enforced admin-only guard, tested for 401 (anonymous) and 403 (teacher, student).
- Admin changes to departments, classes and subjects are written to audit_logs (who, what, when).
EOF
## People and assignments (M5b)
app/routers/admin_people.py: teachers and students (login account + profile created in one transaction), and teaching assignments.
Assignments enforce same-department and same-semester rules. Deleting an assignment that has attendance records returns 409 (enforced by the database, tested once sessions exist).

## Admin screens (M6b)
- /admin/... is the JSON API. /manage/... serves HTML screens. Keeping them apart stops a browser URL from returning raw JSON by accident.
- Departments and classes screens use the shared table.js (with Edit and Delete actions) and call the already-tested API.
- Subjects, teachers, students and assignments screens are not built yet; their nav links return 404.

## Admin screens (M6c)
- Subjects screen: add, edit, delete; uses the same table.js pattern as departments and classes.
- Assignments screen: create and remove only (assignments are not edited). Shows a setup note when teachers, subjects or classes are missing.

## Admin screens (M6d)
- Teachers and Students screens: create and list only. The API has no update or delete routes for people yet, so the screens offer neither.
- Students screen has a class filter that uses the API's class_id query parameter.

## Attendance backend, manual (M7)
- app/services/attendance_service.py holds the attendance rules; app/routers/teacher_attendance.py only maps HTTP to those rules.
- Teacher-only routes under /teacher: list own assignments, start a session, view, mark present/absent, finalize.
- One session per assignment per day. Finalized sessions are locked. Unmarked students are marked absent on finalize.

## Student attendance backend (M8a)
- app/services/student_service.py: percentages, history, low-attendance threshold (75%), goal calculator. Finalized sessions only.
- Student routes under /student. The student is taken from the login session, never from the URL.

## Corrections (M8b)
- app/services/correction_service.py: students request a change to a finalized record; the owning teacher approves or rejects.
- Approval changes the attendance record and writes an audit row. Rejection changes only the request.
- Routes: /student/corrections (create, list own) and /teacher/corrections (pending, approve, reject).

## Teacher attendance screen (M7b)
- /teach/attendance uses the teacher JSON API. GET /teacher/assignments/{id}/today lets the screen resume today's session after a reload.

## Student and teacher screens (M8c)
- /portal/student: overall and per-subject percentages, low-attendance warning, goal calculator, correction request form, history, and correction status.
- /teach/corrections: pending requests for the teacher's own classes, with approve and reject.
- Screens only display and call the API. The rules stay in the service files.

## Face recognition rules (M9a)
- app/services/face_quality.py: photo rules (one face, brightness, sharpness, face size). Pure logic.
- app/services/face_embedding.py: ArcFace embedding via DeepFace (imported lazily), averaging 5 photos into one unit-length template, minimum 3 usable photos.
- Tests use fake embeddings; the model is not downloaded during the test run.

## Live face matching (M9c)
- app/services/face_matcher.py: cosine similarity and thresholds (present >= 0.32, uncertain >= 0.25, else unknown).
- app/services/recognition_service.py: matches each frame against templates of the session's class only; writes face records; never overwrites manual marks.
- POST /teacher/sessions/{id}/recognize accepts one JPEG or PNG frame and returns results without embeddings.
- Thresholds are starting values; M11 measures them on real photos.

## Uncertain-match review (M9d)
- Teachers list and resolve uncertain records for their own active sessions. Resolving sets the method to manual and is audit-logged.
- Finalize is blocked (409) while any uncertain record remains.

## Uncertain-match review screen (M9e)
- /teach/review lists a session's uncertain matches and lets the teacher mark each present or absent. It redraws from the server's list after every change.
- The session ID is typed in for now; M9f will link to it from the attendance screen.

## Role-based home and teacher menu (Navigation A)
- After login, admin goes to /admin, teacher to /teach/home, student to /portal/student (login.js HOME_BY_ROLE).
- /teach/home is a menu linking to the teacher's task pages. Links are convenience only; the backend still enforces roles.

## Teacher face enrollment, backend (part 1)
- POST /teacher/students/{id}/face-enrollment: teachers enroll students in classes they teach. Other students return 404.
- Same photo rules and template storage as admin enrollment. Duplicated upload code to be merged into one helper later.
