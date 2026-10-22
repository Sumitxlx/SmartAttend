from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time in UTC. We store all times in UTC."""
    return datetime.now(timezone.utc)