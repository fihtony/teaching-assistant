"""
Models package initialization.
"""

from app.models.teacher import Teacher, DEFAULT_TEACHER_ID
from app.models.assignment import Assignment, AssignmentStatus, SourceFormat
from app.models.template import GradingTemplate
from app.models.settings import Settings
from app.models.cached_article import CachedArticle
from app.models.grading_context import GradingContext, GreetingHistory
from app.models.grading_history import GradingHistory
from app.models.ai_provider_config import AIProviderConfig

__all__ = [
    "Teacher",
    "DEFAULT_TEACHER_ID",
    "Assignment",
    "AssignmentStatus",
    "SourceFormat",
    "GradingTemplate",
    "Settings",
    "CachedArticle",
    "GradingContext",
    "GreetingHistory",
    "GradingHistory",
    "AIProviderConfig",
]
