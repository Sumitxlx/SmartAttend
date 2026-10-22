from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CorrectionCreate(BaseModel):
    attendance_record_id: int
    requested_status: Literal["present", "absent"]
    reason: str = Field(min_length=10, max_length=500)


class CorrectionOut(BaseModel):
    id: int
    attendance_record_id: int
    session_date: date
    subject_code: str
    student_name: str
    roll_number: str
    current_status: str
    requested_status: str
    reason: str
    status: str
    created_at: datetime