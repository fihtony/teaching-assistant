"""
OCR service for extracting text from images and PDFs.
"""

import io
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile

from PIL import Image

from app.core.config import get_config
from app.core.logging import get_logger
from app.models.assignment import SourceFormat

logger = get_logger()

# Lazy load EasyOCR to avoid slow startup
_reader = None


def get_ocr_reader():
    """Get or create the EasyOCR reader instance."""
    global _reader
    if _reader is None:
        import easyocr

        config = get_config()
        _reader = easyocr.Reader(
            config.ocr.languages,
            gpu=config.ocr.gpu,
        )
        logger.info(f"Initialized EasyOCR with languages: {config.ocr.languages}")
    return _reader


class OCRService:
    """
    Service for extracting text from images and PDFs using EasyOCR.
    """

    def __init__(self):
        self.config = get_config()

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file.

        Args:
            image_path: Path to the image file.

        Returns:
            Extracted text.
        """
        try:
            reader = get_ocr_reader()
            results = reader.readtext(image_path)

            # Extract text from results
            text_lines = [result[1] for result in results]
            extracted_text = "\n".join(text_lines)

            logger.info(f"Extracted {len(text_lines)} lines from image: {image_path}")
            return extracted_text

        except Exception as e:
            logger.error(f"OCR error for image {image_path}: {str(e)}")
            raise

    def extract_text_from_image_bytes(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes.

        Args:
            image_bytes: Raw image bytes.

        Returns:
            Extracted text.
        """
        try:
            # Save to temporary file for EasyOCR
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            text = self.extract_text_from_image(tmp_path)

            # Clean up
            Path(tmp_path).unlink()

            return text

        except Exception as e:
            logger.error(f"OCR error for image bytes: {str(e)}")
            raise

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file.

        First tries to extract embedded text, then falls back to OCR.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text.
        """
        try:
            # Try to extract embedded text first
            import PyPDF2

            with open(pdf_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_parts = []

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                embedded_text = "\n\n".join(text_parts)

            # If we got meaningful text, return it
            if embedded_text and len(embedded_text.strip()) > 50:
                logger.info(f"Extracted embedded text from PDF: {pdf_path}")
                return embedded_text

            # Otherwise, fall back to OCR
            logger.info(f"No embedded text found, using OCR for PDF: {pdf_path}")
            return self._ocr_pdf(pdf_path)

        except Exception as e:
            logger.error(f"PDF extraction error for {pdf_path}: {str(e)}")
            # Try OCR as fallback
            return self._ocr_pdf(pdf_path)

    def _ocr_pdf(self, pdf_path: str) -> str:
        """
        Perform OCR on a PDF by converting to images.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text.
        """
        try:
            from pdf2image import convert_from_path

            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=200)

            all_text = []
            reader = get_ocr_reader()

            for i, image in enumerate(images):
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format="PNG")
                img_bytes = img_byte_arr.getvalue()

                # Save to temp file for EasyOCR
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name

                # OCR the page
                results = reader.readtext(tmp_path)
                page_text = "\n".join([r[1] for r in results])
                all_text.append(f"--- Page {i + 1} ---\n{page_text}")

                # Clean up
                Path(tmp_path).unlink()

            extracted_text = "\n\n".join(all_text)
            logger.info(f"OCR extracted text from {len(images)} PDF pages")
            return extracted_text

        except Exception as e:
            logger.error(f"PDF OCR error: {str(e)}")
            raise

    def extract_text_from_docx(self, docx_path: str) -> str:
        """
        Extract text from a Word document.

        Args:
            docx_path: Path to the DOCX file.

        Returns:
            Extracted text.
        """
        try:
            from docx import Document

            doc = Document(docx_path)
            paragraphs = [p.text for p in doc.paragraphs]

            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        paragraphs.append(cell.text)

            extracted_text = "\n".join(paragraphs)
            logger.info(f"Extracted text from DOCX: {docx_path}")
            return extracted_text

        except Exception as e:
            logger.error(f"DOCX extraction error for {docx_path}: {str(e)}")
            raise

    async def extract_text(
        self,
        file_path: str,
        source_format: SourceFormat,
    ) -> str:
        """
        Extract text from a file based on its format.

        Args:
            file_path: Path to the file.
            source_format: Format of the source file.

        Returns:
            Extracted text.
        """
        if source_format == SourceFormat.PDF:
            return self.extract_text_from_pdf(file_path)
        elif source_format in (SourceFormat.DOCX, SourceFormat.DOC):
            return self.extract_text_from_docx(file_path)
        elif source_format == SourceFormat.IMAGE:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported format: {source_format}")


# Global OCR service instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get the global OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
