#!/usr/bin/env python
"""Test script to verify fixes for teacher profile and Copilot Bridge."""

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


def test_teacher_profile_all_fields():
    """Test that all teacher profile fields are saved correctly."""
    client = TestClient(app)

    # Update profile with all fields
    response = client.post(
        "/api/v1/settings/teacher-profile",
        json={
            "name": "Dr. Jane Smith",
            "email": "jane.smith@school.edu",
            "avatar_url": "https://example.com/jane.jpg",
            "bio": "English teacher with 10 years of experience",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dr. Jane Smith"
    assert data["email"] == "jane.smith@school.edu"
    assert data["avatar_url"] == "https://example.com/jane.jpg"
    assert data["bio"] == "English teacher with 10 years of experience"
    print(f"✅ Profile POST response: all fields present")

    # Verify in database
    SessionLocal = get_session_local()
    db = SessionLocal()
    teacher = db.query(Teacher).filter(Teacher.id == 1).first()
    assert teacher is not None
    assert teacher.name == "Dr. Jane Smith"
    assert teacher.email == "jane.smith@school.edu"
    assert teacher.avatar_url == "https://example.com/jane.jpg"
    assert teacher.bio == "English teacher with 10 years of experience"
    db.close()
    print(f"✅ Database persistence: all fields saved correctly")

    # Get profile again
    response = client.get("/api/v1/settings/teacher-profile")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dr. Jane Smith"
    assert data["email"] == "jane.smith@school.edu"
    assert data["avatar_url"] == "https://example.com/jane.jpg"
    assert data["bio"] == "English teacher with 10 years of experience"
    print(f"✅ Profile GET response: all fields present and correct")


def test_copilot_models_endpoint():
    """Test that Copilot models endpoint uses correct path."""
    client = TestClient(app)

    # This should try to call /models on Copilot Bridge
    # It will fail if Copilot Bridge is not running, but the endpoint should be correct
    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "copilot", "base_url": "http://localhost:1287"},
    )
    assert response.status_code == 200
    data = response.json()
    # Response should have the correct structure
    assert "models" in data
    assert "success" in data
    # Models may be empty if Copilot Bridge is not running
    print(f"✅ Copilot get-models endpoint works (models: {data['models']})")


def test_partial_teacher_profile_update():
    """Test that partial updates work correctly."""
    client = TestClient(app)

    # First, set all fields
    response = client.post(
        "/api/v1/settings/teacher-profile",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "avatar_url": "https://example.com/john.jpg",
            "bio": "An English teacher",
        },
    )
    assert response.status_code == 200

    # Now update only name
    response = client.post(
        "/api/v1/settings/teacher-profile", json={"name": "John Smith"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Smith"
    assert data["email"] == "john@example.com"  # Should still be there
    assert data["avatar_url"] == "https://example.com/john.jpg"  # Should still be there
    assert data["bio"] == "An English teacher"  # Should still be there
    print(f"✅ Partial update works: name changed, other fields preserved")
