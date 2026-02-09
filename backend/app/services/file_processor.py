"""
File processing service for handling uploaded documents.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
import shutil

from app.core.config import get_storage_path
from app.core.logging import get_logger
from app.models.assignment import SourceFormat

logger = get_logger()


class FileProcessor:
    """
    Service for processing uploaded files.

    Handles file storage, format detection, and basic file operations.
    """

    ALLOWED_EXTENSIONS = {
        ".pdf": SourceFormat.PDF,
        ".docx": SourceFormat.DOCX,
        ".doc": SourceFormat.DOC,
        ".png": SourceFormat.IMAGE,
        ".jpg": SourceFormat.IMAGE,
        ".jpeg": SourceFormat.IMAGE,
    }

    def __init__(self):
        self.uploads_dir = get_storage_path("uploads")
        self.graded_dir = get_storage_path("graded")

    def get_file_extension(self, filename: str) -> str:
        """Get the file extension in lowercase."""
        return Path(filename).suffix.lower()

    def detect_format(self, filename: str) -> Optional[SourceFormat]:
        """
        Detect the source format based on file extension.

        Args:
            filename: Original filename.

        Returns:
            SourceFormat enum value or None if unsupported.
        """
        ext = self.get_file_extension(filename)
        return self.ALLOWED_EXTENSIONS.get(ext)

    def is_supported_format(self, filename: str) -> bool:
        """Check if the file format is supported."""
        return self.detect_format(filename) is not None

    def generate_stored_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename for storage.

        Args:
            original_filename: Original filename from upload.

        Returns:
            Unique filename with UUID prefix.
        """
        ext = self.get_file_extension(original_filename)
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"

    async def save_upload(
        self,
        file_content: bytes,
        original_filename: str,
    ) -> Tuple[str, str, SourceFormat]:
        """
        Save an uploaded file to the uploads directory.

        Args:
            file_content: Raw file content.
            original_filename: Original filename from upload.

        Returns:
            Tuple of (stored_filename, file_path, source_format).

        Raises:
            ValueError: If file format is not supported.
        """
        source_format = self.detect_format(original_filename)
        if source_format is None:
            raise ValueError(f"Unsupported file format: {original_filename}")

        stored_filename = self.generate_stored_filename(original_filename)
        file_path = self.uploads_dir / stored_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(
            f"Saved uploaded file: {stored_filename} (original: {original_filename})"
        )

        return stored_filename, str(file_path), source_format

    def get_upload_path(self, stored_filename: str) -> Path:
        """Get the full path to an uploaded file."""
        return self.uploads_dir / stored_filename

    def get_graded_path(self, stored_filename: str) -> Path:
        """Get the full path for a graded file."""
        return self.graded_dir / stored_filename

    def save_graded_file(
        self,
        content: bytes,
        original_stored_filename: str,
        output_format: SourceFormat,
    ) -> str:
        """
        Save a graded file to the graded directory.

        Args:
            content: Graded file content.
            original_stored_filename: Original stored filename.
            output_format: Output file format.

        Returns:
            Graded filename.
        """
        # Generate graded filename
        base_name = Path(original_stored_filename).stem
        ext_map = {
            SourceFormat.PDF: ".pdf",
            SourceFormat.DOCX: ".docx",
            SourceFormat.DOC: ".docx",  # Convert to docx
            SourceFormat.IMAGE: ".pdf",  # Convert images to PDF
        }
        ext = ext_map.get(output_format, ".pdf")
        graded_filename = f"{base_name}_graded{ext}"

        graded_path = self.graded_dir / graded_filename

        with open(graded_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved graded file: {graded_filename}")

        return graded_filename

    def delete_file(self, stored_filename: str, directory: str = "uploads") -> bool:
        """
        Delete a file from storage.

        Args:
            stored_filename: Stored filename to delete.
            directory: 'uploads' or 'graded'.

        Returns:
            True if deleted, False if file not found.
        """
        if directory == "uploads":
            file_path = self.uploads_dir / stored_filename
        else:
            file_path = self.graded_dir / stored_filename

        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Deleted file: {stored_filename} from {directory}")
            return True

        return False

    def get_file_size(self, stored_filename: str) -> str:
        """
        Get the file size in human-readable format.

        Args:
            stored_filename: Stored filename.

        Returns:
            File size string (e.g., "1.5 MB").
        """
        file_path = self.uploads_dir / stored_filename
        if not file_path.exists():
            return "0 B"

        size = file_path.stat().st_size

        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return f"{size:.1f} TB"


# Global file processor instance
_file_processor: Optional[FileProcessor] = None


def get_file_processor() -> FileProcessor:
    """Get the global file processor instance."""
    global _file_processor
    if _file_processor is None:
        _file_processor = FileProcessor()
    return _file_processor
