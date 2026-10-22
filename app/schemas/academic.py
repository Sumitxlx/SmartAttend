from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=20)]
LongName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Semester = Annotated[int, Field(ge=1, le=12)]
AcademicYear = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{4}-[0-9]{4}$")
]


class DepartmentCreate(BaseModel):
    code: Code
    name: LongName

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class ClassCreate(BaseModel):
    name: ShortName
    department_id: int
    semester: Semester
    academic_year: AcademicYear

    @field_validator("academic_year")
    @classmethod
    def years_must_be_consecutive(cls, value: str) -> str:
        start, end = value.split("-")
        if int(end) != int(start) + 1:
            raise ValueError("academic_year must look like 2026-2027")
        return value


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    department_id: int
    semester: int
    academic_year: str


class SubjectCreate(BaseModel):
    code: Code
    name: LongName
    department_id: int
    semester: Semester

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    department_id: int
    semester: int