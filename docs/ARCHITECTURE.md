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
