"""
AIGrading model for storing each grading run (assignment + context + result).
"""

from enum import Enum

from sqlalchemy import Column, Integer, BigInteger, String, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class AIGradingStatus(str, Enum):
    """AI grading run status."""

    NOT_STARTED = "not_started"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"


class AIGrading(Base):
    """
    One grading run: links assignment, context, and result. Template is on grading_contexts.
    """

    __tablename__ = "ai_grading"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    context_id = Column(Integer, ForeignKey("grading_contexts.id"), nullable=False)

    results = Column(Text, nullable=True)  # JSON string of GradingResult
    graded_filename = Column(Text, nullable=True)
    status = Column(
        SQLEnum(AIGradingStatus, values_callable=lambda x: [m.value for m in x]),
        default=AIGradingStatus.GRADING,
    )
    grading_model = Column(String(128), nullable=True)  # e.g. GLM-4.7
    grading_time = Column(Integer, nullable=True)  # duration in seconds

    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )
    graded_at = Column(String, nullable=True)

    # Relationships
    teacher = relationship("Teacher", back_populates="ai_gradings")
    assignment = relationship("Assignment", back_populates="ai_gradings")
    context = relationship("GradingContext", back_populates="ai_gradings")

    def __repr__(self) -> str:
        return f"<AIGrading(id={self.id}, assignment_id={self.assignment_id}, status={self.status})>"
