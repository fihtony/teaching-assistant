"""
AIConfigModel model for storing AI provider configuration.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Text, Boolean, Float, Integer

from app.core.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class AIConfigModel(Base):
    """
    AI configuration model.

    Stores AI provider settings and encrypted API keys.
    """

    __tablename__ = "ai_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Provider settings
    default_provider = Column(String(50), default="openai")
    default_model = Column(String(100), default="gpt-4o")
    api_base_url = Column(String(255), nullable=True)  # Base URL for custom endpoints
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)

    # Copilot Bridge configuration (as a standalone provider)
    copilot_base_url = Column(String(255), default="http://localhost:1287")
    copilot_api_key = Column(Text, nullable=True)  # Not required, but can be provided

    # Encrypted API keys (stored as encrypted strings)
    openai_api_key = Column(Text, nullable=True)
    anthropic_api_key = Column(Text, nullable=True)
    google_api_key = Column(Text, nullable=True)

    # Search engine configuration
    search_engine = Column(String(50), default="duckduckgo")
    google_search_api_key = Column(Text, nullable=True)
    google_search_cx = Column(Text, nullable=True)

    # Status flags
    is_configured = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AIConfigModel(id={self.id}, provider={self.default_provider})>"


# Singleton config ID for single-user mode
DEFAULT_AI_CONFIG_ID = "default-ai-config-001"
