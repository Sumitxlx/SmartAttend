# Security

## Implemented and tested (Milestone 3)
- Passwords hashed with Argon2; plaintext never stored or returned.
- Login token in an HttpOnly, SameSite=Lax cookie; Secure flag via COOKIE_SECURE.
- Token holds only the user id; user and active status looked up on every request.
- Generic login error (no email enumeration); dummy hash check for unknown emails.
- SECRET_KEY required, at least 32 characters, no default; kept in .env (git-ignored).
- Backend role guard: require_roles(...) returns 401 if not logged in, 403 if wrong role.

## Known gaps (planned)
- No login rate limiting or lockout yet.
- No CSRF token; relying on SameSite=Lax plus JSON-only endpoints. Review later.
- No password change/reset flow.
- Embeddings are not yet stored or encrypted (face milestone).
- HTTPS and COOKIE_SECURE=true required in deployment.