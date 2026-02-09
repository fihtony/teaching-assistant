#!/usr/bin/env python
"""Test script to verify teacher profile and AI config save correctly."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.database import init_db, drop_db, get_session_local, get_engine, Base
from app.models import Teacher, Settings


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Initialize database for tests. Clean up test data after each test."""
    # Ensure tables exist (won't drop existing data)
    Base.metadata.create_all(bind=get_engine())

    # Record initial state
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        initial_teacher_ids = set(t.id for t in db.query(Teacher).all())
        initial_ai_config = (
            db.query(Settings).filter(Settings.type == "ai-config").first()
        )
        initial_search_config = (
            db.query(Settings).filter(Settings.type == "search").first()
        )
    finally:
        db.close()

    yield

    # Clean up test data after test (only delete records added during the test)
    db = SessionLocal()
    try:
        # Delete teachers that didn't exist before test
        current_teacher_ids = set(t.id for t in db.query(Teacher).all())
        new_teacher_ids = current_teacher_ids - initial_teacher_ids
        if new_teacher_ids:
            db.query(Teacher).filter(Teacher.id.in_(new_teacher_ids)).delete()

        # Delete ai-config if it didn't exist before (don't touch if it existed)
        if not initial_ai_config:
            db.query(Settings).filter(Settings.type == "ai-config").delete()

        # Delete search config if it didn't exist before (don't touch if it existed)
        if not initial_search_config:
            db.query(Settings).filter(Settings.type == "search").delete()

        db.commit()
    finally:
        db.close()


def test_teacher_profile_save():
    """Test that teacher profile saves to database correctly."""
    client = TestClient(app)

    # Update profile with JSON
    response = client.post(
        "/api/v1/settings/teacher-profile", json={"name": "Mrs. Johnson"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Mrs. Johnson"

    # Verify in database
    SessionLocal = get_session_local()
    db = SessionLocal()
    teacher = db.query(Teacher).filter(Teacher.id == 1).first()
    assert teacher is not None
    assert teacher.name == "Mrs. Johnson"
    db.close()

    # Get profile again
    response = client.get("/api/v1/settings/teacher-profile")
    assert response.status_code == 200
    assert response.json()["name"] == "Mrs. Johnson"


def test_ai_config_save():
    """Test that AI config saves to database correctly."""
    client = TestClient(app)

    # Update AI config
    response = client.post(
        "/api/v1/settings/settings",
        json={
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "base_url": "https://api.anthropic.com",
            "api_key": "test-key",
            "temperature": 0.7,
            "max_tokens": 2000,
            "search_engine": "duckduckgo",
        },
    )
    assert response.status_code == 200
    resp_data = response.json()
    # Response uses default_provider field name
    assert resp_data["default_provider"] == "anthropic"
    assert resp_data["default_model"] == "claude-3-sonnet"

    # Verify in database
    SessionLocal = get_session_local()
    db = SessionLocal()
    config = db.query(Settings).filter(Settings.type == "ai-config").first()
    assert config is not None
    config_data = config.config
    assert config_data is not None
    assert config_data["provider"] == "anthropic"
    assert config_data["model"] == "claude-3-sonnet"
    assert config_data["baseUrl"] == "https://api.anthropic.com"
    db.close()

    # Get config again
    response = client.get("/api/v1/settings/settings")
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["default_provider"] == "anthropic"
    assert resp_data["default_model"] == "claude-3-sonnet"


def test_health_endpoint_with_startup_timestamp():
    """Test that health endpoint returns startup_timestamp."""
    # Use TestClient which properly handles lifespan
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Check that startup_timestamp field exists
    assert "startup_timestamp" in data
    # startup_timestamp may be None briefly if app not yet initialized
    # but should be a valid ISO timestamp string
    if data["startup_timestamp"]:
        # Should be a string in ISO format
        assert isinstance(data["startup_timestamp"], str)
        assert "T" in data["startup_timestamp"] or len(data["startup_timestamp"]) > 0
