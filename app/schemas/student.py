from datetime import date

from pydantic import BaseModel, Field


class SubjectSummary(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    present: int
    total: int
    percentage: float | None  # None when there are no finalized sessions yet
    low: bool


class OverallSummary(BaseModel):
    present: int
    total: int
    percentage: float | None
    low: bool
    threshold: float


class SummaryOut(BaseModel):
    overall: OverallSummary
    subjects: list[SubjectSummary]


class HistoryItem(BaseModel):
    session_date: date
    subject_code: str
    subject_name: str
    status: str


class GoalOut(BaseModel):
    present: int
    total: int
    target: float
    current_percentage: float | None
    # Classes to attend in a row to reach the target. None means the target is unreachable.
    classes_needed: int | None
    # Percentage if all of the next `future_classes` are attended.
    projected_percentage: float | None


class GoalQuery(BaseModel):
    target: float = Field(ge=0, le=100)
    future_classes: int = Field(ge=0, le=1000, default=0)