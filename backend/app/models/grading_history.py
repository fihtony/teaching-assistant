"""
Grading History model for storing essay grading results.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

import uuid

from app.core.database import Base


class GradingHistory(Base):
    """
    Store grading history for essays.
    """

    __tablename__ = "grading_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    student_name = Column(String, nullable=False)
    student_level = Column(String)
    recent_activity = Column(Text)
    template_id = Column(String)
    additional_instructions = Column(Text)
    essay_text = Column(Text)
    html_result = Column(Text)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    teacher = relationship("Teacher", back_populates="grading_history")
