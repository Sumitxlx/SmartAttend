"""Create an admin account. Run from the project root:  python -m scripts.create_admin"""
import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, UserRole


def main() -> None:
    email = input("Admin email: ").strip().lower()
    full_name = input("Full name: ").strip()
    if "@" not in email or not full_name:
        print("Email must contain '@' and the name cannot be empty.")
        return

    password = getpass.getpass("Password (min 10 characters): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.")
        return
    if len(password) < 10:
        print("Password must be at least 10 characters.")
        return

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            print("A user with that email already exists.")
            return
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=UserRole.admin,
            )
        )
        db.commit()
    print(f"Admin '{email}' created.")


if __name__ == "__main__":
    main()