"""
Group model for organizing students.
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class Group(Base):
    """
    Group model.

    Stores group name, description, and goal.
    Uses auto-increment integer primary key.
    Timestamps use ISO 8601 with timezone offset (same as other tables).
    """

    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    students = relationship("Student", back_populates="group")

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name!r})>"
