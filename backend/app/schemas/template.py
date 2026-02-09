"""
Pydantic schemas for Template API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.assignment import QuestionType


class TemplateBase(BaseModel):
    """Base template schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: str = Field(..., min_length=1)
    question_types: List[QuestionType] = Field(default_factory=list)


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""

    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1)
    question_types: Optional[List[QuestionType]] = None


class TemplateResponse(TemplateBase):
    """Template response schema."""

    id: str
    created_at: datetime
    updated_at: datetime
    usage_count: str = "0"

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """List of templates response."""

    items: List[TemplateResponse]
    total: int
