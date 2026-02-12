"""
Copilot Bridge LLM provider. Calls local Copilot Bridge server (e.g. localhost:1287).
"""

import asyncio
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.ai_providers.interface import LLMProvider
from app.services.copilot_bridge_client import CopilotBridgeClient

logger = get_logger()

DEFAULT_BASE_URL = "http://localhost:1287"


class CopilotLLMProvider:
    """Copilot Bridge provider implementing the generic LLM interface."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._model = (config.get("model") or "").strip() or None
        base_url = (config.get("base_url") or config.get("baseUrl") or DEFAULT_BASE_URL).strip()
        if base_url.startswith("http://"):
            parts = base_url.replace("http://", "").split(":")
            host = parts[0] if parts else "localhost"
            port = int(parts[1]) if len(parts) > 1 else 1287
        elif base_url.startswith("https://"):
            parts = base_url.replace("https://", "").split(":")
            host = parts[0] if parts else "localhost"
            port = int(parts[1]) if len(parts) > 1 else 1287
        else:
            host, port = "localhost", 1287
        self._host = host
        self._port = port
        self._timeout = max(60, int(config.get("timeout") or 60))

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        *,
        timeout: Optional[int] = None,
    ) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        to = timeout if timeout is not None else self._timeout
        client = CopilotBridgeClient(host=self._host, port=self._port)
        session_id = client.create_session()
        if not session_id:
            logger.warning("Failed to create Copilot session, continuing without session")
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.query(
                    full_prompt,
                    context=None,
                    timeout=to,
                    model_id=self._model,
                ),
            )
        finally:
            try:
                client.close_session()
            except Exception as e:
                logger.warning("Failed to close Copilot session: %s", e)
        if not response:
            raise ValueError("Copilot Bridge returned empty response")
        return response
