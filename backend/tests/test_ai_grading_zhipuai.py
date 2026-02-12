"""
Tests for AI grading with ZhipuAI via the generic LLM provider interface.
Verifies get_llm_provider uses DB config and ZhipuAI implementation (model normalization, api_base).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.database import get_session_local, init_db
from app.models import Settings
from app.services.ai_grading import AIGradingService
from app.services.ai_providers.llm_zhipuai import ZhipuAILLMProvider, _normalize_model
from app.services.ai_providers.llm_factory import get_llm_provider, get_llm_provider_for_config

SKIP_NO_ZHIPUAI = (
    "No ZhipuAI config in database. Please configure AI provider in Settings "
    "(type=ai-config, provider=zhipuai) first, then run the test."
)


@pytest.fixture
def db():
    """Database session for tests."""
    init_db()
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _require_zhipuai_config(db):
    """Require existing ai-config with provider=zhipuai. Skip if missing."""
    rec = db.query(Settings).filter(Settings.type == "ai-config").first()
    if not rec or not rec.config:
        pytest.skip(SKIP_NO_ZHIPUAI)
    if (rec.config.get("provider") or "").strip().lower() not in ("zhipuai", "zhipu"):
        pytest.skip(
            "AI config in database is not ZhipuAI. Configure provider=zhipuai in Settings (type=ai-config) first."
        )
    return rec


class TestNormalizeZhipuModel:
    """Test ZhipuAI model normalization (capitalized form)."""

    def test_glm_47_to_GLM_47(self):
        assert _normalize_model("glm-4.7") == "GLM-4.7"

    def test_glm_4_flash_to_GLM_4_flash(self):
        assert _normalize_model("glm-4-flash") == "GLM-4-flash"

    def test_already_capitalized_unchanged(self):
        assert _normalize_model("GLM-4.7") == "GLM-4.7"

    def test_empty_returns_empty(self):
        assert _normalize_model("") == ""

    def test_strip_whitespace(self):
        assert _normalize_model("  glm-4.7  ") == "GLM-4.7"


class TestZhipuAIProviderFromConfig:
    """Test get_llm_provider_for_config with ZhipuAI config."""

    def test_zhipuai_config_returns_zhipuai_provider(self):
        config = {
            "provider": "zhipuai",
            "model": "glm-4.7",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key": "test-key",
            "timeout": 300,
        }
        provider = get_llm_provider_for_config(config)
        assert isinstance(provider, ZhipuAILLMProvider)


class TestCallAiViaGenericInterface:
    """
    Test AIGradingService._call_ai uses get_llm_provider(db).complete().
    """

    @pytest.mark.asyncio
    async def test_call_ai_uses_llm_provider_complete(self, db):
        _require_zhipuai_config(db)
        service = AIGradingService(db)
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="Hello from ZhipuAI")
        with patch("app.services.ai_grading.get_llm_provider", return_value=mock_llm):
            result = await service._call_ai("Hello", system_prompt=None)
        assert result == "Hello from ZhipuAI"
        mock_llm.complete.assert_called_once()
        call_kw = mock_llm.complete.call_args.kwargs
        assert call_kw["system_prompt"] is None
        assert mock_llm.complete.call_args.args[0] == "Hello"
