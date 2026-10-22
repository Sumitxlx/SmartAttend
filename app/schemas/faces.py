from pydantic import BaseModel


class PhotoResultOut(BaseModel):
    index: int
    accepted: bool
    reason: str | None


class EnrollmentOut(BaseModel):
    student_id: int
    accepted_count: int
    rejected_count: int
    photos: list[PhotoResultOut]
    enrolled: bool
    message: str