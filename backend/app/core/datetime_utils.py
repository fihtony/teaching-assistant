"""
Utility functions for handling timezone-aware timestamps.
All timestamps use ISO 8601 format with timezone offset: 2026-01-31T10:43:03-05:00
"""

from datetime import datetime, timezone
from typing import Optional


def get_now_with_timezone() -> datetime:
    """
    Get current time with timezone information.
    Returns timezone-aware datetime in local timezone.
    """
    return datetime.now(timezone.utc).astimezone()


def to_iso_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to ISO 8601 string with timezone offset.
    Example: 2026-01-31T10:43:03-05:00
    """
    if dt is None:
        return None

    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone()
    else:
        dt = dt.astimezone()

    return dt.isoformat()


def from_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO 8601 string with timezone offset to datetime.
    Example: 2026-01-31T10:43:03-05:00
    """
    if dt_str is None:
        return None

    return datetime.fromisoformat(dt_str)
