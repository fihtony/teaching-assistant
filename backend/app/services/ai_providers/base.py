"""
Base AI Provider class for essay grading.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseAIProvider(ABC):
    """Base class for all AI providers."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize AI provider.

        Args:
            api_key: API key for the provider
            model: Model name (optional, uses default if not specified)
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def grade_essay(
        self,
        essay: str,
        requirements: str,
        student_name: Optional[str] = None,
        student_level: Optional[str] = None,
        recent_activity: Optional[str] = None,
    ) -> str:
        """
        Grade an essay and return HTML result.

        Args:
            essay: Student essay text
            requirements: Grading requirements/instructions
            student_name: Optional student name
            student_level: Optional student grade level
            recent_activity: Optional recent activity context

        Returns:
            HTML string with corrections and teacher comments
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """
        Validate if the API key is working.

        Returns:
            True if API key is valid, False otherwise
        """
        pass
