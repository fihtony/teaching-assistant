"""
Pydantic schemas for Assignment API.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Question type enumeration."""

    MCQ = "mcq"  # Multiple choice questions
    TRUE_FALSE = "true_false"  # True/False questions
    FILL_BLANK = "fill_blank"  # Fill in the blank
    QA = "qa"  # Question and answer
    READING = "reading"  # Reading comprehension
    PICTURE = "picture"  # Picture description
    ESSAY = "essay"  # Essay/composition


class AssignmentStatusEnum(str, Enum):
    """Assignment status enumeration."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceFormatEnum(str, Enum):
    """Source file format enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    IMAGE = "image"
    TXT = "txt"


class ExportFormat(str, Enum):
    """Export format enumeration."""

    AUTO = "auto"
    PDF = "pdf"
    DOCX = "docx"


# Request schemas
class AssignmentUploadResponse(BaseModel):
    """Response after uploading an assignment."""

    id: int
    title: Optional[str] = None
    filename: str
    source_format: SourceFormatEnum
    upload_time: datetime
    status: AssignmentStatusEnum

    class Config:
        from_attributes = True


class GradingItemResult(BaseModel):
    """Result for a single graded item."""

    question_number: int
    question_type: QuestionType
    student_answer: str
    correct_answer: Optional[str] = None
    is_correct: bool
    comment: str
    inline_position: Optional[Dict[str, Any]] = None  # Position for inline annotation


class SectionScore(BaseModel):
    """Score for a section of questions."""

    correct: int
    total: int
    encouragement: Optional[str] = None  # e.g., "Bravo!", "Excellent!"


class GradingResult(BaseModel):
    """Complete grading result for an assignment."""

    items: List[GradingItemResult] = Field(default_factory=list)
    section_scores: Dict[str, SectionScore] = Field(default_factory=dict)
    overall_comment: Optional[str] = None
    html_content: Optional[str] = None  # AI output as HTML when using HTML grading


class GradeAssignmentRequest(BaseModel):
    """Request to grade an assignment."""

    assignment_id: int
    background: Optional[str] = Field(
        None,
        description="Background information about the assignment, e.g., 'This is a book report on Alice in Wonderland'",
    )
    instructions: Optional[str] = Field(
        None, description="Custom grading instructions from the teacher"
    )
    template_id: Optional[int] = Field(
        None, description="ID of a saved grading template to use"
    )
    question_types: Optional[List[QuestionType]] = Field(
        None, description="Types of questions in the assignment"
    )


class GradeAssignmentByPathBody(BaseModel):
    """Optional body for POST /assignments/{id}/grade."""

    background: Optional[str] = None
    instructions: Optional[str] = None
    template_id: Optional[int] = None
    question_types: Optional[List[QuestionType]] = None


class BatchGradeRequest(BaseModel):
    """Request to batch grade multiple assignments."""

    assignment_ids: List[int]
    background: Optional[str] = None
    instructions: Optional[str] = None
    template_id: Optional[int] = None


class GradedAssignment(BaseModel):
    """Response with graded assignment details."""

    id: int
    assignment_id: int
    status: AssignmentStatusEnum
    results: Optional[GradingResult] = None
    graded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssignmentListItem(BaseModel):
    """Assignment item for list view."""

    id: int
    title: Optional[str] = None
    filename: str
    source_format: SourceFormatEnum
    status: AssignmentStatusEnum
    upload_time: datetime
    graded_at: Optional[datetime] = None
    essay_topic: Optional[str] = None  # First line of homework (extracted_text)
    grading_model: Optional[str] = None  # AI model used e.g. GLM-4.7

    class Config:
        from_attributes = True


class AssignmentListResponse(BaseModel):
    """Paginated list of assignments."""

    items: List[AssignmentListItem]
    total: int
    page: int
    page_size: int


class AssignmentDetail(BaseModel):
    """Detailed assignment information."""

    id: int
    title: Optional[str] = None
    filename: str
    source_format: SourceFormatEnum
    status: AssignmentStatusEnum
    upload_time: datetime
    graded_at: Optional[datetime] = None
    background: Optional[str] = None
    instructions: Optional[str] = None
    extracted_text: Optional[str] = None
    grading_results: Optional[GradingResult] = None
    graded_content: Optional[str] = None  # HTML grading output (from grading_results.html_content)

    class Config:
        from_attributes = True
