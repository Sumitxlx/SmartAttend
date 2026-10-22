from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_against_dummy, verify_password
from app.models import User


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if email+password are right and the account is active."""
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_against_dummy(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user