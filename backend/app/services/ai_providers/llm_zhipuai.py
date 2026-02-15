"""
ZhipuAI (智谱) LLM provider. Uses OpenAI-compatible API with GLM models.
"""

from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.ai_providers._litellm import completion
logger = get_logger()

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


def _normalize_model(model: str) -> str:
    """Normalize ZhipuAI model to capitalized form (API is case-sensitive)."""
    if not model:
        return model
    lower = model.strip().lower()
    if lower.startswith("glm-"):
        return "GLM-" + lower[4:]
    return model.strip().upper()


class ZhipuAILLMProvider:
    """ZhipuAI provider implementing the generic LLM interface."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._provider = (config.get("provider") or "zhipuai").strip().lower()
        self._model = (config.get("model") or "glm-4-flash").strip()
        self._base_url = (config.get("base_url") or config.get("baseUrl") or DEFAULT_BASE_URL).strip()
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
            raise ValueError("No API key configured for provider: zhipuai")
        litellm_model = "openai/" + _normalize_model(self._model)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        to = timeout if timeout is not None else self._timeout
        logger.debug("ZhipuAI complete: model=%s", litellm_model)
        return await completion(
            model=litellm_model,
            messages=messages,
            api_base=self._base_url,
            api_key=self._api_key,
            timeout=to,
            set_openai_key_for_custom_base=True,
        )
