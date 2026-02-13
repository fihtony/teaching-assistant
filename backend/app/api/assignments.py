"""
Assignment API routes.
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.ai_config import get_ai_provider_and_model, normalize_grading_model_display
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.datetime_utils import get_now_with_timezone, from_iso_datetime
from app.models import (
    Assignment,
    AssignmentStatus,
    Teacher,
    GradingTemplate,
    GradingContext,
    AIGrading,
    AIGradingStatus,
    Student,
    DEFAULT_TEACHER_ID,
)
from app.schemas import (
    AssignmentUploadResponse,
    AssignmentListResponse,
    AssignmentListItem,
    AssignmentDetail,
    GradePhaseResponse,
    GradingResult,
    ExportFormat,
    SourceFormatEnum,
    AssignmentStatusEnum,
    AIGradingStatusEnum,
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


def _first_line(text: Optional[str], max_len: int = 500) -> Optional[str]:
    """Extract first line of text (e.g. essay title)."""
    if not text or not text.strip():
        return None
    line = text.strip().split("\n")[0].strip()
    return (line[:max_len] + "…") if len(line) > max_len else line


def _display_status_and_date(assignment: Assignment, latest_ag: Optional[AIGrading]) -> tuple[str, str]:
    """
    Compute display_status and display_date per business rules.
    Returns (display_status, display_date ISO 8601 datetime string).
    """
    a_status = assignment.status.value if assignment.status else ""
    if a_status not in ("extracted",):
        # Use assignment status; date from assignment.updated_at
        status_label = a_status.replace("_", " ").title() if a_status else "—"
        date_str = assignment.updated_at or "—"
        return (status_label, date_str)
    # assignment.status == extracted
    if not latest_ag or (latest_ag.status and latest_ag.status.value == "not_started"):
        return ("Ready for grading", assignment.updated_at or "—")
    ag_status = latest_ag.status.value if latest_ag.status else ""
    status_label = ag_status.replace("_", " ").title() if ag_status else "—"
    date_str = latest_ag.updated_at or "—"
    return (status_label, date_str)


def _template_display(context: Optional[GradingContext], template: Optional[GradingTemplate]) -> str:
    """Template display: template name, 'Custom Instruction', or 'name + Custom'."""
    has_template = template and template.name
    has_custom = context and (context.instructions or "").strip()
    if has_template and has_custom:
        return f"{template.name} + Custom"
    if has_template:
        return template.name
    if has_custom:
        return "Custom Instruction"
    return "—"


@router.post("/upload", response_model=AssignmentUploadResponse)
async def upload_assignment(
    file: UploadFile = File(...),
    student_id: Optional[int] = Form(None),
    student_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload an assignment file. Optional student_id or student_name.
    """
    teacher = ensure_default_teacher(db)
    file_processor = get_file_processor()

    if not file_processor.is_supported_format(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Supported: TXT, PDF, DOCX, DOC, PNG, JPG, JPEG",
        )

    content = await file.read()
    stored_filename, file_path, source_format = await file_processor.save_upload(
        file_content=content,
        original_filename=file.filename,
    )
    file_size = file_processor.get_file_size(stored_filename)

    assignment = Assignment(
        teacher_id=teacher.id,
        student_id=student_id,
        student_name=student_name,
        original_filename=file.filename,
        stored_filename=stored_filename,
        source_format=source_format,
        file_size=file_size,
        status=AssignmentStatus.UPLOADED,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    try:
        ocr_service = get_ocr_service(db)
        extracted_text = await ocr_service.extract_text(file_path, source_format)
        assignment.extracted_text = extracted_text
        assignment.status = AssignmentStatus.EXTRACTED
        db.commit()
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        assignment.status = AssignmentStatus.EXTRACT_FAILED
        db.commit()

    logger.info(f"Uploaded assignment: {assignment.id} ({file.filename})")
    return AssignmentUploadResponse(
        id=assignment.id,
        student_name=assignment.student_name,
        filename=assignment.original_filename,
        source_format=SourceFormatEnum(assignment.source_format.value),
        upload_time=assignment.created_at or "",
        status=AssignmentStatusEnum(assignment.status.value),
    )


@router.post("/grade/upload", response_model=GradePhaseResponse)
async def grade_upload_phase(
    file: UploadFile = File(...),
    student_id: Optional[int] = Form(None),
    student_name: Optional[str] = Form(None),
    background: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    instructions: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Phase 1: Create assignment + context, upload file, extract text (steps a-d).
    Returns assignment_id, context_id for the next phases.
    """
    start_ms = time.perf_counter()
    teacher = ensure_default_teacher(db)
    file_processor = get_file_processor()
    if not file_processor.is_supported_format(file.filename):
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="upload", error=f"Unsupported format: {file.filename}", elapsed_ms=elapsed)
    try:
        content = await file.read()
        stored_filename, file_path, source_format = await file_processor.save_upload(
            file_content=content, original_filename=file.filename
        )
        file_size = file_processor.get_file_size(stored_filename)
        assignment = Assignment(
            teacher_id=teacher.id,
            student_id=student_id,
            student_name=student_name,
            original_filename=file.filename,
            stored_filename=stored_filename,
            source_format=source_format,
            file_size=file_size,
            status=AssignmentStatus.UPLOADED,
        )
        db.add(assignment)
        db.flush()
        context = GradingContext(
            assignment_id=assignment.id,
            template_id=template_id,
            title=None,
            background=(background or "").strip() or None,
            instructions=(instructions or "").strip() or None,
        )
        db.add(context)
        db.flush()
        ocr_service = get_ocr_service(db)
        extracted_text = await ocr_service.extract_text(file_path, source_format)
        assignment.extracted_text = extracted_text
        assignment.status = AssignmentStatus.EXTRACTED
        context.title = _first_line(extracted_text)
        db.commit()
        db.refresh(assignment)
        db.refresh(context)
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(
            phase="upload",
            assignment_id=assignment.id,
            context_id=context.id,
            status=assignment.status.value,
            elapsed_ms=elapsed,
        )
    except Exception as e:
        logger.exception("Grade upload phase failed")
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="upload", error=str(e), elapsed_ms=elapsed)


@router.post("/{assignment_id}/grade/analyze-context", response_model=GradePhaseResponse)
async def grade_analyze_context_phase(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Phase 2: Fetch student info, create ai_grading (not_started), run context prompt (steps e-g).
    """
    start_ms = time.perf_counter()
    assignment = db.query(Assignment).options(joinedload(Assignment.student)).filter(Assignment.id == assignment_id).first()
    if not assignment:
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="analyze_context", error="Assignment not found", elapsed_ms=elapsed)
    context = db.query(GradingContext).filter(GradingContext.assignment_id == assignment_id).order_by(desc(GradingContext.id)).first()
    if not context:
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="analyze_context", error="Grading context not found", elapsed_ms=elapsed)
    try:
        teacher = ensure_default_teacher(db)
        template_instruction = ""
        if context.template_id:
            t = db.query(GradingTemplate).filter(GradingTemplate.id == context.template_id).first()
            if t and (t.instructions or "").strip():
                template_instruction = t.instructions
        custom_instruction = (context.instructions or "").strip()
        student_info = "Not provided."
        if assignment.student_id and assignment.student:
            s = assignment.student
            parts = [f"Name: {s.name}"]
            if s.grade:
                parts.append(f"Grade: {s.grade}")
            if s.vocabulary:
                parts.append(f"Vocabulary: {s.vocabulary}")
            if s.additional_info:
                parts.append(f"Additional info: {s.additional_info}")
            student_info = "\n".join(parts)
        elif assignment.student_name:
            student_info = f"Name: {assignment.student_name} (temporary, no profile)"
        ai_rec = AIGrading(
            teacher_id=teacher.id,
            assignment_id=assignment.id,
            context_id=context.id,
            status=AIGradingStatus.NOT_STARTED,
        )
        db.add(ai_rec)
        db.commit()
        db.refresh(ai_rec)
        grading_service = get_ai_grading_service(db)
        await grading_service.run_context_prompt_phase(
            assignment=assignment,
            context=context,
            template_instruction=template_instruction,
            custom_instruction=custom_instruction,
            student_info=student_info,
        )
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(
            phase="analyze_context",
            assignment_id=assignment.id,
            context_id=context.id,
            ai_grading_id=ai_rec.id,
            status=ai_rec.status.value,
            elapsed_ms=elapsed,
        )
    except Exception as e:
        logger.exception("Analyze context phase failed")
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="analyze_context", error=str(e), elapsed_ms=elapsed)


@router.post("/{assignment_id}/grade/run", response_model=GradePhaseResponse)
async def grade_run_phase(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    """
    Phase 3: Set ai_grading status=grading, run grading prompt, save results (steps h-i).
    """
    start_ms = time.perf_counter()
    assignment = db.query(Assignment).options(joinedload(Assignment.student)).filter(Assignment.id == assignment_id).first()
    if not assignment:
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="grading", error="Assignment not found", elapsed_ms=elapsed)
    ai_rec = (
        db.query(AIGrading)
        .options(joinedload(AIGrading.context))
        .filter(AIGrading.assignment_id == assignment_id)
        .order_by(desc(AIGrading.created_at))
        .first()
    )
    if not ai_rec or not ai_rec.context:
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="grading", error="AI grading or context not found", elapsed_ms=elapsed)
    try:
        provider, model = get_ai_provider_and_model(db)
        ai_rec.grading_model = normalize_grading_model_display(provider, model)
        ai_rec.status = AIGradingStatus.GRADING
        db.commit()
        student_name = (assignment.student_name or "").strip()
        if not student_name and assignment.student:
            student_name = (assignment.student.name or "").strip()
        # Pass empty string when no name so prompt uses "Dear," not "Dear Student"
        grading_service = get_ai_grading_service(db)
        grade_start = time.perf_counter()
        html = await grading_service.run_grading_prompt_phase(
            assignment=assignment,
            context=ai_rec.context,
            student_name=student_name,
        )
        grading_time_seconds = int(round(time.perf_counter() - grade_start))
        result = GradingResult(items=[], section_scores={}, overall_comment=None, html_content=html)
        ai_rec.results = json.dumps(result.model_dump(), ensure_ascii=False)
        ai_rec.graded_at = get_now_with_timezone().isoformat()
        ai_rec.grading_time = grading_time_seconds
        ai_rec.status = AIGradingStatus.COMPLETED
        db.commit()
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(
            phase="grading",
            assignment_id=assignment.id,
            context_id=ai_rec.context_id,
            ai_grading_id=ai_rec.id,
            status=ai_rec.status.value,
            elapsed_ms=elapsed,
        )
    except Exception as e:
        logger.exception("Grading run phase failed")
        # Calculate total grading time from when ai_rec was created (includes all phases)
        try:
            created = from_iso_datetime(ai_rec.created_at)
            now = get_now_with_timezone()
            total_grading_time = int((now - created).total_seconds())
            ai_rec.grading_time = total_grading_time
        except Exception as te:
            logger.warning(f"Failed to calculate grading time on failure: {str(te)}")
        ai_rec.status = AIGradingStatus.FAILED
        db.commit()
        elapsed = int((time.perf_counter() - start_ms) * 1000)
        return GradePhaseResponse(phase="grading", error=str(e), elapsed_ms=elapsed)


@router.get("", response_model=AssignmentListResponse)
@router.get("/history", response_model=AssignmentListResponse)
async def get_assignment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by display_status"),
    search: Optional[str] = Query(None, description="Search in title and student name"),
    sort_by: Optional[str] = Query("date", description="date | student_name | title"),
    sort_order: Optional[str] = Query("desc", description="asc | desc"),
    db: Session = Depends(get_db),
):
    """
    List all assignments with joined grading_context and ai_grading. Returns title,
    student name, template display, display status, display date. Supports search, sort, status filter.
    """
    try:
        teacher = ensure_default_teacher(db)
        assignments = (
            db.query(Assignment)
            .options(joinedload(Assignment.student))
            .filter(Assignment.teacher_id == teacher.id)
            .all()
        )
        if not assignments:
            return AssignmentListResponse(items=[], total=0, page=page, page_size=page_size, status_options=[])

        aid_list = [a.id for a in assignments]
        latest_ag_list = (
            db.query(AIGrading)
            .options(joinedload(AIGrading.context).joinedload(GradingContext.template))
            .filter(AIGrading.assignment_id.in_(aid_list))
            .order_by(desc(AIGrading.created_at))
            .all()
        )
        latest_by_aid: Dict[int, AIGrading] = {}
        for ag in latest_ag_list:
            if ag.assignment_id not in latest_by_aid:
                latest_by_aid[ag.assignment_id] = ag

        rows = []
        for a in assignments:
            student_name = (a.student_name or "").strip()
            if not student_name and a.student_id and a.student:
                student_name = (a.student.name or "").strip()
            latest = latest_by_aid.get(a.id)
            ctx = latest.context if latest else None
            template = ctx.template if ctx else None
            title = (ctx.title or "").strip() if ctx else ""
            if not title:
                title = "Assignment"
            template_display = _template_display(ctx, template)
            display_status, display_date = _display_status_and_date(a, latest)
            graded_at = latest.graded_at if latest else None
            grading_model = latest.grading_model if latest else None
            latest_grading_status = AIGradingStatusEnum(latest.status.value) if latest and latest.status else None
            essay_topic = (ctx.title or _first_line(a.extracted_text, 120)) if ctx else _first_line(a.extracted_text, 120)

            search_lower = (search or "").strip().lower()
            if search_lower and search_lower not in (title or "").lower() and search_lower not in (student_name or "").lower():
                continue
            if status and status.strip() and display_status.lower() != status.strip().lower():
                continue

            rows.append({
                "assignment": a,
                "student_name": student_name or None,
                "title": title,
                "template_display": template_display,
                "display_status": display_status,
                "display_date": display_date,
                "latest": latest,
                "graded_at": graded_at,
                "grading_model": grading_model,
                "latest_grading_status": latest_grading_status,
                "essay_topic": essay_topic,
            })

        status_options = sorted(set(r["display_status"] for r in rows))
        if sort_by == "student_name":
            rows.sort(key=lambda r: (r["student_name"] or "").lower(), reverse=(sort_order == "desc"))
        elif sort_by == "title":
            rows.sort(key=lambda r: (r["title"] or "").lower(), reverse=(sort_order == "desc"))
        else:
            rows.sort(key=lambda r: r["display_date"] or "", reverse=(sort_order == "desc"))

        total = len(rows)
        start = (page - 1) * page_size
        page_rows = rows[start : start + page_size]

        items = []
        for r in page_rows:
            a = r["assignment"]
            items.append(
                AssignmentListItem(
                    id=a.id,
                    title=r["title"],
                    student_name=r["student_name"],
                    template_display=r["template_display"],
                    display_status=r["display_status"],
                    display_date=r["display_date"],
                    filename=a.original_filename,
                    source_format=SourceFormatEnum(a.source_format.value),
                    status=AssignmentStatusEnum(a.status.value),
                    upload_time=a.created_at or "",
                    graded_at=r["graded_at"],
                    essay_topic=r["essay_topic"],
                    grading_model=r["grading_model"],
                    latest_grading_status=r["latest_grading_status"],
                )
            )

        return AssignmentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            status_options=status_options,
        )
    except Exception as e:
        logger.exception("Error fetching assignment history")
        raise HTTPException(status_code=500, detail=f"Error fetching assignments: {str(e)}")


@router.get("/{assignment_id}", response_model=AssignmentDetail)
async def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Get assignment detail and latest grading run (context + result)."""
    assignment = (
        db.query(Assignment)
        .options(joinedload(Assignment.student))
        .filter(Assignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    student_name = assignment.student_name
    if not student_name and assignment.student_id and assignment.student:
        student_name = assignment.student.name

    latest = (
        db.query(AIGrading)
        .options(
            joinedload(AIGrading.context).joinedload(GradingContext.template)
        )
        .filter(AIGrading.assignment_id == assignment.id)
        .order_by(desc(AIGrading.created_at))
        .first()
    )
    graded_at = None
    background = None
    instructions = None
    title = None
    template_name = None
    ai_grading_status = None
    grading_time = None
    essay_topic = _first_line(assignment.extracted_text)
    grading_results = None
    graded_content = None
    grading_model = None
    if latest:
        graded_at = latest.graded_at
        grading_model = latest.grading_model
        grading_time = latest.grading_time
        ai_grading_status = latest.status.value if latest.status else None
        if latest.context:
            background = latest.context.background
            instructions = latest.context.instructions
            title = latest.context.title or None
            if latest.context.title:
                essay_topic = latest.context.title
            if latest.context.template:
                template_name = latest.context.template.name
        if latest.results:
            try:
                data = json.loads(latest.results) if isinstance(latest.results, str) else latest.results
                grading_results = GradingResult(**data)
                graded_content = grading_results.html_content
            except Exception:
                pass

    return AssignmentDetail(
        id=assignment.id,
        student_name=student_name,
        filename=assignment.original_filename,
        source_format=SourceFormatEnum(assignment.source_format.value),
        status=AssignmentStatusEnum(assignment.status.value),
        upload_time=assignment.created_at or "",
        updated_at=assignment.updated_at or "",
        extracted_text=assignment.extracted_text,
        title=title or "Assignment",
        template_name=template_name,
        ai_grading_status=ai_grading_status,
        graded_at=graded_at,
        background=background,
        instructions=instructions,
        grading_time=grading_time,
        essay_topic=essay_topic,
        grading_results=grading_results,
        graded_content=graded_content,
        grading_model=grading_model,
    )


@router.get("/{assignment_id}/export")
async def export_assignment(
    assignment_id: str,
    format: ExportFormat = Query(ExportFormat.AUTO),
    db: Session = Depends(get_db),
):
    """Export latest grading result for this assignment as PDF or DOCX."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    latest = (
        db.query(AIGrading)
        .filter(AIGrading.assignment_id == assignment.id, AIGrading.status == AIGradingStatus.COMPLETED)
        .order_by(desc(AIGrading.created_at))
        .first()
    )
    if not latest or not latest.results:
        raise HTTPException(status_code=400, detail="No completed grading result to export")

    try:
        data = json.loads(latest.results) if isinstance(latest.results, str) else latest.results
        grading_result = GradingResult(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid grading result: {e}")

    export_service = get_export_service()
    content, filename, content_type = await export_service.export(
        assignment=assignment,
        grading_result=grading_result,
        export_format=format,
    )
    latest.graded_filename = filename
    db.commit()

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/stats/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics: total_graded, pending, this_week, needs_review."""
    now = get_now_with_timezone()
    
    # Total Graded: count ai_grading records with status=completed
    total_graded = db.query(AIGrading).filter(
        AIGrading.status == AIGradingStatus.COMPLETED
    ).count()
    
    # Pending: 
    # a. ai_grading with status=not_started
    # b. assignments not in failure status and not referred in ai_grading
    pending_not_started = db.query(AIGrading).filter(
        AIGrading.status == AIGradingStatus.NOT_STARTED
    ).count()
    
    pending_no_grading = db.query(Assignment).filter(
        ~Assignment.status.in_([AssignmentStatus.UPLOAD_FAILED, AssignmentStatus.EXTRACT_FAILED]),
        ~Assignment.id.in_(
            db.query(AIGrading.assignment_id).distinct()
        )
    ).count()
    
    pending = pending_not_started + pending_no_grading
    
    # This Week: completed ai_grading records within this week (Sunday local time)
    # Calculate the start of this week (Sunday)
    days_since_sunday = (now.weekday() + 1) % 7  # Monday=0, Sunday=6 -> Sunday=0
    week_start = now - timedelta(days=days_since_sunday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    this_week = db.query(AIGrading).filter(
        AIGrading.status == AIGradingStatus.COMPLETED,
        AIGrading.updated_at >= week_start
    ).count()
    
    # Needs Review:
    # a. ai_grading with status=failed
    # b. assignments with failure status
    needs_review_grading = db.query(AIGrading).filter(
        AIGrading.status == AIGradingStatus.FAILED
    ).count()
    
    needs_review_assignment = db.query(Assignment).filter(
        Assignment.status.in_([AssignmentStatus.UPLOAD_FAILED, AssignmentStatus.EXTRACT_FAILED])
    ).count()
    
    needs_review = needs_review_grading + needs_review_assignment
    
    return {
        "total_graded": total_graded,
        "pending": pending,
        "this_week": this_week,
        "needs_review": needs_review,
    }


@router.patch("/{assignment_id}/grading-time")
async def update_grading_time(
    assignment_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Update the total grading time (from all phases) for an assignment.
    
    Expects JSON body with 'total_time_ms' (milliseconds).
    Converts to seconds and saves to the AIGrading record's grading_time field.
    """
    total_time_ms = body.get("total_time_ms")
    if total_time_ms is None:
        raise HTTPException(status_code=400, detail="total_time_ms is required")
    
    # Get the latest AIGrading record for this assignment
    ai_rec = (
        db.query(AIGrading)
        .filter(AIGrading.assignment_id == assignment_id)
        .order_by(desc(AIGrading.created_at))
        .first()
    )
    
    if not ai_rec:
        raise HTTPException(status_code=404, detail="AI grading record not found")
    
    # Convert milliseconds to seconds and save
    grading_time_seconds = int(round(total_time_ms / 1000))
    ai_rec.grading_time = grading_time_seconds
    db.commit()
    
    return {"message": "Grading time updated", "grading_time_seconds": grading_time_seconds}


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Delete an assignment and its ai_grading/grading_context records and files."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    file_processor = get_file_processor()
    file_processor.delete_file(assignment.stored_filename, "uploads")
    for ag in assignment.ai_gradings:
        if ag.graded_filename:
            file_processor.delete_file(ag.graded_filename, "graded")
    for ctx in assignment.grading_contexts:
        db.delete(ctx)
    for ag in list(assignment.ai_gradings):
        db.delete(ag)
    db.delete(assignment)
    db.commit()
    return {"message": "Assignment deleted"}
