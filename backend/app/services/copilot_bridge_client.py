"""
Simple Copilot Bridge client for calling VS Code Copilot via localhost endpoint.

This provides a direct interface to the Copilot Bridge server running at localhost:1287.
"""

import requests
import json
from typing import Optional, Dict, Any
from app.core.logging import get_logger

logger = get_logger()


class CopilotBridgeClient:
    """Client for communicating with Copilot Bridge running on localhost:1287"""

    def __init__(self, host: str = "localhost", port: int = 1287):
        """Initialize the client.

        Args:
            host: Host where Copilot Bridge is running
            port: Port where Copilot Bridge is listening
        """
        self.base_url = f"http://{host}:{port}"
        self.session_id = None

    def health_check(self) -> bool:
        """Check if Copilot Bridge server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            result = response.json()
            logger.info(f"Copilot Bridge health: {result}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Copilot Bridge health check failed: {str(e)}")
            return False

    def create_session(self) -> Optional[str]:
        """Create a new session for maintaining context."""
        try:
            response = requests.post(
                f"{self.base_url}/session/create",
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.session_id = result.get("sessionId")
                    logger.info(f"Created Copilot session: {self.session_id}")
                    return self.session_id

            logger.error(f"Failed to create session: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None

    def query(
        self,
        prompt: str,
        context: Optional[str] = None,
        timeout: int = 60,
        model_id: Optional[str] = None,
    ) -> Optional[str]:
        """Send a prompt to Copilot and get the response.

        Args:
            prompt: The prompt to send to Copilot
            context: Optional context information
            timeout: Request timeout in seconds
            model_id: Optional model ID (e.g., 'gpt-4', 'gpt-5.2-codex')

        Returns:
            The response from Copilot or None if failed
        """
        try:
            payload = {
                "prompt": prompt,
                "timeout": timeout * 1000,  # Convert to milliseconds
            }

            if context:
                payload["context"] = context

            if model_id:
                payload["model_id"] = model_id

            # Use session-specific endpoint if we have a session
            if self.session_id:
                endpoint = f"{self.base_url}/session/{self.session_id}/chat/stream"
            else:
                endpoint = f"{self.base_url}/chat/stream"

            logger.info(f"Calling Copilot at {endpoint}")
            logger.info(f"Prompt length: {len(prompt)} chars")

            full_response = ""

            with requests.post(
                endpoint,
                json=payload,
                timeout=timeout + 10,  # Add buffer to request timeout
                headers={"Content-Type": "application/json"},
                stream=True,
            ) as response:
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Copilot error: {error_msg}")
                    return None

                # Read streaming response
                for line in response.iter_lines():
                    if not line:
                        continue

                    # Handle SSE format (data: {...})
                    if line.startswith(b"data: "):
                        line = line[6:]  # Remove "data: " prefix

                    try:
                        data = json.loads(line)
                        if "content" in data:
                            full_response += data["content"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        # Not JSON, just append as text
                        full_response += (
                            line.decode("utf-8") if isinstance(line, bytes) else line
                        )

            logger.info(f"Copilot response length: {len(full_response)} chars")
            return full_response if full_response else None

        except requests.exceptions.Timeout:
            logger.error("Copilot request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Copilot Bridge")
            return None
        except Exception as e:
            logger.error(f"Copilot query error: {str(e)}")
            return None

    def close_session(self) -> bool:
        """Close the current session."""
        if not self.session_id:
            return True

        try:
            response = requests.delete(
                f"{self.base_url}/session/{self.session_id}",
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Closed Copilot session: {self.session_id}")
                    self.session_id = None
                    return True

            logger.error(f"Failed to close session: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
            return False
