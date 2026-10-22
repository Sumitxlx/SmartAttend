# Database Schema

SQLite for development (PostgreSQL possible later). Managed with Alembic migrations.

| Table | Purpose |
|---|---|
| users | Login accounts for all roles (admin, teacher, student) |
| departments | Academic departments |
| classes | A class/section: department + semester + year |
| teachers | Teacher profile, linked 1:1 to a user |
| students | Student profile, linked 1:1 to a user, belongs to one class |
| subjects | Courses taught in a department/semester |
| teaching_assignments | Teacher + subject + class |
| attendance_sessions | One lecture meeting (scheduled/active/finalized) |
| attendance_records | One student in one session (present/absent/uncertain) |
| face_embeddings | Face fingerprints; server-side only |
| correction_requests | Student requests to change a record |
| audit_logs | Append-only history of important actions |

## Key rules
- email unique; passwords stored only as hashes.
- One attendance record per (session, student).
- A student belongs to exactly one class (known limitation: electives).
- Embeddings are never returned by any API.

## Migrations
- 001 initial schema