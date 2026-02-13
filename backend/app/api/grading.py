"""
API endpoints for essay grading.
"""

import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_storage_path
from app.core.logging import get_logger
from app.core.security import encrypt_api_key, get_current_teacher_id
from app.core.datetime_utils import from_iso_datetime, get_now_with_timezone
from app.core.settings_db import ensure_settings_config
from app.models import GradingTemplate, DEFAULT_TEACHER_ID
from app.schemas.grading import (
    GradingHistoryItem,
    GradingHistoryResponse,
    TemplateRequest,
    TemplateResponse,
    AIProviderConfigRequest,
    AIProviderConfigResponse,
    AIProviderInfo,
)
from app.services.ai_providers import list_llm_provider_names

logger = get_logger()

# Display names and default models for GET /providers (from LLM provider registry)
PROVIDER_DISPLAY = {
    "zhipuai": ("ZhipuAI (智谱AI)", "glm-4-flash"),
    "zhipu": ("ZhipuAI (智谱AI)", "glm-4-flash"),
    "openai": ("OpenAI", "gpt-4o"),
    "anthropic": ("Anthropic", "claude-3-5-sonnet-20241022"),
    "google": ("Google Gemini", "gemini-1.5-pro"),
    "gemini": ("Google Gemini", "gemini-1.5-pro"),
    "copilot": ("Copilot Bridge", ""),
}

router = APIRouter(prefix="/grading", tags=["grading"])


@router.get("/history", response_model=GradingHistoryResponse)
async def get_grading_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """Grading history is now from ai_grading; use GET /api/v1/assignments/history for assignment history."""
    return GradingHistoryResponse(total=0, items=[])


@router.get("/providers", response_model=list[AIProviderInfo])
async def list_ai_providers():
    """List available AI providers (from LLM provider registry)."""
    names = list_llm_provider_names()
    return [
        AIProviderInfo(
            name=name,
            display_name=PROVIDER_DISPLAY.get(name, (name.title(), ""))[0],
            default_model=PROVIDER_DISPLAY.get(name, ("", ""))[1],
            description="",
        )
        for name in names
    ]


@router.post("/providers/config", response_model=AIProviderConfigResponse)
async def save_ai_config(
    request: AIProviderConfigRequest,
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """
    Save AI provider configuration (stored in Settings table, type=ai-config).
    API key is encrypted before storage.
    """
    try:
        rec = ensure_settings_config(db)
        config_data = dict(rec.config or {})
        config_data["provider"] = request.provider
        config_data["model"] = request.model or config_data.get("model", "gpt-4o")
        if request.api_key:
            config_data["api_key"] = encrypt_api_key(request.api_key)
        rec.config = config_data
        rec.updated_at = get_now_with_timezone().isoformat()
        db.commit()
        db.refresh(rec)
        now = get_now_with_timezone()
        return AIProviderConfigResponse(
            id="ai-config",
            provider=rec.config.get("provider", "openai"),
            model=rec.config.get("model"),
            is_default=True,
            created_at=from_iso_datetime(rec.created_at) or now,
            updated_at=now,
        )
    except Exception as e:
        logger.error(f"Error saving AI config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.get("/providers/config", response_model=list[AIProviderConfigResponse])
async def get_ai_configs(
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """Get current AI provider configuration (from Settings table, type=ai-config)."""
    rec = ensure_settings_config(db)
    config_data = rec.config or {}
    now = get_now_with_timezone()
    return [
        AIProviderConfigResponse(
            id="ai-config",
            provider=config_data.get("provider", "openai"),
            model=config_data.get("model", "gpt-4o"),
            is_default=True,
            created_at=from_iso_datetime(rec.created_at) or now,
            updated_at=from_iso_datetime(rec.updated_at) or now,
        )
    ]


