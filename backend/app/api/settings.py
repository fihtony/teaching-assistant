"""
Settings API routes (AI config, teacher profile).
"""

import os
from typing import Optional
import httpx

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_storage_path
from app.core.logging import get_logger
from app.core.security import encrypt_api_key, decrypt_api_key_safe
from app.core.settings_db import ensure_settings_config, ensure_search_engine_config
from app.models import Teacher, Settings, DEFAULT_TEACHER_ID
from app.schemas import (
    AIConfigResponse,
    AIConfigUpdate,
    AIProviderUpdate,
    GetModelsRequest,
    ProviderInfo,
    TeacherProfileResponse,
    TeacherProfileUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.services.model_fetcher import fetch_models

logger = get_logger()

router = APIRouter(prefix="/settings", tags=["Settings"])


# Provider list for GET /settings (models are fetched via POST /get-models with user's base_url/api_key)
PROVIDER_MODELS = {
    "openai": [],
    "anthropic": [],
    "google": [],
    "zhipuai": [],
    "copilot": [],
}


def ensure_default_teacher(db: Session) -> Teacher:
    """Ensure the default teacher exists."""
    teacher = db.query(Teacher).filter(Teacher.id == DEFAULT_TEACHER_ID).first()
    if not teacher:
        teacher = Teacher(id=DEFAULT_TEACHER_ID, name="Teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    return teacher


# AI Configuration endpoints (ensure_* live in app.core.settings_db)


@router.get("/settings", response_model=AIConfigResponse)
async def get_settings(db: Session = Depends(get_db)):
    """
    Get AI and search engine configuration.
    """
    # Get AI config
    ai_config = ensure_settings_config(db)
    config_data = ai_config.config or {}

    # Get search engine config (separate record)
    search_config = ensure_search_engine_config(db)
    search_data = search_config.config or {"engine": "duckduckgo"}
    search_engine = search_data.get("engine", "duckduckgo")

    provider = config_data.get("provider", "openai")
    model = config_data.get("model", "gpt-4o")
    base_url = config_data.get("baseUrl", "https://api.openai.com/v1")
    temperature = config_data.get("temperature", 0.3)
    max_token = config_data.get("max_token", 8192)
    # Never send real api_key to frontend; frontend uses empty and backend uses DB key when needed
    api_key = ""

    providers = []
    for provider_name, models in PROVIDER_MODELS.items():
        is_configured = provider == provider_name

        providers.append(
            ProviderInfo(
                name=provider_name,
                is_configured=is_configured,
                available_models=models,
            )
        )

    return AIConfigResponse(
        default_provider=provider,
        default_model=model,
        api_base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_token,
        providers=providers,
        search_engine=search_engine,
        is_configured=bool(provider),
        copilot_base_url="http://localhost:1287",
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(request: TestConnectionRequest):
    """
    Test connection to a provider and get available models.
    """
    if request.provider == "copilot":
        base_url = request.base_url or "http://localhost:1287"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get models from Copilot Bridge
                response = await client.get(f"{base_url}/models")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return TestConnectionResponse(
                        success=True,
                        message="Successfully connected to Copilot Bridge",
                        models=models,
                    )
                else:
                    return TestConnectionResponse(
                        success=False,
                        message=f"Copilot Bridge returned status {response.status_code}",
                        error=f"HTTP {response.status_code}",
                    )
        except httpx.ConnectError:
            return TestConnectionResponse(
                success=False,
                message=f"Could not connect to Copilot Bridge at {base_url}",
                error="Connection refused",
            )
        except Exception as e:
            return TestConnectionResponse(
                success=False,
                message=f"Error testing connection: {str(e)}",
                error=str(e),
            )
    else:
        return TestConnectionResponse(
            success=False,
            message=f"Provider '{request.provider}' not supported for testing",
            error="Unsupported provider",
        )


@router.post("/get-models")
async def get_models(request: GetModelsRequest, db: Session = Depends(get_db)):
    """
    Fetch available models from the provider.
    - If request.api_key is non-empty: use it (user typed a new key or unsaved config).
    - Else: load saved AI config from DB, decrypt api_key, use it with base_url from DB or request.
    """
    api_key = (request.api_key or "").strip()
    base_url = (request.base_url or "").strip()

    if not api_key:
        config = ensure_settings_config(db)
        config_data = config.config or {}
        api_key = decrypt_api_key_safe(config_data.get("api_key"))
        if not base_url:
            base_url = config_data.get("baseUrl", "")

    models, error = await fetch_models(
        provider=request.provider,
        base_url=base_url or None,
        api_key=api_key or None,
    )
    return {
        "success": len(models) > 0,
        "models": models,
        "message": f"Found {len(models)} models" if models else (error or "No models found"),
        "error": error,
    }


@router.post("/settings", response_model=AIConfigResponse)
async def update_settings(
    update: AIConfigUpdate,
    db: Session = Depends(get_db),
):
    """
    Update AI configuration (not including search engine).
    Supports both new field names (provider, model, base_url, api_key)
    and legacy field names (default_provider, default_model, api_base_url).
    """
    config = ensure_settings_config(db)

    # Handle both field name conventions
    provider = update.provider or update.default_provider
    model = update.model or update.default_model
    base_url = update.base_url or update.api_base_url
    api_key = update.api_key
    temperature = update.temperature
    max_tokens = update.max_tokens

    # Parse existing config
    config_data = config.config or {
        "provider": "openai",
        "baseUrl": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "max_token": 4096,
        "temperature": 0.3,
    }

    # Update config fields
    if provider is not None:
        config_data["provider"] = provider

    if model is not None:
        config_data["model"] = model

    if base_url is not None:
        config_data["baseUrl"] = base_url

    if temperature is not None:
        config_data["temperature"] = temperature

    if max_tokens is not None:
        config_data["max_token"] = max_tokens

    # Handle API key encryption (store in separate mechanism if needed)
    if api_key:
        config_data["api_key"] = encrypt_api_key(api_key)

    # Update config JSON - delete and recreate to ensure update
    if config:
        db.delete(config)
        db.commit()

    # Create new config with updated values
    new_config = Settings(type="ai-config", config=dict(config_data))
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    logger.info(f"Updated settings configuration: {new_config.config}")

    return await get_settings(db)


@router.post("/ai-provider")
async def update_ai_provider(update: AIProviderUpdate, db: Session = Depends(get_db)):
    """
    Save only AI provider config. Request body: provider, model, base_url, api_key, temperature, max_tokens.
    No GET after save; returns minimal success response.
    """
    config = ensure_settings_config(db)
    config_data = dict(config.config or {})

    if update.provider is not None:
        config_data["provider"] = update.provider
    if update.model is not None:
        config_data["model"] = update.model
    if update.base_url is not None:
        config_data["baseUrl"] = update.base_url
    if update.temperature is not None:
        config_data["temperature"] = update.temperature
    if update.max_tokens is not None:
        config_data["max_token"] = update.max_tokens
    if update.api_key:
        config_data["api_key"] = encrypt_api_key(update.api_key)

    existing = db.query(Settings).filter(Settings.type == "ai-config").first()
    if existing:
        db.delete(existing)
        db.commit()
    new_config = Settings(type="ai-config", config=config_data)
    db.add(new_config)
    db.commit()
    logger.info("Updated AI provider configuration")
    return {"ok": True}


@router.get("/search-engine", response_model=dict)
async def get_search_engine_config(db: Session = Depends(get_db)):
    """
    Get search engine configuration.
    """
    config = ensure_search_engine_config(db)
    config_data = config.config or {"engine": "duckduckgo"}

    return {
        "engine": config_data.get("engine", "duckduckgo"),
    }


@router.post("/search-engine", response_model=dict)
async def update_search_engine_config(
    config: dict,
    db: Session = Depends(get_db),
):
    """
    Update search engine configuration.
    Request body should contain: {"engine": "duckduckgo"} or {"engine": "google"}
    """
    if "engine" not in config:
        raise HTTPException(status_code=400, detail="'engine' field is required")

    engine = config.get("engine", "duckduckgo")

    # Validate engine
    if engine not in ["duckduckgo", "google"]:
        raise HTTPException(
            status_code=400, detail="engine must be 'duckduckgo' or 'google'"
        )

    # Get or create search config
    search_config = db.query(Settings).filter(Settings.type == "search").first()

    if search_config:
        db.delete(search_config)
        db.commit()

    # Create new search config
    new_config = Settings(type="search", config={"engine": engine})
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    logger.info(f"Updated search engine configuration: {new_config.config}")

    return {
        "engine": new_config.config.get("engine", "duckduckgo"),
    }


# Teacher Profile endpoints


@router.get("/teacher-profile", response_model=TeacherProfileResponse)
async def get_teacher_profile(db: Session = Depends(get_db)):
    """
    Get teacher profile.
    """
    teacher = ensure_default_teacher(db)

    return TeacherProfileResponse(
        id=teacher.id,
        name=teacher.name,
        email=teacher.email,
        avatar_url=teacher.avatar_url,
        bio=teacher.bio,
        created_at=teacher.created_at,
    )


@router.post("/teacher-profile", response_model=TeacherProfileResponse)
async def update_teacher_profile(
    profile_data: dict,
    db: Session = Depends(get_db),
):
    """
    Update teacher profile.
    """
    teacher = ensure_default_teacher(db)

    if "name" in profile_data and profile_data["name"] is not None:
        teacher.name = profile_data["name"]

    if "email" in profile_data and profile_data["email"] is not None:
        teacher.email = profile_data["email"]

    if "avatar_url" in profile_data and profile_data["avatar_url"] is not None:
        teacher.avatar_url = profile_data["avatar_url"]

    if "bio" in profile_data and profile_data["bio"] is not None:
        teacher.bio = profile_data["bio"]

    db.commit()
    db.refresh(teacher)

    logger.info(f"Updated teacher profile: {teacher.name}")

    return await get_teacher_profile(db)


@router.get("/avatar")
async def get_avatar(db: Session = Depends(get_db)):
    """
    Get teacher's avatar image.
    """
    teacher = ensure_default_teacher(db)

    if not teacher.avatar_path or not os.path.exists(teacher.avatar_path):
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(teacher.avatar_path)
