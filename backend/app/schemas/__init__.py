"""
Schemas package initialization.
"""

from app.schemas.assignment import (
    QuestionType,
    AssignmentStatusEnum,
    AIGradingStatusEnum,
    SourceFormatEnum,
    ExportFormat,
    AssignmentUploadResponse,
    GradingItemResult,
    SectionScore,
    GradingResult,
    GradedAssignment,
    GradePhaseResponse,
    AssignmentListItem,
    AssignmentListResponse,
    AssignmentDetail,
    ReviseGradingRequest,
    ReviseGradingResponse,
    SaveRevisionRequest,
)

from app.schemas.template import (
    TemplateBase,
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
)

from app.schemas.settings import (
    ProviderInfo,
    AIConfigResponse,
    AIConfigUpdate,
    AIProviderUpdate,
    GetModelsRequest,
    TestConnectionRequest,
    TestConnectionResponse,
    TeacherProfileResponse,
    TeacherProfileUpdate,
    GreetingSource,
    GreetingResponse,
    CachedArticleResponse,
    CachedArticleListResponse,
)

__all__ = [
    # Assignment
    "QuestionType",
    "AssignmentStatusEnum",
    "AIGradingStatusEnum",
    "SourceFormatEnum",
    "ExportFormat",
    "AssignmentUploadResponse",
    "GradingItemResult",
    "SectionScore",
    "GradingResult",
    "GradedAssignment",
    "GradePhaseResponse",
    "AssignmentListItem",
    "AssignmentListResponse",
    "AssignmentDetail",
    "ReviseGradingRequest",
    "ReviseGradingResponse",
    "SaveRevisionRequest",
    # Template
    "TemplateBase",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListResponse",
    # Settings
    "ProviderInfo",
    "AIConfigResponse",
    "AIConfigUpdate",
    "AIProviderUpdate",
    "GetModelsRequest",
    "TestConnectionRequest",
    "TestConnectionResponse",
    "TeacherProfileResponse",
    "TeacherProfileUpdate",
    "GreetingSource",
    "GreetingResponse",
    "CachedArticleResponse",
    "CachedArticleListResponse",
]
