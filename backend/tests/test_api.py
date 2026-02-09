"""
Backend API Tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import tempfile

# Import app
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    import io
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAssignmentEndpoints:
    """Test assignment-related endpoints."""

    def test_list_assignments_empty(self, client):
        """Test listing assignments when none exist."""
        response = client.get("/api/assignments")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @patch("app.services.ocr_service.OCRService.extract_text")
    def test_upload_assignment(self, mock_ocr, client, sample_image):
        """Test uploading an assignment."""
        mock_ocr.return_value = "Sample extracted text"

        response = client.post(
            "/api/assignments/upload",
            files={"file": ("test.png", sample_image, "image/png")},
            data={"student_name": "Test Student"},
        )

        assert response.status_code in [200, 201]

    def test_get_nonexistent_assignment(self, client):
        """Test getting a non-existent assignment."""
        response = client.get("/api/assignments/nonexistent-id")
        assert response.status_code == 404


class TestTemplateEndpoints:
    """Test template-related endpoints."""

    def test_list_templates(self, client):
        """Test listing grading templates."""
        response = client.get("/api/templates")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_template(self, client):
        """Test creating a grading template."""
        template_data = {
            "name": "Test Template",
            "description": "A test template",
            "question_types": [
                {
                    "type": "mcq",
                    "name": "Multiple Choice",
                    "weight": 50,
                    "enabled": True,
                },
                {"type": "essay", "name": "Essay", "weight": 50, "enabled": True},
            ],
            "encouragement_words": ["Great!", "Excellent!"],
        }

        response = client.post("/api/templates", json=template_data)
        assert response.status_code in [200, 201]

        data = response.json()
        assert data["name"] == "Test Template"


class TestSettingsEndpoints:
    """Test settings-related endpoints."""

    def test_get_teacher_profile(self, client):
        """Test getting teacher profile."""
        response = client.get("/api/settings/profile")
        # Should return 200 even if no profile exists
        assert response.status_code == 200

    def test_update_teacher_profile(self, client):
        """Test updating teacher profile."""
        profile_data = {
            "name": "Test Teacher",
            "email": "teacher@test.com",
            "bio": "A test teacher",
        }

        response = client.put("/api/settings/profile", json=profile_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test Teacher"

    def test_get_ai_config(self, client):
        """Test getting AI configuration."""
        response = client.get("/api/settings/ai-config")
        assert response.status_code == 200

    def test_update_ai_config(self, client):
        """Test updating AI configuration."""
        config_data = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        response = client.put("/api/settings/ai-config", json=config_data)
        assert response.status_code == 200


class TestGreetingEndpoint:
    """Test greeting endpoint."""

    @patch("app.services.greeting_service.GreetingService.generate_greeting")
    def test_get_greeting(self, mock_greeting, client):
        """Test getting personalized greeting."""
        mock_greeting.return_value = {
            "greeting": "Welcome back, Teacher!",
            "source": {"title": "Test Book", "author": "Test Author"},
        }

        response = client.get("/api/greeting")
        assert response.status_code == 200


class TestCacheEndpoints:
    """Test cache-related endpoints."""

    def test_get_cache_stats(self, client):
        """Test getting cache statistics."""
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_articles" in data
        assert "cache_size" in data

    def test_clear_cache(self, client):
        """Test clearing the cache."""
        response = client.delete("/api/cache")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
