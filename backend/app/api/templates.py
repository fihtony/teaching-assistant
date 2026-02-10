"""
Template API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import GradingTemplate, Teacher, DEFAULT_TEACHER_ID
from app.schemas import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
)

logger = get_logger()

router = APIRouter(prefix="/templates", tags=["Templates"])


def ensure_default_teacher(db: Session) -> Teacher:
    """Ensure the default teacher exists."""
    teacher = db.query(Teacher).filter(Teacher.id == DEFAULT_TEACHER_ID).first()
    if not teacher:
        teacher = Teacher(id=DEFAULT_TEACHER_ID, name="Teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    return teacher


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    db: Session = Depends(get_db),
):
    """
    Get all grading templates.
    """
    teacher = ensure_default_teacher(db)

    templates = (
        db.query(GradingTemplate)
        .filter(GradingTemplate.teacher_id == teacher.id)
        .order_by(GradingTemplate.updated_at.desc())
        .all()
    )

    items = [
        TemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description or "",
            instructions=t.instructions or "",
            instruction_format=getattr(t, "instruction_format", None) or "text",
            encouragement_words=getattr(t, "encouragement_words", None) or [],
            question_types=t.question_types or [],
            created_at=t.created_at,
            updated_at=t.updated_at,
            usage_count=t.usage_count or 0,
        )
        for t in templates
    ]

    return TemplateListResponse(items=items, total=len(items))


@router.post("", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new grading template.
    """
    teacher = ensure_default_teacher(db)

    qt_list = template.question_types or []
    qt_stored = [
        qt.model_dump() if hasattr(qt, "model_dump") else qt
        for qt in qt_list
    ]
    new_template = GradingTemplate(
        teacher_id=teacher.id,
        name=template.name,
        description=template.description,
        instructions=template.instructions,
        instruction_format=getattr(template, "instruction_format", None) or "text",
        encouragement_words=getattr(template, "encouragement_words", None) or [],
        question_types=qt_stored,
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    logger.info(f"Created template: {new_template.id} ({new_template.name})")

    return TemplateResponse(
        id=str(new_template.id),
        name=new_template.name,
        description=new_template.description or "",
        instructions=new_template.instructions or "",
        instruction_format=new_template.instruction_format or "text",
        encouragement_words=new_template.encouragement_words or [],
        question_types=new_template.question_types or [],
        created_at=new_template.created_at,
        updated_at=new_template.updated_at,
        usage_count=new_template.usage_count or 0,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific template.
    """
    template = (
        db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description or "",
        instructions=template.instructions or "",
        instruction_format=getattr(template, "instruction_format", None) or "text",
        encouragement_words=getattr(template, "encouragement_words", None) or [],
        question_types=template.question_types or [],
        created_at=template.created_at,
        updated_at=template.updated_at,
        usage_count=template.usage_count or 0,
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    update: TemplateUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a template.
    """
    template = (
        db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if update.name is not None:
        template.name = update.name
    if update.description is not None:
        template.description = update.description
    if update.instructions is not None:
        template.instructions = update.instructions
    if getattr(update, "instruction_format", None) is not None:
        template.instruction_format = update.instruction_format
    if getattr(update, "encouragement_words", None) is not None:
        template.encouragement_words = update.encouragement_words
    if update.question_types is not None:
        template.question_types = [
            qt.model_dump() if hasattr(qt, "model_dump") else qt
            for qt in update.question_types
        ]

    db.commit()
    db.refresh(template)

    logger.info(f"Updated template: {template.id}")

    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description or "",
        instructions=template.instructions or "",
        instruction_format=getattr(template, "instruction_format", None) or "text",
        encouragement_words=getattr(template, "encouragement_words", None) or [],
        question_types=template.question_types or [],
        created_at=template.created_at,
        updated_at=template.updated_at,
        usage_count=template.usage_count or 0,
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a template.
    """
    template = (
        db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()

    logger.info(f"Deleted template: {template_id}")

    return {"message": "Template deleted"}
