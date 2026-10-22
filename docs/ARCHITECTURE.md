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
