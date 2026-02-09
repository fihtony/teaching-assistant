"""
Pydantic schemas for Settings API.
"""

from datetime import datetime
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


# AI Configuration schemas
class ProviderInfo(BaseModel):
    """Information about an AI provider."""

    name: str
    is_configured: bool
    available_models: List[str]


class AIConfigResponse(BaseModel):
    """AI configuration response."""

    default_provider: str
    default_model: str
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 8192
    providers: List[ProviderInfo]
    search_engine: str
    is_configured: bool
    copilot_base_url: Optional[str] = "http://localhost:1287"
    copilot_available_models: Optional[List[str]] = None


class AIConfigUpdate(BaseModel):
    """Request to update AI configuration."""

    # Support both field names for backward compatibility
    provider: Optional[str] = None
    default_provider: Optional[str] = None
    model: Optional[str] = None
    default_model: Optional[str] = None
    base_url: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    api_keys: Optional[Dict[str, str]] = Field(
        None,
        description="API keys for providers. Keys: 'openai', 'anthropic', 'google', 'copilot'",
    )
    google_search_api_key: Optional[str] = None
    google_search_cx: Optional[str] = None
    copilot_base_url: Optional[str] = None


class TestConnectionRequest(BaseModel):
    """Request to test connection to a provider."""

    provider: str = Field(..., description="Provider name: 'copilot'")
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class AIProviderUpdate(BaseModel):
    """Request to save only AI provider config (no extra fields)."""

    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class GetModelsRequest(BaseModel):
    """Request to fetch available models from a provider (uses user's base_url and api_key)."""

    provider: str = Field(..., description="Provider: openai, anthropic, google, gemini, zhipuai, copilot")
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """Response from testing connection to a provider."""

    success: bool
    message: str
    models: Optional[List[str]] = None
    error: Optional[str] = None


# Teacher Profile schemas
class TeacherProfileResponse(BaseModel):
    """Teacher profile response."""

    id: int
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TeacherProfileUpdate(BaseModel):
    """Request to update teacher profile."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)


# Greeting schemas
class GreetingSource(BaseModel):
    """Source information for a greeting."""

    title: str
    author: Optional[str] = None


class GreetingResponse(BaseModel):
    """Greeting response."""

    greeting: str
    source: Optional[GreetingSource] = None


# Cache management schemas
class CachedArticleResponse(BaseModel):
    """Cached article response."""

    id: int
    title: str
    author: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    cached_at: str
    expires_at: Optional[str] = None
    access_count: int = 0

    class Config:
        from_attributes = True


class CachedArticleListResponse(BaseModel):
    """List of cached articles response."""

    items: List[CachedArticleResponse]
    total: int
