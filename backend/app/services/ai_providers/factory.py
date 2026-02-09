"""
AI Provider factory for creating provider instances.
"""

from typing import Optional

from .base import BaseAIProvider
from .zhipuai import ZhipuAIProvider
from .gemini import GeminiProvider

# Map of provider names to provider classes
PROVIDER_MAP = {
    "zhipuai": ZhipuAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(provider_name: str, api_key: str, model: Optional[str] = None) -> BaseAIProvider:
    """
    Get a provider instance by name.

    Args:
        provider_name: Name of the provider (e.g., "zhipuai", "gemini")
        api_key: API key for the provider
        model: Optional model name

    Returns:
        BaseAIProvider instance

    Raises:
        ValueError: If provider name is unknown
    """
    provider_class = PROVIDER_MAP.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available providers: {', '.join(PROVIDER_MAP.keys())}"
        )
    return provider_class(api_key, model)


def list_providers() -> list[str]:
    """List all available provider names."""
    return list(PROVIDER_MAP.keys())
