"""
Schemas package initialization.
"""

from app.schemas.assignment import (
    QuestionType,
    AssignmentStatusEnum,
    SourceFormatEnum,
    ExportFormat,
    AssignmentUploadResponse,
    GradingItemResult,
    SectionScore,
    GradingResult,
    GradeAssignmentRequest,
    GradeAssignmentByPathBody,
    BatchGradeRequest,
    GradedAssignment,
    AssignmentListItem,
    AssignmentListResponse,
    AssignmentDetail,
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
    "SourceFormatEnum",
    "ExportFormat",
    "AssignmentUploadResponse",
    "GradingItemResult",
    "SectionScore",
    "GradingResult",
    "GradeAssignmentRequest",
    "GradeAssignmentByPathBody",
    "BatchGradeRequest",
    "GradedAssignment",
    "AssignmentListItem",
    "AssignmentListResponse",
    "AssignmentDetail",
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
