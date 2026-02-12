"""
Factory for the generic LLM provider. Builds the implementation from config or DB.
"""

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.core.ai_config import get_resolved_ai_config
from app.services.ai_providers.interface import LLMProvider
from app.services.ai_providers.llm_anthropic import AnthropicLLMProvider
from app.services.ai_providers.llm_copilot import CopilotLLMProvider
from app.services.ai_providers.llm_gemini import GeminiLLMProvider
from app.services.ai_providers.llm_openai import OpenAILLMProvider
from app.services.ai_providers.llm_zhipuai import ZhipuAILLMProvider

_LLM_PROVIDER_MAP = {
    "zhipuai": ZhipuAILLMProvider,
    "zhipu": ZhipuAILLMProvider,
    "openai": OpenAILLMProvider,
    "anthropic": AnthropicLLMProvider,
    "google": GeminiLLMProvider,
    "gemini": GeminiLLMProvider,
    "copilot": CopilotLLMProvider,
}


def get_llm_provider_for_config(config: Dict[str, Any]) -> LLMProvider:
    """
    Return an LLM provider instance for the given config dict.
    Config must include: provider, model, base_url (optional), api_key (optional), timeout (optional).
    """
    provider = (config.get("provider") or "zhipuai").strip().lower()
    cls = _LLM_PROVIDER_MAP.get(provider)
    if not cls:
        raise ValueError(
            f"Unknown AI provider: {provider}. "
            f"Available: {', '.join(sorted(_LLM_PROVIDER_MAP.keys()))}"
        )
    return cls(config)


def get_llm_provider(db: Session) -> LLMProvider:
    """
    Return an LLM provider instance using the user-defined AI config from the database.
    All modules that need to call an AI provider should use this.
    """
    config = get_resolved_ai_config(db)
    return get_llm_provider_for_config(config)


def list_llm_provider_names() -> list[str]:
    """Return list of registered LLM provider names (unique, sorted)."""
    return sorted(set(_LLM_PROVIDER_MAP.keys()))
