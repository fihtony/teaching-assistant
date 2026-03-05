"""
OpenRouter LLM provider. Uses OpenRouter REST API for unified access to many models.

API: https://openrouter.ai/api/v1/chat/completions
Docs: https://openrouter.ai/docs/quickstart
"""

from typing import Any, Dict, Optional

import httpx

from app.core.logging import get_logger

logger = get_logger()

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b"


def _normalize_base_url(raw: str) -> str:
    """Ensure base URL is the OpenRouter API root; wrong paths cause 404."""
    u = (raw or "").strip().rstrip("/")
    if not u or "/api/v1" not in u:
        return DEFAULT_BASE_URL
    # If path is longer than /api/v1, trim to avoid double paths (e.g. .../api/v1/chat/completions)
    if u.endswith("/api/v1"):
        return u
    idx = u.find("/api/v1")
    if idx != -1:
        return u[: idx + 7]  # include "/api/v1"
    return DEFAULT_BASE_URL


class OpenRouterLLMProvider:
    """OpenRouter provider using REST API (no LiteLLM). Implements the generic LLM interface."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._provider = (config.get("provider") or "openrouter").strip().lower()
        model = (config.get("model") or DEFAULT_MODEL).strip()
        # OpenRouter: use model id without ":free" to avoid data-policy 404
        self._model = model.replace(":free", "").strip().rstrip(":") or model
        raw = (config.get("base_url") or config.get("baseUrl") or DEFAULT_BASE_URL).strip()
        self._base_url = _normalize_base_url(raw)
        self._api_key = config.get("api_key")
        self._timeout = max(300, int(config.get("timeout") or 300))
        # OpenRouter request body params (per official example)
        self._temperature = float(config.get("temperature", 0.1))
        self._max_tokens = int(config.get("max_tokens") or config.get("max_token") or 8192)

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        *,
        timeout: Optional[int] = None,
    ) -> str:
        if not self._api_key:
            raise ValueError("No API key configured for provider: openrouter")
        url = f"{self._base_url}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        to = timeout if timeout is not None else self._timeout
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Request body matches OpenRouter official example: model, messages, temperature, max_tokens
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        logger.debug("OpenRouter complete: model=%s", self._model)
        async with httpx.AsyncClient(timeout=float(to)) as client:
            r = await client.post(url, headers=headers, json=body)
            if r.status_code != 200:
                try:
                    err_body = r.json()
                    err_msg = err_body.get("error", {}).get("message", r.text)
                except Exception:
                    err_msg = r.text
                if r.status_code == 404 and "data policy" in (err_msg or "").lower():
                    raise ValueError(
                        "OpenRouter 404: No endpoints matching your data policy. "
                        "Configure https://openrouter.ai/settings/privacy"
                    )
                r.raise_for_status()
            data = r.json()
        # Extract content per official example: choices[0].message.content
        if not data.get("choices") or not data["choices"][0].get("message", {}).get("content"):
            logger.warning("OpenRouter unexpected response format: %s", data)
            raise ValueError("OpenRouter returned no choices or missing message.content")
        content = data["choices"][0]["message"]["content"]
        return content if isinstance(content, str) else str(content)
