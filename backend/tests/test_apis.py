"""
Comprehensive API tests for the English Teaching Assignment Grading System.
Tests all endpoints and verifies data is correctly stored in the database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from app.core.database import (
    get_db,
    get_engine,
    Base,
    get_session_local,
    init_db,
    drop_db,
)
from app.models import Teacher, Settings, GradingTemplate


@pytest.fixture(scope="function", autouse=True)
def setup_teardown():
    """Setup and teardown for each test."""
    init_db()
    yield
    drop_db()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def db():
    """Create a test database session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    yield db
    db.close()


class TestTeacherProfileAPI:
    """Test cases for teacher profile endpoints."""

    def test_get_teacher_profile_default(self, client, db):
        """Test getting the default teacher profile."""
        response = client.get("/api/v1/settings/teacher-profile")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Teacher"
        assert data["id"] == 1

        # Verify in database
        teacher = db.query(Teacher).filter(Teacher.id == 1).first()
        assert teacher is not None
        assert teacher.name == "Teacher"

    def test_update_teacher_profile(self, client, db):
        """Test updating teacher profile."""
        response = client.post(
            "/api/v1/settings/teacher-profile", data={"name": "Ms. Smith"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ms. Smith"

        # Verify in database
        teacher = db.query(Teacher).filter(Teacher.id == 1).first()
        assert teacher.name == "Ms. Smith"

    def test_update_teacher_profile_multiple_times(self, client, db):
        """Test updating teacher profile multiple times."""
        # First update
        response1 = client.post(
            "/api/v1/settings/teacher-profile", data={"name": "Mr. Johnson"}
        )
        assert response1.status_code == 200
        assert response1.json()["name"] == "Mr. Johnson"

        # Second update
        response2 = client.post(
            "/api/v1/settings/teacher-profile", data={"name": "Dr. Lee"}
        )
        assert response2.status_code == 200
        assert response2.json()["name"] == "Dr. Lee"

        # Verify final state in database
        teacher = db.query(Teacher).filter(Teacher.id == 1).first()
        assert teacher.name == "Dr. Lee"


class TestAIConfigAPI:
    """Test cases for AI configuration endpoints."""

    def test_get_ai_config_default(self, client, db):
        """Test getting default AI configuration."""
        response = client.get("/api/v1/settings/ai-config")
        assert response.status_code == 200
        data = response.json()
        assert data["default_provider"] == "openai"
        assert data["default_model"] == "gpt-4o"
        assert data["is_configured"] == False

        # Verify in database
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config is not None
        assert config.default_provider == "openai"

    def test_update_ai_config_provider(self, client, db):
        """Test updating AI provider configuration."""
        response = client.post(
            "/api/v1/settings/ai-config",
            json={
                "default_provider": "anthropic",
                "default_model": "claude-3-5-sonnet-20241022",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["default_provider"] == "anthropic"
        assert data["default_model"] == "claude-3-5-sonnet-20241022"

        # Verify in database
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config.default_provider == "anthropic"
        assert config.default_model == "claude-3-5-sonnet-20241022"

    def test_update_ai_config_with_api_key(self, client, db):
        """Test updating AI config with API key."""
        response = client.post(
            "/api/v1/settings/ai-config",
            json={
                "default_provider": "openai",
                "default_model": "gpt-4o",
                "api_keys": {"openai": "sk-test-key-12345"},
            },
        )
        assert response.status_code == 200

        # Verify in database - API key should be encrypted
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config.openai_api_key is not None
        assert config.is_configured == True

    def test_update_ai_config_copilot(self, client, db):
        """Test updating AI config with Copilot settings."""
        response = client.post(
            "/api/v1/settings/ai-config",
            json={
                "default_provider": "copilot",
                "default_model": "gpt-5-mini",
                "copilot_base_url": "http://localhost:1287",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["copilot_base_url"] == "http://localhost:1287"

        # Verify in database
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config.copilot_base_url == "http://localhost:1287"

    def test_update_ai_config_search_engine(self, client, db):
        """Test updating search engine configuration."""
        response = client.post(
            "/api/v1/settings/ai-config", json={"search_engine": "google"}
        )
        assert response.status_code == 200

        # Verify in database
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config.search_engine == "google"

    def test_ai_config_multiple_updates(self, client, db):
        """Test multiple sequential updates to AI config."""
        # First update
        response1 = client.post(
            "/api/v1/settings/ai-config", json={"default_provider": "google"}
        )
        assert response1.status_code == 200

        # Second update
        response2 = client.post(
            "/api/v1/settings/ai-config", json={"default_model": "gemini-1.5-pro"}
        )
        assert response2.status_code == 200

        # Verify final state in database
        config = (
            db.query(AIConfigModel)
            .filter(AIConfigModel.id == "default-ai-config-001")
            .first()
        )
        assert config.default_provider == "google"
        assert config.default_model == "gemini-1.5-pro"


class TestTemplatesAPI:
    """Test cases for grading templates endpoints."""

    def test_list_templates_empty(self, client, db):
        """Test listing templates when none exist."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_template(self, client, db):
        """Test creating a template."""
        response = client.post(
            "/api/v1/templates",
            json={
                "name": "English Essay",
                "description": "Template for grading English essays",
                "instructions": "Grade based on structure, content, and grammar",
                "question_types": ["essay", "reading"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "English Essay"
        template_id = data["id"]

        # Verify in database
        template = (
            db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
        )
        assert template is not None
        assert template.name == "English Essay"
        assert template.description == "Template for grading English essays"

    def test_list_templates_after_creation(self, client, db):
        """Test listing templates after creation."""
        # Create a template
        create_response = client.post(
            "/api/v1/templates",
            json={
                "name": "Vocabulary Test",
                "description": "Template for vocabulary tests",
                "instructions": "Test students on vocabulary",
                "question_types": ["mcq"],
            },
        )
        assert create_response.status_code == 200

        # List templates
        list_response = client.get("/api/v1/templates")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Vocabulary Test"

    def test_get_template_by_id(self, client, db):
        """Test getting a template by ID."""
        # Create a template
        create_response = client.post(
            "/api/v1/templates",
            json={
                "name": "Grammar Test",
                "description": "Test grammar knowledge",
                "instructions": "Grade based on grammar rules",
                "question_types": ["qa"],
            },
        )
        template_id = create_response.json()["id"]

        # Get the template
        get_response = client.get(f"/api/v1/templates/{template_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == template_id
        assert data["name"] == "Grammar Test"

    def test_update_template(self, client, db):
        """Test updating a template."""
        # Create a template
        create_response = client.post(
            "/api/v1/templates",
            json={
                "name": "Listening Test",
                "description": "Original description",
                "instructions": "Listen and answer",
                "question_types": ["fill_blank"],
            },
        )
        template_id = create_response.json()["id"]

        # Update the template
        update_response = client.put(
            f"/api/v1/templates/{template_id}",
            json={
                "name": "Advanced Listening Test",
                "description": "Updated description",
            },
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Advanced Listening Test"
        assert data["description"] == "Updated description"

        # Verify in database
        template = (
            db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
        )
        assert template.name == "Advanced Listening Test"
        assert template.description == "Updated description"

    def test_delete_template(self, client, db):
        """Test deleting a template."""
        # Create a template
        create_response = client.post(
            "/api/v1/templates",
            json={
                "name": "Speaking Test",
                "description": "Speaking assessment",
                "instructions": "Evaluate pronunciation and fluency",
                "question_types": ["picture"],
            },
        )
        template_id = create_response.json()["id"]

        # Delete the template
        delete_response = client.delete(f"/api/v1/templates/{template_id}")
        assert delete_response.status_code == 200

        # Verify deleted from database
        template = (
            db.query(GradingTemplate).filter(GradingTemplate.id == template_id).first()
        )
        assert template is None


class TestHealthCheck:
    """Test cases for health check endpoints."""

    def test_health_endpoint(self, client):
        """Test health check endpoint returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "startup_time" in data
        assert "timestamp" in data

    def test_root_endpoint(self, client):
        """Test root endpoint returns application info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data
        assert "name" in data
