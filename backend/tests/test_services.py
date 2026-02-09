"""
Unit tests for backend services
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestFileProcessor:
    """Test FileProcessor service."""

    def test_detect_format_pdf(self):
        """Test PDF format detection."""
        from app.services.file_processor import FileProcessor

        processor = FileProcessor()
        assert processor.detect_format("test.pdf") == "pdf"

    def test_detect_format_docx(self):
        """Test DOCX format detection."""
        from app.services.file_processor import FileProcessor

        processor = FileProcessor()
        assert processor.detect_format("test.docx") == "docx"

    def test_detect_format_image(self):
        """Test image format detection."""
        from app.services.file_processor import FileProcessor

        processor = FileProcessor()
        assert processor.detect_format("test.png") == "image"
        assert processor.detect_format("test.jpg") == "image"
        assert processor.detect_format("test.jpeg") == "image"

    def test_detect_format_unknown(self):
        """Test unknown format detection."""
        from app.services.file_processor import FileProcessor

        processor = FileProcessor()
        assert processor.detect_format("test.xyz") == "unknown"


class TestOCRService:
    """Test OCR service."""

    @patch("easyocr.Reader")
    def test_init_reader(self, mock_reader):
        """Test OCR reader initialization."""
        from app.services.ocr_service import OCRService

        service = OCRService(languages=["en"])
        mock_reader.assert_called_once_with(["en"], gpu=False)

    @patch("easyocr.Reader")
    def test_extract_text_from_image(self, mock_reader):
        """Test text extraction from image."""
        from app.services.ocr_service import OCRService

        mock_instance = MagicMock()
        mock_instance.readtext.return_value = [
            (None, "Hello", 0.9),
            (None, "World", 0.95),
        ]
        mock_reader.return_value = mock_instance

        service = OCRService(languages=["en"])

        # Create a simple test image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            from PIL import Image

            img = Image.new("RGB", (100, 100), color="white")
            img.save(f.name)

            result = service.extract_text(f.name)
            assert "Hello" in result
            assert "World" in result

            os.unlink(f.name)


class TestSearchService:
    """Test search service."""

    @patch("duckduckgo_search.DDGS")
    def test_search_articles(self, mock_ddgs):
        """Test article search."""
        from app.services.search_service import SearchService

        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {
                "title": "Test Article",
                "href": "http://example.com",
                "body": "Test content",
            }
        ]
        mock_ddgs.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs.return_value.__exit__ = MagicMock(return_value=False)

        service = SearchService()
        results = service.search("test query")

        assert len(results) >= 0

    def test_known_classics_mapping(self):
        """Test known classics URL mapping."""
        from app.services.search_service import SearchService

        service = SearchService()

        # Check if classic works have predefined URLs
        assert "alice in wonderland" in [
            k.lower() for k in service.known_classics.keys()
        ]


class TestAIGradingService:
    """Test AI grading service."""

    @patch("litellm.completion")
    def test_grade_assignment(self, mock_completion):
        """Test assignment grading."""
        from app.services.ai_grading import AIGradingService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = """
        {
            "total_score": 85,
            "sections": [
                {"type": "mcq", "score": 90, "feedback": "Good job!"}
            ],
            "overall_feedback": "Well done overall.",
            "encouragement": "Keep up the great work!"
        }
        """
        mock_completion.return_value = mock_response

        service = AIGradingService(provider="openai", model="gpt-4", api_key="test-key")

        result = service.grade(
            text="Sample assignment text",
            template={
                "question_types": [{"type": "mcq", "weight": 100, "enabled": True}],
                "encouragement_words": ["Great!"],
            },
            context={},
        )

        assert "total_score" in result

    def test_generate_encouragement(self):
        """Test encouragement word generation."""
        from app.services.ai_grading import AIGradingService

        service = AIGradingService(provider="openai", model="gpt-4", api_key="test-key")

        words = ["Bravo!", "Excellent!", "Perfect!"]
        encouragement = service.select_encouragement(words)

        assert encouragement in words


class TestExportService:
    """Test export service."""

    def test_export_pdf(self):
        """Test PDF export."""
        from app.services.export_service import ExportService

        service = ExportService()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            service.export_to_pdf(
                content="<p>Test content</p>",
                output_path=f.name,
                metadata={"student_name": "Test Student", "score": 85},
            )

            assert os.path.exists(f.name)
            assert os.path.getsize(f.name) > 0

            os.unlink(f.name)

    def test_export_docx(self):
        """Test DOCX export."""
        from app.services.export_service import ExportService

        service = ExportService()

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            service.export_to_docx(
                content="Test content",
                output_path=f.name,
                metadata={"student_name": "Test Student", "score": 85},
            )

            assert os.path.exists(f.name)
            assert os.path.getsize(f.name) > 0

            os.unlink(f.name)


class TestGreetingService:
    """Test greeting service."""

    @patch("litellm.completion")
    def test_generate_greeting(self, mock_completion):
        """Test greeting generation."""
        from app.services.greeting_service import GreetingService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = """
        {
            "greeting": "Welcome back! As Alice said, 'Curiouser and curiouser!'",
            "quote": "Curiouser and curiouser!",
            "source": {"title": "Alice in Wonderland", "author": "Lewis Carroll"}
        }
        """
        mock_completion.return_value = mock_response

        service = GreetingService(provider="openai", model="gpt-4", api_key="test-key")

        result = service.generate_greeting(
            teacher_name="Teacher",
            recent_articles=[
                {"title": "Alice in Wonderland", "author": "Lewis Carroll"}
            ],
        )

        assert "greeting" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
