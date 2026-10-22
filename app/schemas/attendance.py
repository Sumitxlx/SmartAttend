from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class SessionStart(BaseModel):
    teaching_assignment_id: int


class MarkIn(BaseModel):
    # Manual marking can only say present or absent. "uncertain" comes from face matching.
    status: Literal["present", "absent"]


class MyAssignmentOut(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    subject_name: str
    class_id: int
    class_name: str
    semester: int
    academic_year: str


class StudentRowOut(BaseModel):
    student_id: int
    roll_number: str
    full_name: str
    status: str | None  # None means not marked yet


class SessionOut(BaseModel):
    id: int
    teaching_assignment_id: int
    session_date: date
    status: str
    started_at: datetime | None
    finalized_at: datetime | None
    students: list[StudentRowOut]


class FinalizeOut(BaseModel):
    session: SessionOut
    auto_marked_absent: int