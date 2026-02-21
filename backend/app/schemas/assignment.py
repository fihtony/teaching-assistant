"""
Pydantic schemas for Assignment API.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union

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

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    UPLOAD_FAILED = "upload_failed"
    EXTRACT_FAILED = "extract_failed"


class SourceFormatEnum(str, Enum):
    """Source file format enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    IMAGE = "image"
    TXT = "txt"
    TEXT = "text"


class ExportFormat(str, Enum):
    """Export format enumeration."""

    AUTO = "auto"
    PDF = "pdf"
    DOCX = "docx"


# Request schemas
class AssignmentUploadResponse(BaseModel):
    """Response after uploading an assignment."""

    id: int
    student_name: Optional[str] = None
    filename: str
    source_format: SourceFormatEnum
    upload_time: str
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


class AIGradingStatusEnum(str, Enum):
    """AI grading run status."""

    NOT_STARTED = "not_started"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"


class GradedAssignment(BaseModel):
    """Response after a grading run (ai_grading record)."""

    id: int  # ai_grading.id
    assignment_id: int
    status: AIGradingStatusEnum
    results: Optional[GradingResult] = None
    graded_at: Optional[str] = None

    class Config:
        from_attributes = True


class GradePhaseResponse(BaseModel):
    """Response for each phase of the grading flow."""

    phase: str  # "upload", "analyze_context", "grading"
    assignment_id: Optional[Union[int, str]] = (
        None  # int for persistent grading, str (UUID) for preview
    )
    context_id: Optional[int] = None
    ai_grading_id: Optional[int] = None
    status: Optional[str] = None
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class AssignmentListItem(BaseModel):
    """Assignment item for list view (assignment + latest grading info if any)."""

    id: int
    title: str  # From grading_context.title or "Assignment"
    student_name: Optional[str] = None
    template_display: str  # Template name, "Custom Instruction", or "name + Custom"
    display_status: str  # "Ready for grading", "Uploaded", "Completed", etc.
    display_date: str  # ISO 8601 datetime string from assignment.updated_at or ai_grading.updated_at
    filename: str
    source_format: SourceFormatEnum
    status: AssignmentStatusEnum
    upload_time: str
    graded_at: Optional[str] = None
    essay_topic: Optional[str] = None
    grading_model: Optional[str] = None
    latest_grading_status: Optional[AIGradingStatusEnum] = None

    class Config:
        from_attributes = True


class AssignmentListResponse(BaseModel):
    """Paginated list of assignments."""

    items: List[AssignmentListItem]
    total: int
    page: int
    page_size: int
    status_options: List[str] = []  # Distinct display_status values for filter dropdown


class AssignmentDetail(BaseModel):
    """Detailed assignment + latest grading run (context + result)."""

    id: int
    student_name: Optional[str] = None
    filename: str
    source_format: SourceFormatEnum
    status: AssignmentStatusEnum
    upload_time: str
    updated_at: Optional[str] = None  # from assignments.updated_at
    extracted_text: Optional[str] = None
    # From latest grading_context + ai_grading
    title: Optional[str] = (
        None  # from grading_contexts.title, falls back to "Assignment"
    )
    template_name: Optional[str] = None  # from grading_templates.name
    ai_grading_status: Optional[str] = None  # from ai_grading.status
    graded_at: Optional[str] = None
    background: Optional[str] = None
    instructions: Optional[str] = None
    grading_time: Optional[int] = (
        None  # duration in seconds from ai_grading.grading_time
    )
    essay_topic: Optional[str] = None  # fallback/legacy
    grading_results: Optional[GradingResult] = None
    graded_content: Optional[str] = None
    grading_model: Optional[str] = None
    ai_grading_id: Optional[int] = None  # ai_grading.id for revise reference

    class Config:
        from_attributes = True


class ReviseGradingRequest(BaseModel):
    """Request to revise a graded output."""

    ai_grading_id: int
    teacher_instruction: str  # The teacher's revision instruction
    current_html_content: str  # The current version of graded HTML being revised


class ReviseGradingResponse(BaseModel):
    """Response after AI revises the grading."""

    html_content: str  # The revised HTML content
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class SaveRevisionRequest(BaseModel):
    """Request to save a revised version as the final graded output."""

    ai_grading_id: int
    html_content: str  # The revised HTML content to save
    revision_history: Optional[List[Dict[str, Any]]] = None  # All revision instructions
