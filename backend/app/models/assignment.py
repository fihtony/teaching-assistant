"""
Assignment model for storing uploaded assignments.
"""

from enum import Enum

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    UPLOAD_FAILED = "upload_failed"
    EXTRACT_FAILED = "extract_failed"


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

    Stores information about uploaded assignments (file and OCR state).
    Grading runs are stored in ai_grading with grading_context.
    """

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    student_name = Column(Text, nullable=True)  # Optional; teacher may grade without student profile

    # File information
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    source_format = Column(
        SQLEnum(SourceFormat, values_callable=lambda x: [m.value for m in x]),
        nullable=False,
    )
    file_size = Column(String(50), nullable=True)

    # OCR extracted content
    extracted_text = Column(Text, nullable=True)

    # Status: upload/extract only (no grading state here). Use values for DB so stored "uploaded" etc. map correctly.
    status = Column(
        SQLEnum(AssignmentStatus, values_callable=lambda x: [m.value for m in x]),
        default=AssignmentStatus.UPLOADED,
    )

    # Timestamps with timezone - ISO 8601 format string
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    # Relationships
    teacher = relationship("Teacher", back_populates="assignments")
    student = relationship("Student", back_populates="assignments")
    grading_contexts = relationship("GradingContext", back_populates="assignment")
    ai_gradings = relationship("AIGrading", back_populates="assignment")

    def __repr__(self) -> str:
        return f"<Assignment(id={self.id}, status={self.status})>"
