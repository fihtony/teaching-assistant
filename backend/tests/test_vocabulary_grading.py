"""
End-to-end homework grading test script.

This script demonstrates the complete grading workflow:
1. Loads student homework PDF
2. Extracts text content via OCR
3. Sends extracted content to AI for intelligent grading
4. Receives detailed feedback with marks and comments
5. Creates annotated PDF with marks (✓/✗) and comments
6. Generates unique output file with student info and timestamp

Each test run uses real AI grading based on actual extracted content.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import random
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session_local, init_db
from app.models import Assignment, Teacher, AssignmentStatus, SourceFormat, Settings, GradingContext
from app.services.ocr_service import OCRService
from app.services.ai_grading import AIGradingService
from app.services.pdf_annotation_service import PDFAnnotationService
from app.schemas.assignment import (
    QuestionType,
    GradingResult,
    GradingItemResult,
    SectionScore,
)


# Path to homework files
HOMEWORK_DIR = Path(__file__).parent.parent.parent / "docs" / "homework"
ORIGINAL_HOMEWORK = HOMEWORK_DIR / "1_vocabulary.pdf"
GRADED_HOMEWORK = HOMEWORK_DIR / "1_vocabulary_graded.pdf"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "graded"


async def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    ocr = OCRService()
    text = await ocr.extract_text(str(pdf_path), "pdf")
    return text or ""


async def create_test_assignment(
    db_session,
    extracted_text: str,
    student_name: str = "Ethan",
    student_id: str = "001",
) -> Assignment:
    """Create a test assignment in the database."""
    # Ensure teacher exists
    teacher = db_session.query(Teacher).filter(Teacher.id == 1).first()
    if not teacher:
        teacher = Teacher(id=1, name="Test Teacher")
        db_session.add(teacher)
        db_session.commit()

    assignment = Assignment(
        teacher_id=teacher.id,
        student_name=student_name,
        original_filename="1_vocabulary.pdf",
        stored_filename=f"homework_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        source_format=SourceFormat.PDF,
        status=AssignmentStatus.EXTRACTED,
        extracted_text=extracted_text,
    )
    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)
    return assignment


def has_valid_ai_config(db_session) -> bool:
    """Check if there's a valid AI config."""
    settings = db_session.query(Settings).filter(Settings.type == "ai-config").first()
    if not settings or not settings.config:
        return False
    provider = settings.config.get("provider")
    # copilot doesn't need external API key, it uses local endpoint
    # For other providers, check if API key exists
    if provider in ["openai", "anthropic", "google"]:
        api_key = settings.config.get("api_key")
        return bool(api_key)
    return bool(provider)  # copilot or other providers that use local endpoints


async def grade_assignment(db_session, assignment: Assignment) -> GradingResult:
    """Grade the assignment using real AI service; create context with background/instructions."""

    print("Calling AI grading service with extracted content...")
    grading_service = AIGradingService(db_session)

    background = """
This is a vocabulary worksheet focusing on synonyms.
The worksheet has multiple sections:
1. Section A: Cross out the word that doesn't belong in each word group
2. Section B: Write vocabulary words to complete sentences (using words like: vast, unfurl, garment, trophy, chide, thaw, din, nimble, fret, eerie)
3. Section B (Reading): Multiple choice questions about vocabulary words
4. Writing section: Design a new item of clothing using vocabulary words
5. Maze section: Match synonyms to navigate through a maze

Key vocabulary words: unfurl, vex, din, chide, nimble, thaw, garment, trophy, vast, eerie, fret

The student is named """ + (assignment.student_name or "Student") + """.
Based on the extracted text provided, please analyze and grade the homework.
"""
    instructions = """
Please grade this vocabulary homework following these guidelines:
1. Check if the student correctly identified words that don't belong
2. Verify sentence completion uses appropriate vocabulary words
3. Grade multiple choice questions
4. Evaluate the creative writing section for vocabulary usage
5. Check the synonym maze answers

For each question/section, provide:
- Mark as correct (✓) or incorrect (✗)
- Brief feedback or correction (1 sentence max for incorrect answers)
- Encouragement for correct answers

Be encouraging and provide positive feedback. Use phrases like "Great job!" or "Excellent!" for correct answers.
For any mistakes, provide gentle corrections suggesting the right answer.
"""
    context = GradingContext(
        assignment_id=assignment.id,
        title=(assignment.extracted_text or "").strip().split("\n")[0][:200] if assignment.extracted_text else None,
        background=background,
        instructions=instructions,
    )
    db_session.add(context)
    db_session.commit()
    db_session.refresh(context)

    question_types = [
        QuestionType.MCQ,
        QuestionType.FILL_BLANK,
        QuestionType.MCQ,
        QuestionType.ESSAY,
        QuestionType.FILL_BLANK,
    ]

    # Call real AI grading with context
    result = await grading_service.grade_with_context(assignment, context, question_types)
    print("✓ AI grading completed successfully")
    return result


def export_to_pdf(
    original_pdf_path: str,
    assignment: Assignment,
    grading_result: GradingResult,
    student_name: str = "Student",
) -> Path:
    """Export graded assignment by annotating the original PDF with unique filename."""
    annotation_service = PDFAnnotationService()

    # Generate unique filename with student name and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{student_name}_{timestamp}_graded.pdf"

    output_path, filename = annotation_service.create_annotated_pdf(
        original_pdf_path, assignment, grading_result, custom_filename=unique_filename
    )

    print(f"✓ Exported annotated PDF: {filename}")
    print(f"  Location: {output_path}")

    return Path(output_path)


async def compare_with_teacher_graded(our_graded_path: Path, teacher_graded_path: Path):
    """Compare our graded version with teacher's version."""
    print("\n" + "=" * 60)
    print("COMPARISON WITH TEACHER'S GRADED VERSION")
    print("=" * 60)

    # Extract text from both PDFs
    ocr = OCRService()

    our_text = await ocr.extract_text(str(our_graded_path), "pdf")
    teacher_text = await ocr.extract_text(str(teacher_graded_path), "pdf")

    print(f"\nTeacher's graded PDF content:")
    print("-" * 40)
    print(teacher_text[:2000] if teacher_text else "Could not extract text")

    print(f"\n\nOur graded PDF content (extracted):")
    print("-" * 40)
    print(our_text[:2000] if our_text else "Could not extract text")

    # Check for key phrases from teacher's grading
    teacher_key_phrases = ["Excellent", "Great job", "Ethan"]
    our_key_matches = []
    for phrase in teacher_key_phrases:
        if our_text and phrase.lower() in our_text.lower():
            our_key_matches.append(phrase)

    print(f"\n\nKey phrase matching:")
    print(f"Teacher's graded PDF phrases found in our version: {our_key_matches}")
    print(
        f"Match rate: {len(our_key_matches)}/{len(teacher_key_phrases)} ({100*len(our_key_matches)//len(teacher_key_phrases)}%)"
    )

    return our_text, teacher_text


async def main():
    """Main test function."""
    print("=" * 60)
    print("VOCABULARY HOMEWORK GRADING TEST")
    print("=" * 60)

    # Check files exist
    if not ORIGINAL_HOMEWORK.exists():
        print(f"ERROR: Original homework not found: {ORIGINAL_HOMEWORK}")
        return

    if not GRADED_HOMEWORK.exists():
        print(f"WARNING: Teacher's graded homework not found: {GRADED_HOMEWORK}")

    # Initialize database
    init_db()
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Define student info for this test run
        student_name = (
            "Ethan"  # This would come from the PDF metadata or user input in production
        )
        student_id = "001"

        print("\n" + "=" * 70)
        print(f"END-TO-END HOMEWORK GRADING TEST")
        print(f"Student: {student_name} (ID: {student_id})")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Step 1: Extract text from original homework
        print("\n[Step 1] EXTRACTING TEXT FROM PDF...")
        print(f"  Source: {ORIGINAL_HOMEWORK}")
        extracted_text = await extract_text_from_pdf(ORIGINAL_HOMEWORK)
        print(
            f"  ✓ Extracted {len(extracted_text)} characters from {len(extracted_text.split())} words"
        )
        print("\n  Text preview (first 500 chars):")
        print("  " + "-" * 50)
        for line in extracted_text[:500].split("\n"):
            if line.strip():
                print(f"  {line[:65]}")
        print("  " + "-" * 50)

        # Step 2: Create test assignment
        print("\n[Step 2] CREATING ASSIGNMENT RECORD...")
        assignment = await create_test_assignment(
            db, extracted_text, student_name, student_id
        )
        print(f"  ✓ Assignment created (ID: {assignment.id})")
        print(f"  Student: {assignment.student_name}")
        print(f"  Storage: {assignment.stored_filename}")

        # Step 3: Grade the assignment using AI
        print("\n[Step 3] GRADING WITH AI SERVICE...")
        print(f"  Processing extracted content from PDF...")
        grading_result = await grade_assignment(db, assignment)

        print("\n[Step 4] GRADING RESULTS SUMMARY:")
        print("-" * 40)
        print(f"Total items graded: {len(grading_result.items)}")
        for section_name, scores in grading_result.section_scores.items():
            print(f"  {section_name}: {scores.correct}/{scores.total}")
            if scores.encouragement:
                print(f"    🌟 {scores.encouragement}")
        print(f"\nOverall comment: {grading_result.overall_comment}")

        # Step 4: Export to PDF with unique filename
        print("\n[Step 5] GENERATING ANNOTATED PDF...")
        print(f"  Creating unique output file with student info and timestamp...")
        output_path = export_to_pdf(
            str(ORIGINAL_HOMEWORK), assignment, grading_result, student_name
        )

        # Step 5: Compare with teacher's version
        if GRADED_HOMEWORK.exists():
            print("\n[Step 6] COMPARING WITH TEACHER'S GRADED VERSION...")
            await compare_with_teacher_graded(output_path, GRADED_HOMEWORK)
        else:
            print("\n[Step 6] Teacher's graded version not available for comparison")

        # Assignment status stays EXTRACTED; grading is stored in ai_grading
        db.commit()

        print("\n" + "=" * 70)
        print("✓ END-TO-END GRADING WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\n📁 Output File: {output_path}")
        print(f"📊 Grade Summary:")
        print(f"   - Total items: {len(grading_result.items)}")
        correct_count = sum(1 for item in grading_result.items if item.is_correct)
        incorrect_count = len(grading_result.items) - correct_count
        print(
            f"   - Correct: {correct_count} ({correct_count*100//len(grading_result.items)}%)"
        )
        print(
            f"   - Incorrect: {incorrect_count} ({incorrect_count*100//len(grading_result.items)}%)"
        )
        print(f"🎓 Student: {student_name}")
        print(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
