from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=255)]
Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def _normalise_email(value: str) -> str:
    if "@" not in value:
        raise ValueError("Enter a valid email address")
    return value.lower()


class TeacherCreate(BaseModel):
    email: Email
    password: Password
    full_name: PersonName
    employee_id: Identifier
    department_id: int

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _normalise_email(value)


class TeacherOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    department_id: int
    employee_id: str


class StudentCreate(BaseModel):
    email: Email
    password: Password
    full_name: PersonName
    roll_number: Identifier
    class_id: int

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _normalise_email(value)


class StudentOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    class_id: int
    roll_number: str


class AssignmentCreate(BaseModel):
    teacher_id: int
    subject_id: int
    class_id: int


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    subject_id: int
    class_id: int