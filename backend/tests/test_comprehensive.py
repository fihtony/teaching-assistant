#!/usr/bin/env python
"""Comprehensive end-to-end test for all improvements."""

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


def test_complete_workflow():
    """Test complete workflow: teacher profile → AI config → Get Models → Save."""
    client = TestClient(app)

    # Step 1: Update teacher profile
    print("\n1️⃣  Updating teacher profile...")
    response = client.post(
        "/api/v1/settings/teacher-profile", json={"name": "Dr. Smith"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Dr. Smith"
    print("✅ Teacher profile saved")

    # Step 2: Update AI config with new field names
    print("\n2️⃣  Updating AI configuration...")
    response = client.post(
        "/api/v1/settings/settings",
        json={
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "base_url": "https://api.anthropic.com",
            "api_key": "sk-test-anthropic-key",
            "temperature": 0.8,
            "max_tokens": 2048,
            "search_engine": "google",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_provider"] == "anthropic"
    assert data["default_model"] == "claude-3-5-sonnet-20241022"
    assert data["temperature"] == 0.8
    assert data["max_tokens"] == 2048
    print("✅ AI configuration saved with temperature and max_tokens")

    # Step 3: Get models from provider
    print("\n3️⃣  Fetching available models...")
    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "anthropic", "base_url": "https://api.anthropic.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["models"]) > 0
    print(f"✅ Retrieved {len(data['models'])} models: {data['models']}")

    # Step 4: Verify database persistence
    print("\n4️⃣  Verifying database persistence...")
    SessionLocal = get_session_local()
    db = SessionLocal()

    # Check teacher
    teacher = db.query(Teacher).filter(Teacher.id == 1).first()
    assert teacher is not None
    assert teacher.name == "Dr. Smith"
    print("✅ Teacher profile persisted in database")

    # Check AI config
    config = db.query(Settings).filter(Settings.type == "ai-config").first()
    assert config is not None
    config_data = config.config
    assert config_data is not None
    assert config_data["provider"] == "anthropic"
    assert config_data["model"] == "claude-3-5-sonnet-20241022"
    assert config_data["temperature"] == 0.8
    assert config_data["max_token"] == 2048
    db.close()
    print("✅ AI configuration with temperature/max_token persisted in database")

    # Step 5: Check health endpoint
    print("\n5️⃣  Checking health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "startup_timestamp" in data
    assert data["status"] == "healthy"
    print(f"✅ Health endpoint returns startup_timestamp: {data['startup_timestamp']}")

    # Step 6: Get models for other providers
    print("\n6️⃣  Testing Get Models for multiple providers...")
    providers_to_test = [
        ("openai", "https://api.openai.com/v1"),
        ("google", "https://generativelanguage.googleapis.com"),
    ]

    for provider, base_url in providers_to_test:
        response = client.post(
            "/api/v1/settings/get-models",
            json={"provider": provider, "base_url": base_url},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print(f"✅ {provider.capitalize()}: {len(data['models'])} models available")

    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED - All improvements working correctly!")
    print("=" * 70)
