"""
Pydantic schemas for Template API.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.assignment import QuestionType

InstructionFormat = Union[str, None]
VALID_INSTRUCTION_FORMATS = ("markdown", "html", "text", "json")


class QuestionTypeItem(BaseModel):
    """One question type with weight and enabled flag."""

    type: str = Field(..., description="e.g. mcq, essay")
    name: str = Field(..., description="Display name")
    weight: int = Field(default=10, ge=0, le=100)
    enabled: bool = Field(default=True)


class TemplateBase(BaseModel):
    """Base template schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: str = Field(..., min_length=1)
    instruction_format: str = Field(default="text", description="One of: markdown, html, text, json")
    encouragement_words: List[str] = Field(default_factory=list)
    question_types: List[Union[QuestionTypeItem, Dict[str, Any]]] = Field(default_factory=list)


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""

    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1)
    instruction_format: Optional[str] = Field(None, description="One of: markdown, html, text, json")
    encouragement_words: Optional[List[str]] = None
    question_types: Optional[List[QuestionTypeItem]] = None


class TemplateResponse(TemplateBase):
    """Template response schema. id/usage_count from DB are int; timestamps are ISO strings."""

    id: str  # Serialized from DB int for API
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    usage_count: int = 0


class TemplateListResponse(BaseModel):
    """List of templates response."""

    items: List[TemplateResponse]
    total: int
