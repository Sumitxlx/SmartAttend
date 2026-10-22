# Project Spec

## Goal
Web app for college attendance using face recognition, with Admin, Teacher, Student portals.

## Roles
- Admin: manage users, departments, classes, subjects, teaching assignments; view reports and audit log.
- Teacher: start a session for an assigned class/subject, see live recognition, review uncertain matches, correct manually, finalize.
- Student: view own attendance %, per-subject totals, history, warnings; request corrections.

## Out of scope (for now)
- Mobile app, electives across classes, email notifications.

## Non-functional
- Permissions enforced on the backend.
- No passwords or embeddings in API responses.
- Every feature has a focused test.