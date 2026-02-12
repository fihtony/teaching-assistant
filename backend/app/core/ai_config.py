"""
Single source of truth for AI provider and model configuration.

All AI agent requests (grading, essay grading, greeting, etc.) must use
the user-defined provider and model from Settings (type=ai-config) via
these helpers. Do not duplicate config reading or default values elsewhere.
"""

from typing import Optional, Tuple, Any, Dict

from sqlalchemy.orm import Session

from app.core.settings_db import ensure_settings_config
from app.core.security import decrypt_api_key
from app.models import Settings


def get_ai_config_record(db: Session) -> Settings:
    """Return the AI config Settings row (type=ai-config). Creates default if missing."""
    return ensure_settings_config(db)


def get_ai_provider_and_model(db: Session) -> Tuple[str, str]:
    """
    Return (provider, model) from user settings. Uses same defaults as ensure_settings_config.
    """
    rec = get_ai_config_record(db)
    cfg = rec.config or {}
    provider = (cfg.get("provider") or "zhipuai").strip().lower()
    model = (cfg.get("model") or "glm-4-flash").strip()
    return provider, model


def get_resolved_ai_config(db: Session) -> Dict[str, Any]:
    """
    Return full resolved AI config for callers that need provider, model, api_key, base_url, etc.
    api_key is decrypted; omit from dict if not set or decrypt fails.
    """
    rec = get_ai_config_record(db)
    cfg = rec.config or {}
    provider = (cfg.get("provider") or "zhipuai").strip().lower()
    model = (cfg.get("model") or "glm-4-flash").strip()
    base_url = cfg.get("baseUrl") or cfg.get("api_base") or ""
    if not base_url and provider in ("zhipuai", "zhipu"):
        base_url = "https://open.bigmodel.cn/api/paas/v4"
    elif not base_url and provider == "openai":
        base_url = "https://api.openai.com/v1"

    api_key = None
    raw_key = cfg.get("api_key")
    if raw_key:
        try:
            api_key = decrypt_api_key(raw_key) if isinstance(raw_key, str) else raw_key
        except Exception:
            pass

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout": cfg.get("timeout", 300),
        "max_token": cfg.get("max_token", 4096),
        "temperature": cfg.get("temperature", 0.3),
    }


def normalize_grading_model_display(provider: str, model: str) -> Optional[str]:
    """
    Return the display model name to store in ai_grading.grading_model.
    ZhipuAI: normalized to capitalized form (e.g. GLM-4.7). Others: model as-is.
    """
    if not model:
        return None
    provider_lower = (provider or "").strip().lower()
    if provider_lower in ("zhipuai", "zhipu"):
        raw = model.strip()
        if len(raw) > 4 and raw.lower().startswith("glm-"):
            return "GLM-" + raw[4:]
        return raw.upper() if raw else None
    return model.strip() or None
