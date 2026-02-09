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

    Stores the background information, search results, and article
    references used during grading. Uses auto-increment integer primary key.
    """

    __tablename__ = "grading_contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(
        Integer, ForeignKey("assignments.id"), nullable=False, unique=True
    )

    # Teacher-provided background
    raw_background = Column(Text, nullable=True)

    # Extracted references (JSON)
    extracted_references = Column(JSON, nullable=True)
    """
    Example:
    {
        "books": ["Alice's Adventures in Wonderland"],
        "articles": ["The Importance of Reading"],
        "authors": ["Lewis Carroll"]
    }
    """

    # Search results (JSON)
    search_results = Column(JSON, nullable=True)
    """
    Example:
    [
        {
            "query": "Alice's Adventures in Wonderland",
            "results": [
                {"title": "...", "url": "...", "snippet": "..."}
            ]
        }
    ]
    """

    # Cached article IDs used
    cached_article_ids = Column(JSON, nullable=True)  # List of article IDs

    # AI understanding summary
    ai_understanding = Column(Text, nullable=True)

    # Timestamp with timezone
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())

    # Relationships
    assignment = relationship("Assignment", back_populates="grading_context")

    def __repr__(self) -> str:
        return f"<GradingContext(id={self.id}, assignment_id={self.assignment_id})>"


class GreetingHistory(Base):
    """
    Greeting history model.

    Stores generated greetings to avoid repetition.
    Uses auto-increment integer primary key.
    """

    __tablename__ = "greeting_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Greeting content
    greeting_text = Column(Text, nullable=False)

    # Source information
    source_article_id = Column(Integer, ForeignKey("cached_articles.id"), nullable=True)
    source_title = Column(String(500), nullable=True)
    source_author = Column(String(255), nullable=True)
    source_quote = Column(Text, nullable=True)

    # Timestamp with timezone
    generated_at = Column(String, default=lambda: get_now_with_timezone().isoformat())

    def __repr__(self) -> str:
        return f"<GreetingHistory(id={self.id}, generated_at={self.generated_at})>"
