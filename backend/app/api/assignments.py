"""
Assignment API routes.
"""

from datetime import datetime
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Assignment, AssignmentStatus, Teacher, DEFAULT_TEACHER_ID
from app.schemas import (
    AssignmentUploadResponse,
    AssignmentListResponse,
    AssignmentListItem,
    AssignmentDetail,
    GradeAssignmentRequest,
    BatchGradeRequest,
    GradedAssignment,
    GradingResult,
    ExportFormat,
    SourceFormatEnum,
    AssignmentStatusEnum,
)
from app.services import (
    get_file_processor,
    get_ocr_service,
    get_ai_grading_service,
    get_export_service,
)

logger = get_logger()

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def ensure_default_teacher(db: Session) -> Teacher:
    """Ensure the default teacher exists."""
    teacher = db.query(Teacher).filter(Teacher.id == DEFAULT_TEACHER_ID).first()
    if not teacher:
        teacher = Teacher(id=DEFAULT_TEACHER_ID, name="Teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    return teacher


@router.post("/upload", response_model=AssignmentUploadResponse)
async def upload_assignment(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload an assignment file for grading.

    Supports PDF, Word (.docx, .doc), and image files.
    """
    # Ensure default teacher exists
    teacher = ensure_default_teacher(db)

    file_processor = get_file_processor()

    # Validate file format
    if not file_processor.is_supported_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: PDF, DOCX, DOC, PNG, JPG, JPEG",
        )

    # Read file content
    content = await file.read()

    # Save file
    stored_filename, file_path, source_format = await file_processor.save_upload(
        file_content=content,
        original_filename=file.filename,
    )

    # Get file size
    file_size = file_processor.get_file_size(stored_filename)

    # Create assignment record
    assignment = Assignment(
        teacher_id=teacher.id,
        title=title,
        original_filename=file.filename,
        stored_filename=stored_filename,
        source_format=source_format,
        file_size=file_size,
        status=AssignmentStatus.UPLOADED,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # Start OCR extraction in background (for now, do it synchronously)
    try:
        ocr_service = get_ocr_service(db)
        extracted_text = await ocr_service.extract_text(file_path, source_format)
        assignment.extracted_text = extracted_text
        assignment.status = AssignmentStatus.UPLOADED
        db.commit()
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        # Continue without OCR - can retry later

    logger.info(f"Uploaded assignment: {assignment.id} ({file.filename})")

    return AssignmentUploadResponse(
        id=assignment.id,
        title=assignment.title,
        filename=assignment.original_filename,
        source_format=SourceFormatEnum(assignment.source_format.value),
        upload_time=assignment.created_at,
        status=AssignmentStatusEnum(assignment.status.value),
    )


@router.post("/grade", response_model=GradedAssignment)
async def grade_assignment(
    request: GradeAssignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Grade an uploaded assignment.

    Uses AI to analyze and grade the assignment based on
    provided background and instructions.
    """
    # Get assignment
    assignment = (
        db.query(Assignment).filter(Assignment.id == request.assignment_id).first()
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Update assignment with grading info
    assignment.background = request.background
    assignment.instructions = request.instructions
    assignment.template_id = request.template_id
    assignment.status = AssignmentStatus.GRADING
    db.commit()

    try:
        # Get AI grading service
        grading_service = get_ai_grading_service(db)

        # Grade the assignment
        result = await grading_service.grade(
            assignment=assignment,
            question_types=request.question_types,
        )

        # Save results
        assignment.grading_results = result.model_dump()
        assignment.status = AssignmentStatus.COMPLETED
        assignment.graded_at = datetime.utcnow()
        db.commit()

        logger.info(f"Graded assignment: {assignment.id}")

        return GradedAssignment(
            id=assignment.id,
            assignment_id=assignment.id,
            status=AssignmentStatusEnum.COMPLETED,
            results=result,
            graded_at=assignment.graded_at,
        )

    except Exception as e:
        logger.error(f"Grading failed: {str(e)}")
        assignment.status = AssignmentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Grading failed: {str(e)}")


@router.post("/batch-grade")
async def batch_grade_assignments(
    request: BatchGradeRequest,
    db: Session = Depends(get_db),
):
    """
    Grade multiple assignments with the same instructions.
    """
    results = []
    errors = []

    for assignment_id in request.assignment_ids:
        try:
            grade_request = GradeAssignmentRequest(
                assignment_id=assignment_id,
                background=request.background,
                instructions=request.instructions,
                template_id=request.template_id,
            )
            result = await grade_assignment(grade_request, db)
            results.append(result)
        except Exception as e:
            errors.append({"assignment_id": assignment_id, "error": str(e)})

    return {
        "completed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.get("", response_model=AssignmentListResponse)
@router.get("/history", response_model=AssignmentListResponse)
async def get_assignment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get assignment history with pagination.
    Supports both "/" and "/history" endpoints for backward compatibility.
    """
    teacher = ensure_default_teacher(db)

    query = db.query(Assignment).filter(Assignment.teacher_id == teacher.id)

    if status:
        try:
            status_enum = AssignmentStatus(status)
            query = query.filter(Assignment.status == status_enum)
        except ValueError:
            pass

    total = query.count()

    assignments = (
        query.order_by(Assignment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        AssignmentListItem(
            id=a.id,
            title=a.title,
            filename=a.original_filename,
            source_format=SourceFormatEnum(a.source_format.value),
            status=AssignmentStatusEnum(a.status.value),
            upload_time=a.created_at,
            graded_at=a.graded_at,
        )
        for a in assignments
    ]

    return AssignmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{assignment_id}", response_model=AssignmentDetail)
async def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about an assignment.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    grading_results = None
    if assignment.grading_results:
        grading_results = GradingResult(**assignment.grading_results)

    return AssignmentDetail(
        id=assignment.id,
        title=assignment.title,
        filename=assignment.original_filename,
        source_format=SourceFormatEnum(assignment.source_format.value),
        status=AssignmentStatusEnum(assignment.status.value),
        upload_time=assignment.created_at,
        graded_at=assignment.graded_at,
        background=assignment.background,
        instructions=assignment.instructions,
        extracted_text=assignment.extracted_text,
        grading_results=grading_results,
    )


@router.get("/{assignment_id}/export")
async def export_assignment(
    assignment_id: str,
    format: ExportFormat = Query(ExportFormat.AUTO),
    db: Session = Depends(get_db),
):
    """
    Export a graded assignment as PDF or DOCX.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status != AssignmentStatus.COMPLETED:
        raise HTTPException(
            status_code=400, detail="Assignment has not been graded yet"
        )

    if not assignment.grading_results:
        raise HTTPException(status_code=400, detail="No grading results available")

    # Get grading result
    grading_result = GradingResult(**assignment.grading_results)

    # Export
    export_service = get_export_service()
    content, filename, content_type = await export_service.export(
        assignment=assignment,
        grading_result=grading_result,
        export_format=format,
    )

    # Update assignment
    db.commit()

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete an assignment.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Delete files
    file_processor = get_file_processor()
    file_processor.delete_file(assignment.stored_filename, "uploads")
    if assignment.graded_filename:
        file_processor.delete_file(assignment.graded_filename, "graded")

    # Delete record
    db.delete(assignment)
    db.commit()

    return {"message": "Assignment deleted"}
