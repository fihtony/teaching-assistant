"""
Fetch available models from AI providers using user's base_url and api_key.

Follows ai-provider skills: Copilot (GET /models), OpenAI-compatible (GET /models + Bearer),
Gemini (GET /models?key= or Bearer). Returns normalized list of { id, name?, vendor? } or str ids.
"""

import httpx
from typing import List, Optional, Tuple, Union, Any
from app.core.logging import get_logger

logger = get_logger()

# Default base URLs per provider (from ai-provider skills)
PROVIDER_DEFAULT_BASE_URLS = {
    "copilot": "http://localhost:1287",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "zhipuai": "https://open.bigmodel.cn/api/coding/paas/v4",
    "zhipu": "https://open.bigmodel.cn/api/coding/paas/v4",
}


def _normalize_model(m: Any, vendor: str = "") -> Union[str, dict]:
    """Normalize a model entry to either id string or { id, name, vendor }."""
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        mid = m.get("id") or m.get("model") or m.get("model_id") or ""
        name = m.get("name") or mid
        v = m.get("vendor") or vendor
        return {"id": mid, "name": name, "vendor": v} if mid else mid
    return str(m)


async def fetch_models_copilot(base_url: str) -> List[Union[str, dict]]:
    """Copilot Bridge: GET {base_url}/models, no auth."""
    url = f"{base_url.rstrip('/')}/models"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    raw = data.get("models") or data.get("data") or []
    return [_normalize_model(m, "GitHub Copilot") for m in raw if m]


async def fetch_models_openai_compatible(
    base_url: str, api_key: str, vendor: str = "openai"
) -> List[Union[str, dict]]:
    """OpenAI-compatible (OpenAI, ZhipuAI, etc.): GET {base_url}/models, Bearer token."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    # OpenAI returns { data: [ { id: "gpt-4o", ... } ] }
    raw = data.get("data") or data.get("models") or []
    return [_normalize_model(m, vendor) for m in raw if (m.get("id") or m.get("model") or isinstance(m, str))]


async def fetch_models_gemini(base_url: str, api_key: str) -> List[Union[str, dict]]:
    """Google Gemini: GET {base_url}/models?key={api_key} (per skill doc)."""
    base_url = base_url.rstrip("/")
    url = f"{base_url}/models"
    if api_key:
        url = f"{url}?key={api_key}"
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    raw = data.get("data") or data.get("models") or []
    return [_normalize_model(m, "Google") for m in raw if (m.get("id") or m.get("model") or isinstance(m, str))]


async def fetch_models_anthropic(base_url: str, api_key: str) -> List[Union[str, dict]]:
    """Anthropic: GET {base_url}/models. No fallback list; errors are returned as-is."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    raw = data.get("data") or data.get("models") or []
    return [_normalize_model(m, "Anthropic") for m in raw if m]


def _http_error_message(status_code: int, body: str = "") -> str:
    """Return a user-friendly message for HTTP errors."""
    if status_code == 401:
        return "Invalid API key or unauthorized. Check your API key."
    if status_code == 403:
        return "Access forbidden. Check your API key and permissions."
    if status_code == 404:
        return "Base URL or models endpoint not found. Check the base URL."
    if status_code == 422:
        return "Invalid request. Check base URL and provider."
    if 400 <= status_code < 500:
        return f"Request failed ({status_code}). Check base URL and API key."
    if status_code >= 500:
        return f"Provider server error ({status_code}). Try again later."
    return f"Request failed (HTTP {status_code})."


async def fetch_models(
    provider: str, base_url: Optional[str] = None, api_key: Optional[str] = None
) -> Tuple[List[Union[str, dict]], Optional[str]]:
    """
    Fetch model list from the given provider using user's base_url and api_key.

    Returns (list of model ids or objects { id, name, vendor }, error_message or None).
    """
    base_url = (base_url or "").strip() or PROVIDER_DEFAULT_BASE_URLS.get(
        provider, ""
    )
    if not base_url:
        logger.warning("No base_url for provider %s", provider)
        return [], "Base URL is required."

    provider_lower = (provider or "").lower()

    try:
        if provider_lower == "copilot":
            models = await fetch_models_copilot(base_url)
            return models, None
        if provider_lower in ("google", "gemini"):
            models = await fetch_models_gemini(base_url, api_key or "")
            return models, None
        if provider_lower == "anthropic":
            models = await fetch_models_anthropic(base_url, api_key or "")
            return models, None
        if provider_lower in ("openai", "zhipuai", "zhipu", "azure", "ollama", "custom"):
            models = await fetch_models_openai_compatible(
                base_url,
                api_key or "",
                vendor=provider_lower.replace("zhipu", "ZhipuAI").replace("openai", "OpenAI").title(),
            )
            return models, None
        models = await fetch_models_openai_compatible(base_url, api_key or "", vendor=provider)
        return models, None
    except httpx.HTTPStatusError as e:
        msg = _http_error_message(e.response.status_code, e.response.text)
        logger.warning("fetch_models %s HTTP error: %s %s", provider, e.response.status_code, e.response.text)
        return [], msg
    except httpx.ConnectError as e:
        logger.warning("fetch_models %s connect error: %s", provider, e)
        return [], "Cannot connect to base URL. Check the URL and that the service is running."
    except httpx.TimeoutException as e:
        logger.warning("fetch_models %s timeout: %s", provider, e)
        return [], "Request timed out. Check the base URL and network."
    except Exception as e:
        logger.exception("fetch_models %s failed: %s", provider, e)
        return [], f"Failed to fetch models: {str(e)}"
