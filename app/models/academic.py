from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # e.g. "CSE"
    name: Mapped[str] = mapped_column(String(150), unique=True)


class ClassGroup(Base):
    """A class/section, e.g. 'CSE Sem 5 A'. Named ClassGroup because 'class' is a Python keyword."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("department_id", "name", "semester", "academic_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # e.g. "A"
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester: Mapped[int]
    academic_year: Mapped[str] = mapped_column(String(9))  # e.g. "2026-2027"


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    employee_id: Mapped[str] = mapped_column(String(50), unique=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    roll_number: Mapped[str] = mapped_column(String(50), unique=True)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    semester: Mapped[int]


class TeachingAssignment(Base):
    """Says: this teacher teaches this subject to this class."""

    __tablename__ = "teaching_assignments"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id", "class_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))