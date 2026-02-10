"""
GradingTemplate model for storing reusable grading instruction templates.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class GradingTemplate(Base):
    """
    Grading template model.

    Stores reusable grading instructions that teachers can apply
    to multiple assignments. Uses auto-increment integer primary key.
    """

    __tablename__ = "grading_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)

    # Template information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Grading instructions
    instructions = Column(Text, nullable=False)
    # Format of instructions: "markdown", "html", "text", "json"
    instruction_format = Column(String(20), nullable=False, default="text")

    # Encouragement words (JSON string array), e.g. ["Bravo!", "Excellent!", ...]
    encouragement_words = Column(JSON, default=list)

    # Question types (JSON array of {type, name, weight, enabled})
    question_types = Column(JSON, default=list)
    """
    Example: [{"type":"mcq","name":"Multiple Choice","weight":15,"enabled":true}, ...]
    """

    # Usage count for analytics
    usage_count = Column(Integer, default=0)

    # Timestamps with timezone
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    # Relationships
    teacher = relationship("Teacher", back_populates="templates")
    assignments = relationship("Assignment", back_populates="template")

    def __repr__(self) -> str:
        return f"<GradingTemplate(id={self.id}, name={self.name})>"
