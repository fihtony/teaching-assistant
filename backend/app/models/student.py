"""
Student model for storing student information.
"""

from enum import Enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class Gender(str, Enum):
    """Student gender."""

    BOY = "boy"
    GIRL = "girl"


class Student(Base):
    """
    Student model.

    Stores student name, age, gender, vocabulary, grade, optional group, and additional info.
    Uses auto-increment integer primary key.
    Timestamps use ISO 8601 with timezone offset (same as other tables).
    """

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)
    vocabulary = Column(Text, nullable=True)
    grade = Column(Text, nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    additional_info = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    group = relationship("Group", back_populates="students")
    assignments = relationship("Assignment", back_populates="student")

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name={self.name!r})>"
