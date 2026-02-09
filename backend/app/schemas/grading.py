"""
Schemas for essay grading API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GradeEssayRequest(BaseModel):
    """Request model for grading an essay."""

    student_name: str = Field(..., description="Student name")
    student_level: str = Field(default="Grade 4", description="Student grade level")
    recent_activity: str = Field(default="", description="Recent activity context")
    essay_text: Optional[str] = Field(None, description="Essay text if pasting")
    file_id: Optional[str] = Field(None, description="File ID if uploading")
    template_id: str = Field(
        default="persuasive_essay_grade4.html",
        description="Template ID to use"
    )
    additional_instructions: Optional[str] = Field(
        None, description="Additional grading instructions"
    )


class GradingResultResponse(BaseModel):
    """Response model for grading result."""

    grading_id: str
    status: str  # processing, completed, failed
    html_result: Optional[str] = None
    download_url: Optional[str] = None
    student_name: str
    student_level: str
    created_at: datetime


class GradingHistoryItem(BaseModel):
    """Item in grading history."""

    id: str
    student_name: str
    student_level: str
    template_id: str
    created_at: datetime


class GradingHistoryResponse(BaseModel):
    """Response model for grading history."""

    total: int
    items: list[GradingHistoryItem]


class TemplateRequest(BaseModel):
    """Request model for creating/updating a template."""

    id: str = Field(..., description="Template ID (e.g., persuasive_essay_grade4.html)")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    content: str = Field(..., description="Template content (Markdown)")
    grade_level: Optional[str] = Field(None, description="Grade level")
    essay_type: Optional[str] = Field(None, description="Essay type")


class TemplateResponse(BaseModel):
    """Response model for template."""

    id: str
    name: str
    description: Optional[str]
    grade_level: Optional[str]
    essay_type: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class AIProviderConfigRequest(BaseModel):
    """Request model for AI provider configuration."""

    provider: str = Field(..., description="Provider name (zhipuai, gemini, etc.)")
    api_key: str = Field(..., description="API key")
    model: Optional[str] = Field(None, description="Model name")
    is_default: bool = Field(default=False, description="Set as default provider")


class AIProviderConfigResponse(BaseModel):
    """Response model for AI provider configuration."""

    id: str
    provider: str
    model: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    # Note: api_key is not returned for security


class AIProviderInfo(BaseModel):
    """Information about an AI provider."""

    name: str
    display_name: str
    default_model: str
    description: str
