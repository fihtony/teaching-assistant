"""
Internal helper for LiteLLM-based provider implementations.
Do not import from outside ai_providers package.
"""

from typing import Any, Dict, List, Optional


async def completion(
    model: str,
    messages: List[Dict[str, Any]],
    *,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 300,
    set_openai_key_for_custom_base: bool = False,
) -> str:
    """
    Run LiteLLM acompletion with the given model and messages.

    Args:
        model: LiteLLM model string (e.g. openai/gpt-4o, openai/GLM-4.7, gemini/gemini-1.5-pro).
        messages: List of {"role": "user"|"system"|"assistant", "content": "..."}.
        api_base: Optional base URL for OpenAI-compatible endpoints.
        api_key: Optional API key; may be set on litellm.openai_key for custom base.
        timeout: Request timeout in seconds.
        set_openai_key_for_custom_base: If True and api_key set, assign litellm.openai_key so
            the client sends Authorization header (needed for ZhipuAI etc.).

    Returns:
        Response content string.
    """
    import litellm

    if api_key:
        if set_openai_key_for_custom_base or model.split("/")[0].lower() == "openai":
            litellm.openai_key = api_key
        elif model.split("/")[0].lower() == "anthropic":
            litellm.anthropic_key = api_key

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content
