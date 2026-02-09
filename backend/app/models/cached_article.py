"""
CachedArticle model for storing fetched article content.
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, Text, Boolean

from app.core.database import Base
from app.core.config import get_config
from app.core.datetime_utils import get_now_with_timezone


class CachedArticle(Base):
    """
    Cached article model.

    Stores article content fetched from the web to avoid
    repeated searches and improve performance.
    Uses auto-increment integer primary key.
    """

    __tablename__ = "cached_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Article identification
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=True)

    # Source information
    source_url = Column(Text, nullable=True)
    source_type = Column(
        String(50), nullable=True
    )  # e.g., "gutenberg", "wikipedia", "web"

    # Content
    full_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # Notable quotes for greetings
    notable_quotes = Column(Text, nullable=True)  # JSON array of quotes

    # Cache metadata
    search_query = Column(String(500), nullable=True)  # Original search query
    cached_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    expires_at = Column(String, nullable=True)
    is_expired = Column(Boolean, default=False)

    # Usage tracking
    access_count = Column(Integer, default=0)
    last_accessed = Column(String, default=lambda: get_now_with_timezone().isoformat())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "expires_at" not in kwargs or kwargs["expires_at"] is None:
            config = get_config()
            cache_days = config.article_cache.cache_days
            expires_dt = get_now_with_timezone() + timedelta(days=cache_days)
            self.expires_at = expires_dt.isoformat()

    def is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self.is_expired:
            return False
        if self.expires_at is None:
            return True
        # Parse ISO timestamp to datetime
        from app.core.datetime_utils import from_iso_datetime

        expires_dt = from_iso_datetime(self.expires_at)
        return get_now_with_timezone() < expires_dt

    def __repr__(self) -> str:
        return f"<CachedArticle(id={self.id}, title={self.title[:50]}...)>"
