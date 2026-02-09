"""
Utility functions and helpers.
"""

import re
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename.
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    # Limit length
    if len(sanitized) > 200:
        ext_match = re.search(r"\.[a-zA-Z0-9]+$", sanitized)
        ext = ext_match.group() if ext_match else ""
        sanitized = sanitized[: 200 - len(ext)] + ext
    return sanitized


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length.
        suffix: Suffix to add if truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Text to normalize.

    Returns:
        Text with normalized whitespace.
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)
    # Replace multiple newlines with double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_title_from_text(text: str, max_length: int = 50) -> Optional[str]:
    """
    Try to extract a title from the beginning of text.

    Args:
        text: Text to extract title from.
        max_length: Maximum title length.

    Returns:
        Extracted title or None.
    """
    if not text:
        return None

    # Take first line
    first_line = text.split("\n")[0].strip()

    # Remove common prefixes
    for prefix in ["Title:", "Name:", "Assignment:"]:
        if first_line.lower().startswith(prefix.lower()):
            first_line = first_line[len(prefix) :].strip()

    # Truncate if too long
    if len(first_line) > max_length:
        first_line = first_line[:max_length] + "..."

    return first_line if first_line else None
