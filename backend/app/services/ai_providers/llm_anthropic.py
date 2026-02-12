"""
Anthropic LLM provider (Claude models). Uses LiteLLM with anthropic/ model prefix.
"""

from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.ai_providers._litellm import completion

logger = get_logger()


class AnthropicLLMProvider:
    """Anthropic provider implementing the generic LLM interface."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._model = (config.get("model") or "claude-3-5-sonnet-20241022").strip()
        self._api_key = config.get("api_key")
        self._timeout = max(300, int(config.get("timeout") or 300))

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        *,
        timeout: Optional[int] = None,
    ) -> str:
        if not self._api_key:
            raise ValueError("No API key configured for provider: anthropic")
        litellm_model = f"anthropic/{self._model}"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        to = timeout if timeout is not None else self._timeout
        logger.debug("Anthropic complete: model=%s", litellm_model)
        return await completion(
            model=litellm_model,
            messages=messages,
            api_base=None,
            api_key=self._api_key,
            timeout=to,
            set_openai_key_for_custom_base=False,
        )
