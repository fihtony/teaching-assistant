"""
Tests for AI grading service with ZhipuAI config read from database (Settings type=ai-config).
Verifies model normalization (GLM-4.7), litellm model string (openai/GLM-4.7), and api_base.

Does NOT insert or delete ai-config. If no ZhipuAI config exists in DB, tests that need it are skipped.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.database import get_session_local, init_db
from app.models import Settings
from app.services.ai_grading import AIGradingService

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
    """
    Require existing ai-config with provider=zhipuai. Skip with message if missing.
    Does not modify the Settings table.
    """
    rec = db.query(Settings).filter(Settings.type == "ai-config").first()
    if not rec or not rec.config:
        pytest.skip(SKIP_NO_ZHIPUAI)
    if (rec.config.get("provider") or "").strip().lower() not in ("zhipuai", "zhipu"):
        pytest.skip(
            "AI config in database is not ZhipuAI. Configure provider=zhipuai in Settings (type=ai-config) first."
        )
    return rec


class TestNormalizeZhipuModel:
    """Test _normalize_zhipu_model (capitalized model name). No DB required."""

    def test_glm_47_to_GLM_47(self):
        assert AIGradingService._normalize_zhipu_model("glm-4.7") == "GLM-4.7"

    def test_glm_4_flash_to_GLM_4_flash(self):
        assert AIGradingService._normalize_zhipu_model("glm-4-flash") == "GLM-4-flash"

    def test_already_capitalized_unchanged(self):
        assert AIGradingService._normalize_zhipu_model("GLM-4.7") == "GLM-4.7"

    def test_empty_returns_empty(self):
        assert AIGradingService._normalize_zhipu_model("") == ""

    def test_strip_whitespace(self):
        assert AIGradingService._normalize_zhipu_model("  glm-4.7  ") == "GLM-4.7"


class TestBuildLitellmModelFromDb:
    """
    Test _build_litellm_model_and_base reads config from DB. Uses existing ai-config only.
    Skipped if no ZhipuAI config in database.
    """

    def test_zhipuai_returns_openai_GLM47_and_base(self, db):
        _require_zhipuai_config(db)
        service = AIGradingService(db)
        litellm_model, api_base, api_key = service._build_litellm_model_and_base(
            "zhipuai", "glm-4.7"
        )
        assert litellm_model == "openai/GLM-4.7"
        assert api_base == "https://open.bigmodel.cn/api/coding/paas/v4"
        assert api_key is not None and len(api_key) > 0

    def test_zhipu_alias_same_as_zhipuai(self, db):
        _require_zhipuai_config(db)
        service = AIGradingService(db)
        litellm_model, api_base, api_key = service._build_litellm_model_and_base(
            "zhipu", "glm-4.7"
        )
        assert litellm_model == "openai/GLM-4.7"
        assert api_base == "https://open.bigmodel.cn/api/coding/paas/v4"
        assert api_key is not None

    def test_get_ai_config_returns_db_record(self, db):
        rec = _require_zhipuai_config(db)
        service = AIGradingService(db)
        ai_config = service._get_ai_config()
        assert ai_config is not None
        assert ai_config.type == "ai-config"
        assert (ai_config.config.get("provider") or "").strip().lower() in (
            "zhipuai",
            "zhipu",
        )
        assert ai_config.config.get("model")


class TestCallAiWithZhipuaiConfig:
    """
    Test _call_ai uses config from database and calls LiteLLM with correct params.
    Skipped if no ZhipuAI config in database. Does not modify Settings.
    """

    @pytest.mark.asyncio
    async def test_call_ai_uses_litellm_with_openai_GLM47_and_base(self, db):
        _require_zhipuai_config(db)
        service = AIGradingService(db)
        with patch("app.services.ai_grading.AIGradingService._get_litellm") as mock_get:
            mock_ll = MagicMock()
            mock_ll.acompletion = AsyncMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content="Hello from ZhipuAI"))]
                )
            )
            mock_get.return_value = mock_ll

            result = await service._call_ai("Hello", system_prompt=None)

            assert result == "Hello from ZhipuAI"
            mock_ll.acompletion.assert_called_once()
            call_kw = mock_ll.acompletion.call_args.kwargs
            assert call_kw["model"] == "openai/GLM-4.7"
            assert call_kw["api_base"] == "https://open.bigmodel.cn/api/coding/paas/v4"
            assert call_kw.get("api_key") is not None and len(call_kw["api_key"]) > 0
            assert call_kw["messages"] == [{"role": "user", "content": "Hello"}]
