"""
PDF annotation service for marking up assignments with teacher feedback.

This service:
1. Takes the original PDF and extracted text
2. Adds visual marks (✓, ✗) and comments to a copy of the PDF
3. Creates an annotated version that preserves the original context
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from datetime import datetime
import json

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch

from app.core.config import get_storage_path
from app.core.logging import get_logger
from app.models import Assignment
from app.schemas.assignment import GradingResult, GradingItemResult

logger = get_logger()


class PDFAnnotationService:
    """Service for annotating PDF documents with grading feedback."""

    def __init__(self):
        self.graded_dir = get_storage_path("graded")

    def create_annotated_pdf(
        self,
        original_pdf_path: str,
        assignment: Assignment,
        grading_result: GradingResult,
        custom_filename: str = None,
    ) -> Tuple[str, str]:
        """
        Create an annotated version of the original PDF.

        This adds teacher feedback directly to the original PDF rather than
        creating a new document, preserving the original context.

        Args:
            original_pdf_path: Path to the original PDF file
            assignment: Assignment object
            grading_result: Grading results with feedback
            custom_filename: Optional custom output filename

        Returns:
            Tuple of (output_path, filename)
        """
        try:
            # Read the original PDF
            reader = PdfReader(original_pdf_path)
            writer = PdfWriter()

            # Get the number of pages
            num_pages = len(reader.pages)

            # Create an overlay PDF with annotations
            overlay_pdf_path = self._create_overlay_pdf(
                num_pages, assignment, grading_result
            )

            # Merge the overlay with the original PDF
            overlay_reader = PdfReader(overlay_pdf_path)

            for page_num in range(num_pages):
                if page_num < len(reader.pages):
                    original_page = reader.pages[page_num]
                    if page_num < len(overlay_reader.pages):
                        overlay_page = overlay_reader.pages[page_num]
                        original_page.merge_page(overlay_page)
                    writer.add_page(original_page)

            # Add a summary page at the end
            summary_page = self._create_summary_page(assignment, grading_result)
            writer.add_page(summary_page)

            # Save the annotated PDF with custom or default filename
            if custom_filename:
                filename = custom_filename
            else:
                base_name = Path(assignment.stored_filename).stem
                filename = f"{base_name}_graded.pdf"

            output_path = self.graded_dir / filename

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            logger.info(f"Created annotated PDF: {filename}")

            # Clean up overlay
            if os.path.exists(overlay_pdf_path):
                os.remove(overlay_pdf_path)

            return str(output_path), filename

        except Exception as e:
            logger.error(f"Error creating annotated PDF: {str(e)}")
            raise

    def _create_overlay_pdf(
        self,
        num_pages: int,
        assignment: Assignment,
        grading_result: GradingResult,
    ) -> str:
        """
        Create an overlay PDF with annotations and inline marks.

        Args:
            num_pages: Number of pages in the original PDF
            assignment: Assignment object
            grading_result: Grading results

        Returns:
            Path to the temporary overlay PDF
        """
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        # Create a PDF with annotations using canvas (allows custom drawing)
        buffer = BytesIO()

        # Create canvas for each page
        c = canvas.Canvas(buffer, pagesize=letter)

        # Set up for red text annotations
        c.setFillColor(colors.red)
        c.setFont("Helvetica", 10)

        # Create consistent positioning strategy
        # We'll add annotations in the margins and at strategic positions
        page_width, page_height = letter

        # Add annotations for each grading item
        # Group items by page (roughly 11 items per page for 3-page worksheet)
        items_per_page = 11

        for page_num in range(num_pages):
            # Calculate which items are on this page
            start_idx = page_num * items_per_page
            end_idx = min((page_num + 1) * items_per_page, len(grading_result.items))

            # Set margin position for annotations
            margin_left = 40
            margin_right = page_width - 40
            margin_top = page_height - 50

            y_position = margin_top

            # Add annotations for items on this page
            for idx in range(start_idx, end_idx):
                if idx < len(grading_result.items):
                    item = grading_result.items[idx]

                    # Create annotation line with mark and comment
                    mark = "✓" if item.is_correct else "✗"

                    # Annotation text
                    annotation_text = f"Q{item.question_number}: {mark}"
                    if not item.is_correct and item.comment:
                        # For incorrect items, add a brief comment (first 40 chars)
                        brief_comment = item.comment[:40]
                        if len(item.comment) > 40:
                            brief_comment += "..."
                        annotation_text += f" - {brief_comment}"

                    # Add to PDF with small offset from standard positions
                    c.drawString(margin_left, y_position, annotation_text)
                    y_position -= 15

                    # Check if we need a new page
                    if y_position < 100:
                        c.showPage()
                        y_position = margin_top

        # Finalize canvas
        c.save()

        # Save to temporary file
        buffer.seek(0)
        temp_path = f"/tmp/overlay_{datetime.now().timestamp()}.pdf"
        with open(temp_path, "wb") as f:
            f.write(buffer.getvalue())

        return temp_path

    def _create_summary_page(
        self, assignment: Assignment, grading_result: GradingResult
    ):
        """
        Create a summary page with overall feedback.

        Args:
            assignment: Assignment object
            grading_result: Grading results

        Returns:
            Page object
        """
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()
        content = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=30,
        )
        content.append(Paragraph("Teacher's Feedback Summary", title_style))

        # Overall comment
        if grading_result.overall_comment:
            comment_style = ParagraphStyle(
                "Comment",
                parent=styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#2d5016"),
                spaceAfter=20,
            )
            content.append(Paragraph(grading_result.overall_comment, comment_style))

        content.append(Spacer(1, 12))

        # Section scores
        content.append(Paragraph("Section Scores:", styles["Heading2"]))
        for section_name, scores in grading_result.section_scores.items():
            score_text = f"<b>{section_name}:</b> {scores.correct}/{scores.total}"
            if scores.encouragement:
                score_text += f" 🌟 {scores.encouragement}"
            content.append(Paragraph(score_text, styles["Normal"]))

        doc.build(content)
        buffer.seek(0)

        # Convert BytesIO to PdfReader and extract the page
        from PyPDF2 import PdfReader

        pdf_reader = PdfReader(buffer)
        return pdf_reader.pages[0]


def get_pdf_annotation_service() -> PDFAnnotationService:
    """Get a PDF annotation service instance."""
    return PDFAnnotationService()
