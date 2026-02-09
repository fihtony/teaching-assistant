"""
Enhanced end-to-end grading test for multiple students.

This demonstrates the complete workflow for each student:
- OCR text extraction
- AI grading based on real extracted content
- Annotated PDF generation with unique filename
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_vocabulary_grading import (
    ORIGINAL_HOMEWORK,
    extract_text_from_pdf,
    create_test_assignment,
    grade_assignment,
    export_to_pdf,
)
from app.core.database import get_session_local, init_db
from datetime import datetime


async def run_test_for_student(student_name: str, student_id: str):
    """Run complete grading test for a single student."""

    print("\n" + "=" * 75)
    print(f"PROCESSING: {student_name} (ID: {student_id})")
    print("=" * 75)

    init_db()
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Step 1: OCR extraction
        print(f"\n[1/5] Extracting homework content via OCR...")
        extracted_text = await extract_text_from_pdf(ORIGINAL_HOMEWORK)
        print(f"      ✓ Extracted {len(extracted_text)} characters")

        # Step 2: Create assignment
        print(f"\n[2/5] Creating assignment record...")
        assignment = await create_test_assignment(
            db, extracted_text, student_name, student_id
        )
        print(f"      ✓ Assignment ID: {assignment.id}")

        # Step 3: AI grading
        print(f"\n[3/5] Grading with AI (extracted content)...")
        grading_result = await grade_assignment(db, assignment)
        correct_count = sum(1 for item in grading_result.items if item.is_correct)
        total_count = len(grading_result.items)
        print(
            f"      ✓ Graded: {correct_count}/{total_count} ({correct_count*100//total_count}%)"
        )

        # Step 4: Generate annotated PDF
        print(f"\n[4/5] Generating annotated PDF...")
        output_path = export_to_pdf(
            str(ORIGINAL_HOMEWORK), assignment, grading_result, student_name
        )
        print(f"      ✓ PDF saved: {Path(output_path).name}")

        # Step 5: Summary
        print(f"\n[5/5] Workflow summary:")
        print(f"      ✓ Student: {student_name}")
        print(f"      ✓ Score: {correct_count}/{total_count}")
        print(f"      ✓ File: {Path(output_path).name}")

        return True

    except Exception as e:
        print(f"      ✗ Error: {str(e)[:100]}")
        return False
    finally:
        db.close()


async def main():
    """Run tests for multiple students."""

    if not ORIGINAL_HOMEWORK.exists():
        print(f"ERROR: Homework file not found: {ORIGINAL_HOMEWORK}")
        return

    print("\n" + "=" * 75)
    print("MULTI-STUDENT END-TO-END GRADING TEST")
    print("=" * 75)
    print(f"Source Homework: {ORIGINAL_HOMEWORK.name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test with multiple students
    students = [
        ("Ethan", "001"),
        ("Emma", "002"),
        ("Liam", "003"),
    ]

    results = []
    for student_name, student_id in students:
        success = await run_test_for_student(student_name, student_id)
        results.append((student_name, success))

    # Final summary
    print("\n" + "=" * 75)
    print("FINAL SUMMARY")
    print("=" * 75)

    success_count = sum(1 for _, success in results if success)
    print(f"\nProcessed: {success_count}/{len(results)} students successfully")
    print("\nStudent Processing Results:")
    for student_name, success in results:
        status = "✓ COMPLETED" if success else "✗ FAILED"
        print(f"  - {student_name:15} {status}")

    print("\n" + "=" * 75)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
