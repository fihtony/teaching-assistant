"""
API routes package initialization.
"""

from fastapi import APIRouter

from app.api.assignments import router as assignments_router
from app.api.templates import router as templates_router
from app.api.settings import router as settings_router
from app.api.greeting import router as greeting_router
from app.api.cache import router as cache_router
from app.api.grading import router as grading_router

# Create main API router with v1 versioning
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(assignments_router)
api_router.include_router(templates_router)
api_router.include_router(settings_router)
api_router.include_router(greeting_router)
api_router.include_router(cache_router)
api_router.include_router(grading_router)

__all__ = ["api_router"]
