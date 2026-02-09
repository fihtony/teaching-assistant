"""
Services package initialization.
"""

from app.services.file_processor import FileProcessor, get_file_processor
from app.services.ocr_service import OCRService, get_ocr_service
from app.services.search_service import SearchService, SearchResult, get_search_service
from app.services.ai_grading import AIGradingService, get_ai_grading_service
from app.services.export_service import ExportService, get_export_service
from app.services.greeting_service import GreetingService, get_greeting_service

__all__ = [
    "FileProcessor",
    "get_file_processor",
    "OCRService",
    "get_ocr_service",
    "SearchService",
    "SearchResult",
    "get_search_service",
    "AIGradingService",
    "get_ai_grading_service",
    "ExportService",
    "get_export_service",
    "GreetingService",
    "get_greeting_service",
]
