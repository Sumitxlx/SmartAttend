"""Smoke test for the admin API. Start the server first, then run from the project root:
    python -m scripts.smoke_admin
"""
import getpass
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

# A cookie jar keeps the login session between calls, like a browser would.
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener.open(request) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, raw.decode(errors="replace")


def check(label: str, expected: int, status: int, payload: object) -> bool:
    ok = status == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label} (expected {expected}, got {status})")
    if not ok:
        print(f"      response: {payload}")
    return ok


def main() -> None:
    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password: ")

    status, body = call("POST", "/auth/login", {"email": email, "password": password})
    if not check("login", 200, status, body):
        sys.exit("Stopping: login failed. Check the email and password.")

    status, dept = call("POST", "/admin/departments", {"code": "smk", "name": "Smoke Test Dept"})
    if not check("create department", 201, status, dept):
        sys.exit("Stopping: a department 'SMK' may already exist. Remove it and rerun.")
    dept_id = dept["id"]

    status, body = call("POST", "/admin/departments", {"code": "SMK", "name": "Other Name"})
    check("duplicate department is 409", 409, status, body)

    status, cls = call(
        "POST",
        "/admin/classes",
        {"name": "A", "department_id": dept_id, "semester": 5, "academic_year": "2026-2027"},
    )
    if not check("create class", 201, status, cls):
        sys.exit("Stopping before deletes; the department still exists and needs manual removal.")
    class_id = cls["id"]

    status, body = call("DELETE", f"/admin/departments/{dept_id}")
    check("delete department in use is 409", 409, status, body)

    status, body = call("DELETE", f"/admin/classes/{class_id}")
    check("delete class", 204, status, body)

    status, body = call("DELETE", f"/admin/departments/{dept_id}")
    check("delete department", 204, status, body)

    status, body = call("POST", "/auth/logout")
    check("logout", 200, status, body)

    status, body = call("GET", "/admin/departments")
    check("admin route after logout is 401", 401, status, body)

    print("Done. Now check the audit log.")


if __name__ == "__main__":
    main()