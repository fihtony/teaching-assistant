"""
AI Provider Configuration model for storing teacher's AI settings.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIProviderConfig(Base):
    """
    Store AI provider configurations per teacher.
    API keys are encrypted before storage.
    """

    __tablename__ = "ai_provider_config"

    id = Column(String, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    provider = Column(String, nullable=False)  # zhipuai, gemini, openai, etc.
    api_key_encrypted = Column(String, nullable=False)
    model = Column(String)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = relationship("Teacher", back_populates="ai_configs")
