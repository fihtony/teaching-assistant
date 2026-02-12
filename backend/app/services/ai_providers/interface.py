"""
Common interface for all AI/LLM providers.

All modules that need to call an AI provider must use this interface only.
Implementations hide provider-specific details (LiteLLM, HTTP, Copilot Bridge, etc.).
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    Generic LLM provider interface. Suitable for any provider and model.

    Implementations are created from resolved config (provider, model, api_key,
    base_url, timeout) and expose a single completion method.
    """

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        *,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Send a prompt to the model and return the generated text.

        Args:
            prompt: User message / main prompt.
            system_prompt: Optional system/instruction message (provider-dependent handling).
            timeout: Optional request timeout in seconds; implementation may use config default.

        Returns:
            Model response as plain text.

        Raises:
            ValueError: If API key or required config is missing.
            Exception: On network or API errors.
        """
        ...
