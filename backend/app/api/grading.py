"""
API endpoints for essay grading.
"""

import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import encrypt_api_key, get_current_teacher_id
from app.core.datetime_utils import from_iso_datetime, get_now_with_timezone
from app.core.settings_db import ensure_settings_config
from app.models import GradingHistory, GradingTemplate, DEFAULT_TEACHER_ID
from app.schemas.grading import (
    GradeEssayRequest,
    GradingResultResponse,
    GradingHistoryItem,
    GradingHistoryResponse,
    TemplateRequest,
    TemplateResponse,
    AIProviderConfigRequest,
    AIProviderConfigResponse,
    AIProviderInfo,
)
from app.services.essay_grading import EssayGradingService

logger = get_logger()

router = APIRouter(prefix="/grading", tags=["grading"])


# Background task storage (simple in-memory for now)
# In production, use Celery or similar
_grading_tasks = {}


@router.post("/grade-essay", response_model=GradingResultResponse)
async def grade_essay(
    request: GradeEssayRequest,
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """
    Grade a student essay.

    Accepts essay text or file upload (via /upload endpoint first).
    Returns grading result with HTML output.
    """
    try:
        service = EssayGradingService(db)

        # Handle file upload
        file_path = None
        if request.file_id:
            # Get file path from uploaded files
            file_path = _get_uploaded_file_path(request.file_id)
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

        # Grade the essay
        result = await service.grade_essay(
            teacher_id=teacher_id,
            student_name=request.student_name,
            student_level=request.student_level,
            recent_activity=request.recent_activity,
            essay_text=request.essay_text,
            file_path=file_path,
            template_id=request.template_id,
            additional_instructions=request.additional_instructions,
        )

        return GradingResultResponse(
            grading_id=result.id,
            status="completed",
            html_result=result.html_result,
            download_url=f"/api/v1/grading/download/{result.id}",
            student_name=result.student_name,
            student_level=result.student_level,
            created_at=result.created_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error grading essay: {str(e)}")
        raise HTTPException(status_code=500, detail="Grading failed")


@router.post("/upload")
async def upload_essay_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an essay file (txt, docx, pdf).

    Returns a file_id that can be used in /grade-essay.
    """
    # Validate file type
    allowed_extensions = {".txt", ".docx", ".pdf"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_id = f"{file.filename}_{datetime.now().timestamp()}"
    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Store file path for later retrieval
    _grading_tasks[file_id] = {"file_path": file_path}

    return {"file_id": file_id, "filename": file.filename}


@router.get("/history", response_model=GradingHistoryResponse)
async def get_grading_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """Get grading history for the current teacher."""
    service = EssayGradingService(db)
    history = service.get_grading_history(teacher_id, limit, offset)

    items = [
        GradingHistoryItem(
            id=h.id,
            student_name=h.student_name,
            student_level=h.student_level,
            template_id=h.template_id,
            created_at=h.created_at,
        )
        for h in history
    ]

    total = len(items)  # In production, use count query

    return GradingHistoryResponse(total=total, items=items)


@router.get("/{grading_id}", response_model=GradingResultResponse)
async def get_grading_result(
    grading_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific grading result."""
    result = db.query(GradingHistory).filter(GradingHistory.id == grading_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Grading result not found")

    return GradingResultResponse(
        grading_id=result.id,
        status="completed",
        html_result=result.html_result,
        download_url=f"/api/v1/grading/download/{result.id}",
        student_name=result.student_name,
        student_level=result.student_level,
        created_at=result.created_at,
    )


@router.get("/download/{grading_id}")
async def download_grading(
    grading_id: str,
    db: Session = Depends(get_db),
):
    """Download the HTML grading report."""
    result = db.query(GradingHistory).filter(GradingHistory.id == grading_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Grading result not found")

    # Generate HTML file path
    output_dir = "data/graded"
    filename = f"{result.student_name.replace(' ', '_')}_{result.id}.html"
    file_path = os.path.join(output_dir, filename)

    # Create file if it doesn't exist
    if not os.path.exists(file_path):
        os.makedirs(output_dir, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result.html_result)

    return FileResponse(
        file_path,
        filename=filename,
        media_type="text/html",
    )


@router.get("/providers", response_model=list[AIProviderInfo])
async def list_ai_providers():
    """List available AI providers."""
    providers = [
        AIProviderInfo(
            name="zhipuai",
            display_name="ZhipuAI (智谱AI)",
            default_model="glm-4.7",
            description="Chinese AI provider with GLM models"
        ),
        AIProviderInfo(
            name="gemini",
            display_name="Google Gemini",
            default_model="gemini-1.5-pro",
            description="Google's Gemini AI models"
        ),
    ]
    return providers


@router.post("/providers/config", response_model=AIProviderConfigResponse)
async def save_ai_config(
    request: AIProviderConfigRequest,
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """
    Save AI provider configuration (stored in Settings table, type=ai-config).
    API key is encrypted before storage.
    """
    try:
        rec = ensure_settings_config(db)
        config_data = dict(rec.config or {})
        config_data["provider"] = request.provider
        config_data["model"] = request.model or config_data.get("model", "gpt-4o")
        if request.api_key:
            config_data["api_key"] = encrypt_api_key(request.api_key)
        rec.config = config_data
        rec.updated_at = get_now_with_timezone().isoformat()
        db.commit()
        db.refresh(rec)
        now = get_now_with_timezone()
        return AIProviderConfigResponse(
            id="ai-config",
            provider=rec.config.get("provider", "openai"),
            model=rec.config.get("model"),
            is_default=True,
            created_at=from_iso_datetime(rec.created_at) or now,
            updated_at=now,
        )
    except Exception as e:
        logger.error(f"Error saving AI config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.get("/providers/config", response_model=list[AIProviderConfigResponse])
async def get_ai_configs(
    db: Session = Depends(get_db),
    teacher_id: int = DEFAULT_TEACHER_ID,
):
    """Get current AI provider configuration (from Settings table, type=ai-config)."""
    rec = ensure_settings_config(db)
    config_data = rec.config or {}
    now = get_now_with_timezone()
    return [
        AIProviderConfigResponse(
            id="ai-config",
            provider=config_data.get("provider", "openai"),
            model=config_data.get("model", "gpt-4o"),
            is_default=True,
            created_at=from_iso_datetime(rec.created_at) or now,
            updated_at=from_iso_datetime(rec.updated_at) or now,
        )
    ]


def _get_uploaded_file_path(file_id: str) -> Optional[str]:
    """Get file path from uploaded file ID."""
    task_data = _grading_tasks.get(file_id)
    return task_data.get("file_path") if task_data else None
