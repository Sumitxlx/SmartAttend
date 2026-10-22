import enum
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import utcnow


class SessionStatus(str, enum.Enum):
    scheduled = "scheduled"
    active = "active"
    finalized = "finalized"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    uncertain = "uncertain"  # face match was borderline; teacher must review


class MarkMethod(str, enum.Enum):
    face = "face"
    manual = "manual"


class CorrectionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AttendanceSession(Base):
    """One lecture/class meeting."""

    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    teaching_assignment_id: Mapped[int] = mapped_column(ForeignKey("teaching_assignments.id"))
    session_date: Mapped[date] = mapped_column(Date)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, length=20), default=SessionStatus.scheduled
    )


class AttendanceRecord(Base):
    """One student's attendance in one session."""

    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, native_enum=False, length=20)
    )
    method: Mapped[MarkMethod] = mapped_column(Enum(MarkMethod, native_enum=False, length=20))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # face matches only
    marked_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CorrectionRequest(Base):
    """A student asks for one attendance record to be changed."""

    __tablename__ = "correction_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_record_id: Mapped[int] = mapped_column(ForeignKey("attendance_records.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    requested_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, native_enum=False, length=20)
    )
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[CorrectionStatus] = mapped_column(
        Enum(CorrectionStatus, native_enum=False, length=20), default=CorrectionStatus.pending
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    """Who did what, and when. Rows are only ever added, never edited."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))  # e.g. "attendance.corrected"
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)