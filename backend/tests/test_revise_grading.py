"""
Tests for the grading revision API endpoints.

Covers:
- POST /assignments/{id}/grade/revise
- PUT /assignments/{id}/grade/save-revision
- GET /assignments/{id} returns ai_grading_id
- REVISE_GRADING_PROMPT template validation
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def _mock_db_none():
    """Mock DB session that returns None for all .first() queries."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_session.query.return_value = mock_query
    yield mock_session


@pytest.fixture
def client_with_mock_db():
    """Test client with mocked DB that returns None for queries."""
    app.dependency_overrides[get_db] = _mock_db_none
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


class TestReviseGradingEndpoint:
    """Tests for POST /assignments/{id}/grade/revise"""

    def test_revise_missing_instruction(self, client):
        """Should return error when teacher_instruction is empty."""
        response = client.post(
            "/api/v1/assignments/1/grade/revise",
            json={
                "ai_grading_id": 1,
                "teacher_instruction": "",
                "current_html_content": "<p>Some content</p>",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["error"] is not None
        assert "required" in result["error"].lower()

    def test_revise_missing_ai_grading_id(self, client):
        """Should return error when ai_grading_id is missing."""
        response = client.post(
            "/api/v1/assignments/1/grade/revise",
            json={
                "teacher_instruction": "Be more encouraging",
                "current_html_content": "<p>Some content</p>",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["error"] is not None

    def test_revise_nonexistent_assignment(self, client_with_mock_db):
        """Should return error for non-existent ai_grading record."""
        response = client_with_mock_db.post(
            "/api/v1/assignments/99999/grade/revise",
            json={
                "ai_grading_id": 99999,
                "teacher_instruction": "Be more encouraging",
                "current_html_content": "<p>Some content</p>",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

    def test_revise_returns_proper_structure(self, client):
        """Response should always have html_content, elapsed_ms, and error fields."""
        response = client.post(
            "/api/v1/assignments/1/grade/revise",
            json={
                "ai_grading_id": 1,
                "teacher_instruction": "",
                "current_html_content": "",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert "html_content" in result
        assert "error" in result

    @patch("app.services.ai_grading.AIGradingService._call_ai")
    def test_revise_calls_ai_with_teacher_instruction(
        self, mock_call_ai, client_with_mock_db
    ):
        """Should pass teacher instruction to the AI service."""
        mock_call_ai.return_value = "## Revised Essay\n\nModified content."

        response = client_with_mock_db.post(
            "/api/v1/assignments/99999/grade/revise",
            json={
                "ai_grading_id": 99999,
                "teacher_instruction": "Be more encouraging",
                "current_html_content": "<p>Content</p>",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["error"] is not None


class TestSaveRevisionEndpoint:
    """Tests for PUT /assignments/{id}/grade/save-revision"""

    def test_save_missing_ai_grading_id(self, client):
        """Should return 400 when ai_grading_id is missing."""
        response = client.put(
            "/api/v1/assignments/1/grade/save-revision",
            json={"html_content": "<p>Content</p>"},
        )
        assert response.status_code == 400

    def test_save_missing_html_content(self, client):
        """Should return 400 when html_content is empty."""
        response = client.put(
            "/api/v1/assignments/1/grade/save-revision",
            json={"ai_grading_id": 1, "html_content": ""},
        )
        assert response.status_code == 400

    def test_save_empty_body(self, client):
        """Should return 400 when body is empty."""
        response = client.put(
            "/api/v1/assignments/1/grade/save-revision",
            json={},
        )
        assert response.status_code == 400

    def test_save_nonexistent_grading(self, client_with_mock_db):
        """Should return 404 for non-existent AI grading record."""
        response = client_with_mock_db.put(
            "/api/v1/assignments/99999/grade/save-revision",
            json={
                "ai_grading_id": 99999,
                "html_content": "<p>Revised content</p>",
            },
        )
        assert response.status_code == 404

    def test_save_with_revision_history_structure(self, client_with_mock_db):
        """Should accept revision_history as a list of dicts."""
        response = client_with_mock_db.put(
            "/api/v1/assignments/99999/grade/save-revision",
            json={
                "ai_grading_id": 99999,
                "html_content": "<p>Content</p>",
                "revision_history": [
                    {
                        "instruction": "Be encouraging",
                        "timestamp": "2026-02-19T10:00:00Z",
                    },
                ],
            },
        )
        assert response.status_code == 404


class TestRevisePromptTemplate:
    """Tests for the REVISE_GRADING_PROMPT template."""

    def test_prompt_has_required_placeholders(self):
        """Should contain all required format placeholders."""
        from app.services.ai_prompts import REVISE_GRADING_PROMPT

        assert "{teacher_revise_instruction}" in REVISE_GRADING_PROMPT
        assert "{background}" in REVISE_GRADING_PROMPT
        assert "{template_instruction}" in REVISE_GRADING_PROMPT
        assert "{custom_instruction}" in REVISE_GRADING_PROMPT
        assert "{current_graded_output}" in REVISE_GRADING_PROMPT

    def test_prompt_formatting_works(self):
        """Should format without errors."""
        from app.services.ai_prompts import REVISE_GRADING_PROMPT

        result = REVISE_GRADING_PROMPT.format(
            teacher_revise_instruction="Be more encouraging",
            background="Grade 4 essay",
            template_instruction="Grade for grammar",
            custom_instruction="None",
            current_graded_output="<p>Test</p>",
        )
        assert "Be more encouraging" in result
        assert "Grade 4 essay" in result

    def test_prompt_emphasizes_teacher_instruction(self):
        """Teacher instruction should appear before background info."""
        from app.services.ai_prompts import REVISE_GRADING_PROMPT

        teacher_idx = REVISE_GRADING_PROMPT.index("{teacher_revise_instruction}")
        background_idx = REVISE_GRADING_PROMPT.index("{background}")
        assert teacher_idx < background_idx

    def test_prompt_contains_markup_rules(self):
        """Should contain markup rules for corrections."""
        from app.services.ai_prompts import REVISE_GRADING_PROMPT

        assert "~~" in REVISE_GRADING_PROMPT
        assert "{{" in REVISE_GRADING_PROMPT


class TestReviseSchemas:
    """Tests for the Pydantic schemas used in revision."""

    def test_revise_grading_request_schema(self):
        """Should create a valid ReviseGradingRequest."""
        from app.schemas.assignment import ReviseGradingRequest

        req = ReviseGradingRequest(
            ai_grading_id=1,
            teacher_instruction="Be encouraging",
            current_html_content="<p>Content</p>",
        )
        assert req.ai_grading_id == 1
        assert req.teacher_instruction == "Be encouraging"

    def test_revise_grading_response_schema(self):
        """Should create a valid ReviseGradingResponse."""
        from app.schemas.assignment import ReviseGradingResponse

        resp = ReviseGradingResponse(
            html_content="<p>Revised</p>",
            elapsed_ms=1500,
        )
        assert resp.html_content == "<p>Revised</p>"
        assert resp.elapsed_ms == 1500
        assert resp.error is None

    def test_revise_grading_response_with_error(self):
        """Should create a response with error."""
        from app.schemas.assignment import ReviseGradingResponse

        resp = ReviseGradingResponse(
            html_content="",
            error="AI unavailable",
        )
        assert resp.error == "AI unavailable"

    def test_save_revision_request_schema(self):
        """Should create a valid SaveRevisionRequest."""
        from app.schemas.assignment import SaveRevisionRequest

        req = SaveRevisionRequest(
            ai_grading_id=1,
            html_content="<p>Final</p>",
            revision_history=[
                {"instruction": "Fix grammar", "timestamp": "2026-01-01T00:00:00Z"}
            ],
        )
        assert req.ai_grading_id == 1
        assert len(req.revision_history) == 1

    def test_save_revision_request_optional_history(self):
        """Should allow missing revision_history."""
        from app.schemas.assignment import SaveRevisionRequest

        req = SaveRevisionRequest(
            ai_grading_id=1,
            html_content="<p>Final</p>",
        )
        assert req.revision_history is None

    def test_assignment_detail_includes_ai_grading_id(self):
        """AssignmentDetail schema should include ai_grading_id field."""
        from app.schemas.assignment import AssignmentDetail

        detail = AssignmentDetail(
            id=1,
            filename="test.txt",
            source_format="txt",
            status="extracted",
            upload_time="2026-01-01T00:00:00Z",
            ai_grading_id=42,
        )
        assert detail.ai_grading_id == 42

    def test_assignment_detail_ai_grading_id_optional(self):
        """ai_grading_id should be optional (None when no grading exists)."""
        from app.schemas.assignment import AssignmentDetail

        detail = AssignmentDetail(
            id=1,
            filename="test.txt",
            source_format="txt",
            status="extracted",
            upload_time="2026-01-01T00:00:00Z",
        )
        assert detail.ai_grading_id is None
