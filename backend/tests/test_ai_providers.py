"""
Tests for AI provider implementations (generic LLM interface).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.ai_providers import (
    get_llm_provider_for_config,
    list_llm_provider_names,
)
from app.services.ai_providers.llm_zhipuai import ZhipuAILLMProvider, _normalize_model
from app.services.ai_providers.llm_openai import OpenAILLMProvider
from app.services.ai_providers.llm_gemini import GeminiLLMProvider
from app.services.ai_providers.llm_copilot import CopilotLLMProvider

# Sample HTML grading result
SAMPLE_HTML_RESULT = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Graded Essay</title>
</head>
<body>
    <h1>Revised Essay</h1>
    <p>This is <del class="error">a test</del><span class="correction">an example</span>.</p>
    <h2>Teacher's Comments</h2>
    <p>Dear Student,</p>
    <p>Good job!</p>
</body>
</html>"""


class TestLLMProviderFactory:
    """Tests for LLM provider factory."""

    def test_get_zhipuai_provider(self):
        provider = get_llm_provider_for_config({
            "provider": "zhipuai",
            "model": "glm-4.7",
            "api_key": "test_key",
        })
        assert isinstance(provider, ZhipuAILLMProvider)

    def test_get_openai_provider(self):
        provider = get_llm_provider_for_config({
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "test_key",
        })
        assert isinstance(provider, OpenAILLMProvider)

    def test_get_gemini_provider(self):
        provider = get_llm_provider_for_config({
            "provider": "gemini",
            "model": "gemini-1.5-pro",
            "api_key": "test_key",
        })
        assert isinstance(provider, GeminiLLMProvider)

    def test_get_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            get_llm_provider_for_config({"provider": "unknown", "api_key": "x"})

    def test_list_llm_provider_names(self):
        names = list_llm_provider_names()
        assert "zhipuai" in names
        assert "openai" in names
        assert "gemini" in names
        assert "copilot" in names


class TestZhipuAIModelNormalization:
    """Tests for ZhipuAI model name normalization."""

    def test_glm_47_to_GLM_47(self):
        assert _normalize_model("glm-4.7") == "GLM-4.7"

    def test_glm_4_flash(self):
        assert _normalize_model("glm-4-flash") == "GLM-4-flash"


class TestZhipuAILLMProviderComplete:
    """Tests for ZhipuAI LLM provider complete()."""

    @pytest.mark.asyncio
    async def test_complete_calls_litellm_with_correct_params(self):
        config = {
            "provider": "zhipuai",
            "model": "glm-4.7",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key": "test_key",
            "timeout": 300,
        }
        provider = ZhipuAILLMProvider(config)
        with patch("app.services.ai_providers.llm_zhipuai.completion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = "Hello from ZhipuAI"
            result = await provider.complete("Hello", system_prompt="You are helpful.")
        assert result == "Hello from ZhipuAI"
        mock_completion.assert_called_once()
        call_kw = mock_completion.call_args.kwargs
        assert call_kw["model"] == "openai/GLM-4.7"
        assert call_kw["api_base"] == "https://open.bigmodel.cn/api/paas/v4"
        assert call_kw["api_key"] == "test_key"
        assert call_kw["messages"] == [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

    @pytest.mark.asyncio
    async def test_complete_raises_without_api_key(self):
        provider = ZhipuAILLMProvider({"provider": "zhipuai", "model": "glm-4-flash"})
        with pytest.raises(ValueError, match="No API key"):
            await provider.complete("Hi")


class TestProviderResponseParsing:
    """Tests for parsing AI responses."""

    def test_parse_html_response(self):
        from app.services.html_generator import parse_ai_response

        ai_response = """<h1>Revised Essay</h1>
<p>Some text <del class="error">wrong</del><span class="correction">correct</span>.</p>

<h2>Detailed Corrections</h2>
<ul>
  <li>Fixed spelling error</li>
</ul>

<h2>Teacher's Comments</h2>
<p>Dear Student,</p>
<p>Good job!</p>
"""

        essay_html, corrections_html, comments_html = parse_ai_response(ai_response)

        assert "Some text <del class=\"error\">wrong</del><span class=\"correction\">correct</span>." in essay_html
        assert "<h2>Detailed Corrections</h2>" in corrections_html
        assert "<h2>Teacher's Comments</h2>" in comments_html

    def test_parse_response_without_sections(self):
        from app.services.html_generator import parse_ai_response

        ai_response = """Just some text without proper HTML structure."""

        essay_html, corrections_html, comments_html = parse_ai_response(ai_response)

        assert essay_html.strip() == ai_response.strip()
        assert corrections_html == ""
        assert comments_html == ""


class TestFileHandler:
    """Tests for file handling."""

    def test_read_txt_file(self, tmp_path):
        from app.services.file_handler import read_essay

        test_file = tmp_path / "test_essay.txt"
        test_file.write_text("This is a test essay content.")

        result = read_essay(str(test_file))
        assert result == "This is a test essay content."

    def test_read_txt_file_with_unicode(self, tmp_path):
        from app.services.file_handler import read_essay

        test_file = tmp_path / "test_unicode.txt"
        test_file.write_text("This is a test with émojis 🎉 and spëcial çharacters.")

        result = read_essay(str(test_file))
        assert "émojis 🎉" in result
        assert "spëcial çharacters" in result

    def test_read_unsupported_file_type(self, tmp_path):
        from app.services.file_handler import read_essay

        test_file = tmp_path / "test.xyz"
        test_file.write_text("Some content")

        with pytest.raises(ValueError, match="Unsupported file"):
            read_essay(str(test_file))


class TestHTMLGenerator:
    """Tests for HTML generation."""

    def test_generate_html(self, tmp_path):
        from app.services.html_generator import HTMLGenerator

        generator = HTMLGenerator()
        output_path = tmp_path / "test_output.html"

        generator.generate(
            essay="<p>Test essay.</p>",
            corrections="<ul><li>Fixed error</li></ul>",
            comments="<p>Good job!</p>",
            output_path=str(output_path),
            student_name="Test Student",
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "Test essay." in content
        assert "Good job!" in content
        assert "Graded Essay - Test Student" in content

    def test_get_css_styles(self):
        from app.services.html_generator import HTMLGenerator

        generator = HTMLGenerator()
        css = generator._get_css_styles()

        assert ".error" in css
        assert "text-decoration: line-through" in css
        assert ".correction" in css
        assert "color: #e74c3c" in css
