from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import utcnow


class FaceEmbedding(Base):
    """A numeric 'fingerprint' of a student's face. Server-side only: never sent to the browser."""

    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    model_name: Mapped[str] = mapped_column(String(50))  # e.g. "ArcFace"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)