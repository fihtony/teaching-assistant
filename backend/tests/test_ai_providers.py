"""
Tests for AI provider implementations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.ai_providers.factory import get_provider
from app.services.ai_providers.zhipuai import ZhipuAIProvider
from app.services.ai_providers.gemini import GeminiProvider

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


class TestProviderFactory:
    """Tests for provider factory."""

    def test_get_zhipuai_provider(self):
        """Test getting ZhipuAI provider."""
        provider = get_provider("zhipuai", "test_key", "glm-4.7")
        assert isinstance(provider, ZhipuAIProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "glm-4.7"

    def test_get_gemini_provider(self):
        """Test getting Gemini provider."""
        provider = get_provider("gemini", "test_key", "gemini-1.5-pro")
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "gemini-1.5-pro"

    def test_get_unknown_provider(self):
        """Test getting unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown_provider", "test_key")

    def test_list_providers(self):
        """Test listing all providers."""
        from app.services.ai_providers.factory import list_providers
        providers = list_providers()
        assert "zhipuai" in providers
        assert "gemini" in providers


class TestZhipuAIProvider:
    """Tests for ZhipuAI provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = ZhipuAIProvider("test_key")
        assert provider.api_key == "test_key"
        assert provider.model is None  # Uses default

        provider_with_model = ZhipuAIProvider("test_key", "glm-4-flash")
        assert provider_with_model.model == "glm-4-flash"

    def test_build_prompt_basic(self):
        """Test building prompt with basic parameters."""
        provider = ZhipuAIProvider("test_key")
        prompt = provider._build_prompt(
            essay="My essay text.",
            requirements="Grade this well.",
        )

        assert "My essay text." in prompt
        assert "Grade this well." in prompt
        assert "Student" in prompt

    def test_build_prompt_with_context(self):
        """Test building prompt with full context."""
        provider = ZhipuAIProvider("test_key")
        prompt = provider._build_prompt(
            essay="My essay text.",
            requirements="Grade this well.",
            student_name="John Doe",
            student_level="Grade 5",
            recent_activity="Reading books",
        )

        assert "John Doe" in prompt
        assert "My essay text." in prompt
        assert "Grade this well." in prompt

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing HTTP client."""
        provider = ZhipuAIProvider("test_key")

        # Create client first
        await provider._get_client()
        assert provider._client is not None

        # Close client
        await provider.close()
        assert provider._client is None


class TestGeminiProvider:
    """Tests for Gemini provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = GeminiProvider("test_key")
        assert provider.api_key == "test_key"
        assert provider.model is None  # Uses default

        provider_with_model = GeminiProvider("test_key", "gemini-1.5-flash")
        assert provider_with_model.model == "gemini-1.5-flash"

    def test_build_prompt_basic(self):
        """Test building prompt with basic parameters."""
        provider = GeminiProvider("test_key")
        prompt = provider._build_prompt(
            essay="My essay text.",
            requirements="Grade this well.",
        )

        assert "My essay text." in prompt
        assert "Grade this well." in prompt
        assert "Student" in prompt


class TestProviderResponseParsing:
    """Tests for parsing AI responses."""

    def test_parse_html_response(self):
        """Test parsing HTML response from AI."""
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

        # essay_html contains the essay paragraphs (not the h1 header)
        assert "Some text <del class=\"error\">wrong</del><span class=\"correction\">correct</span>." in essay_html
        assert "<h2>Detailed Corrections</h2>" in corrections_html
        assert "<h2>Teacher's Comments</h2>" in comments_html

    def test_parse_response_without_sections(self):
        """Test parsing response when sections are not properly separated."""
        from app.services.html_generator import parse_ai_response

        ai_response = """Just some text without proper HTML structure."""

        essay_html, corrections_html, comments_html = parse_ai_response(ai_response)

        # Should return what we have
        assert essay_html.strip() == ai_response.strip()
        assert corrections_html == ""
        assert comments_html == ""


class TestFileHandler:
    """Tests for file handling."""

    def test_read_txt_file(self, tmp_path):
        """Test reading .txt file."""
        from app.services.file_handler import read_essay

        # Create test file
        test_file = tmp_path / "test_essay.txt"
        test_file.write_text("This is a test essay content.")

        result = read_essay(str(test_file))
        assert result == "This is a test essay content."

    def test_read_txt_file_with_unicode(self, tmp_path):
        """Test reading .txt file with unicode content."""
        from app.services.file_handler import read_essay

        # Create test file with unicode
        test_file = tmp_path / "test_unicode.txt"
        test_file.write_text("This is a test with émojis 🎉 and spëcial çharacters.")

        result = read_essay(str(test_file))
        assert "émojis 🎉" in result
        assert "spëcial çharacters" in result

    def test_read_unsupported_file_type(self, tmp_path):
        """Test reading unsupported file type raises error."""
        from app.services.file_handler import read_essay

        # Create test file
        test_file = tmp_path / "test.xyz"
        test_file.write_text("Some content")

        with pytest.raises(ValueError, match="Unsupported file"):
            read_essay(str(test_file))


class TestHTMLGenerator:
    """Tests for HTML generation."""

    def test_generate_html(self, tmp_path):
        """Test generating complete HTML file."""
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

        # Verify file was created
        assert output_path.exists()

        # Verify content
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "Test essay." in content
        assert "Good job!" in content
        assert "Graded Essay - Test Student" in content

    def test_get_css_styles(self):
        """Test CSS styles are included."""
        from app.services.html_generator import HTMLGenerator

        generator = HTMLGenerator()
        css = generator._get_css_styles()

        assert ".error" in css
        assert "text-decoration: line-through" in css
        assert ".correction" in css
        assert "color: #e74c3c" in css


@pytest.mark.integration
class TestIntegrationWithMocks:
    """Integration tests with mocked AI responses."""

    @pytest.mark.asyncio
    async def test_zhipuai_with_mock_response(self):
        """Test ZhipuAI provider with mocked HTTP response."""
        provider = ZhipuAIProvider("test_key")

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": SAMPLE_HTML_RESULT
                    }
                }
            ]
        }
        mock_client.post.return_value = mock_response

        # Set mock client
        provider._client = mock_client

        # Test grading
        result = await provider.grade_essay(
            essay="Test essay.",
            requirements="Grade this.",
        )

        assert result == SAMPLE_HTML_RESULT

    @pytest.mark.asyncio
    async def test_gemini_with_mock_response(self):
        """Test Gemini provider with mocked response."""
        provider = GeminiProvider("test_key")

        # Mock model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = SAMPLE_HTML_RESULT
        mock_model.generate_content.return_value = mock_response

        # Set mock model
        provider._model = mock_model

        # Test grading
        result = await provider.grade_essay(
            essay="Test essay.",
            requirements="Grade this.",
        )

        assert result == SAMPLE_HTML_RESULT
