from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    """Add an audit row to the current transaction. The caller commits."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )