"""
Teacher model for storing teacher profile information.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, LargeBinary
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class Teacher(Base):
    """
    Teacher profile model.

    Stores teacher's name, avatar, and related metadata.
    Uses auto-increment integer primary key.
    """

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, default="Teacher")
    email = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    avatar = Column(LargeBinary, nullable=True)  # Store uploaded image data
    website = Column(String(500), nullable=True)
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    # Relationships
    assignments = relationship("Assignment", back_populates="teacher")
    templates = relationship("GradingTemplate", back_populates="teacher")
    ai_gradings = relationship("AIGrading", back_populates="teacher")

    def __repr__(self) -> str:
        return f"<Teacher(id={self.id}, name={self.name})>"


# Default teacher ID (using integer for new schema)
DEFAULT_TEACHER_ID = 1
