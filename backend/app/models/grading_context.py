"""
GradingContext model for storing grading background and search results.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class GradingContext(Base):
    """
    Grading context model.

    Stores title (from essay first line), background, instructions,
    search results, and AI understanding (text, line by line).
    One context per grading run; assignment can have multiple runs.
    """

    __tablename__ = "grading_contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("grading_templates.id"), nullable=True)

    # Essay title (e.g. first line of homework)
    title = Column(Text, nullable=True)
    # Teacher-provided background
    background = Column(Text, nullable=True)
    # Teacher's additional instructions at runtime
    instructions = Column(Text, nullable=True)

    # Extracted references (JSON)
    extracted_references = Column(JSON, nullable=True)
    # Search results (JSON)
    search_results = Column(JSON, nullable=True)
    # Cached article IDs used
    cached_article_ids = Column(JSON, nullable=True)
    # AI understanding summary (text, line by line)
    ai_understanding = Column(Text, nullable=True)
    # Output format requirements extracted from teacher's instructions
    output_requirements = Column(Text, nullable=True)

    # Timestamps with timezone
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    # Relationships
    assignment = relationship("Assignment", back_populates="grading_contexts")
    template = relationship("GradingTemplate", back_populates="grading_contexts")
    ai_gradings = relationship("AIGrading", back_populates="context")

    def __repr__(self) -> str:
        return f"<GradingContext(id={self.id}, assignment_id={self.assignment_id})>"


class GreetingHistory(Base):
    """
    Greeting history model.

    Stores generated greetings to avoid repetition.
    """

    __tablename__ = "greeting_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    greeting_text = Column(Text, nullable=False)
    source_article_id = Column(Integer, ForeignKey("cached_articles.id"), nullable=True)
    source_title = Column(String(500), nullable=True)
    source_author = Column(String(255), nullable=True)
    source_quote = Column(Text, nullable=True)
    generated_at = Column(String, default=lambda: get_now_with_timezone().isoformat())

    def __repr__(self) -> str:
        return f"<GreetingHistory(id={self.id}, generated_at={self.generated_at})>"
