"""
Settings model for storing application configuration.
Replaces the old AIConfigModel.
"""

from sqlalchemy import Column, Integer, String, JSON

from app.core.database import Base
from app.core.datetime_utils import get_now_with_timezone


class Settings(Base):
    """
    Application settings/configuration model.
    Stores configuration for different features (AI, search, etc).
    Using a flexible JSON structure to support multiple config types.
    """

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)  # e.g., "ai-config", "search"
    config = Column(JSON, nullable=False)  # Configuration in JSON format
    created_at = Column(String, default=lambda: get_now_with_timezone().isoformat())
    updated_at = Column(
        String,
        default=lambda: get_now_with_timezone().isoformat(),
        onupdate=lambda: get_now_with_timezone().isoformat(),
    )

    def __repr__(self) -> str:
        return f"<Settings(id={self.id}, type={self.type})>"
