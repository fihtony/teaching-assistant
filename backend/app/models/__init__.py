"""
Models package initialization.
"""

from app.models.teacher import Teacher, DEFAULT_TEACHER_ID
from app.models.assignment import Assignment, AssignmentStatus, SourceFormat
from app.models.template import GradingTemplate
from app.models.settings import Settings
from app.models.cached_article import CachedArticle
from app.models.grading_context import GradingContext, GreetingHistory
from app.models.ai_grading import AIGrading, AIGradingStatus
from app.models.group import Group
from app.models.student import Student, Gender

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
    "AIGrading",
    "AIGradingStatus",
    "Group",
    "Student",
    "Gender",
]
