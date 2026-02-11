"""
Assignment model for storing uploaded assignments and grading results.
"""

from enum import Enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceFormat(str, Enum):
    """Source file format enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    IMAGE = "image"
    TXT = "txt"


class Assignment(Base):
    """
    Assignment model.

    Stores information about uploaded assignments, grading status,
    and grading results. Uses auto-increment integer primary key.
    """

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)

    # File information
    title = Column(String(255), nullable=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    source_format = Column(SQLEnum(SourceFormat), nullable=False)
    file_size = Column(String(50), nullable=True)

    # OCR extracted content
    extracted_text = Column(Text, nullable=True)

    # Grading information
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.UPLOADED)
    background = Column(Text, nullable=True)  # Teacher-provided background info
    instructions = Column(Text, nullable=True)  # Custom grading instructions
    template_id = Column(Integer, ForeignKey("grading_templates.id"), nullable=True)

    # Grading results (JSON structure)
    grading_results = Column(JSON, nullable=True)
    grading_model = Column(String(128), nullable=True)  # AI model used e.g. GLM-4.7
    """
    Grading results structure:
    {
        "items": [
            {
                "question_number": 1,
                "question_type": "mcq",
                "student_answer": "A",
                "correct_answer": "B",
                "is_correct": false,
                "comment": "The correct answer is B because..."
            }
        ],
        "section_scores": {
            "mcq": {"correct": 3, "total": 5, "encouragement": null},
            "fill_blank": {"correct": 5, "total": 5, "encouragement": "Excellent!"}
        },
        "overall_comment": "Good work overall..."
    }
    """

    # Export information
    graded_filename = Column(String(255), nullable=True)

    # Timestamps with timezone - ISO 8601 format string
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )
    graded_at = Column(String, nullable=True)

    # Relationships
    teacher = relationship("Teacher", back_populates="assignments")
    template = relationship("GradingTemplate", back_populates="assignments")
    grading_context = relationship(
        "GradingContext", back_populates="assignment", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Assignment(id={self.id}, title={self.title}, status={self.status})>"
