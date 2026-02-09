#!/usr/bin/env python
"""Test script to verify search engine configuration is stored separately."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.database import get_session_local, get_engine, Base, init_db, drop_db
from app.models import Settings


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Initialize database for tests. Clean up test data after each test."""
    # Ensure tables exist (won't drop existing data)
    Base.metadata.create_all(bind=get_engine())

    # Record initial state
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
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
        # Delete ai-config if it didn't exist before (don't touch if it existed)
        if not initial_ai_config:
            db.query(Settings).filter(Settings.type == "ai-config").delete()

        # Delete search config if it didn't exist before (don't touch if it existed)
        if not initial_search_config:
            db.query(Settings).filter(Settings.type == "search").delete()

        db.commit()
    finally:
        db.close()


def test_search_engine_stored_separately():
    """Verify that search engine config is stored in a separate record with type=search."""
    client = TestClient(app)

    # Get initial search engine config
    response = client.get("/api/v1/settings/search-engine")
    assert response.status_code == 200
    initial_data = response.json()
    assert "engine" in initial_data
    print(f"✓ Initial search engine: {initial_data['engine']}")

    # Update search engine to google
    response = client.post("/api/v1/settings/search-engine", json={"engine": "google"})
    assert response.status_code == 200
    result = response.json()
    assert result["engine"] == "google"
    print(f"✓ Updated search engine to: {result['engine']}")

    # Verify it persists in database
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        search_config = db.query(Settings).filter(Settings.type == "search").first()
        assert search_config is not None, "Search config not found in database"
        assert (
            search_config.config["engine"] == "google"
        ), "Search engine not saved correctly"
        print(
            f"✓ Verified in database: type='{search_config.type}', engine='{search_config.config['engine']}'"
        )
    finally:
        db.close()


def test_search_engine_separate_from_ai_config():
    """Verify that search engine config doesn't affect ai-config record and vice versa."""
    client = TestClient(app)

    # Get initial AI config
    response = client.get("/api/v1/settings/settings")
    assert response.status_code == 200
    initial_ai_config = response.json()
    initial_provider = initial_ai_config["default_provider"]
    print(f"✓ Initial AI provider: {initial_provider}")

    # Update search engine
    response = client.post("/api/v1/settings/search-engine", json={"engine": "google"})
    assert response.status_code == 200
    print("✓ Updated search engine")

    # Verify AI config is unchanged
    response = client.get("/api/v1/settings/settings")
    assert response.status_code == 200
    updated_ai_config = response.json()
    assert updated_ai_config["default_provider"] == initial_provider
    assert updated_ai_config["search_engine"] == "google"
    print(f"✓ AI config unchanged (provider={updated_ai_config['default_provider']})")
    print(f"✓ Search engine in AI response: {updated_ai_config['search_engine']}")

    # Verify in database - two separate records
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        ai_config = db.query(Settings).filter(Settings.type == "ai-config").first()
        search_config = db.query(Settings).filter(Settings.type == "search").first()

        assert ai_config is not None, "AI config not found"
        assert search_config is not None, "Search config not found"

        # AI config should NOT have search_engine
        assert (
            "search_engine" not in ai_config.config
            or ai_config.config.get("search_engine") is None
        )
        print(f"✓ AI config record (type='ai-config'): {ai_config.config.keys()}")

        # Search config should have engine
        assert search_config.config.get("engine") == "google"
        print(f"✓ Search config record (type='search'): {search_config.config}")
    finally:
        db.close()


def test_update_ai_config_no_search_engine():
    """Verify that updating AI config doesn't overwrite search engine setting."""
    client = TestClient(app)

    # Set search engine to google
    response = client.post("/api/v1/settings/search-engine", json={"engine": "google"})
    assert response.status_code == 200
    print("✓ Set search engine to google")

    # Update AI config (provider change)
    response = client.post("/api/v1/settings/settings", json={"provider": "anthropic"})
    assert response.status_code == 200
    updated_ai = response.json()
    assert updated_ai["default_provider"] == "anthropic"
    assert updated_ai["search_engine"] == "google"
    print(f"✓ Updated AI provider, search engine still: {updated_ai['search_engine']}")

    # Verify database records
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        ai_config = db.query(Settings).filter(Settings.type == "ai-config").first()
        search_config = db.query(Settings).filter(Settings.type == "search").first()

        assert ai_config.config["provider"] == "anthropic"
        assert search_config.config["engine"] == "google"
        print(
            f"✓ Database verified: AI provider='{ai_config.config['provider']}', search engine='{search_config.config['engine']}'"
        )
    finally:
        db.close()


def test_invalid_search_engine():
    """Verify that invalid search engines are rejected."""
    client = TestClient(app)

    # Try to set invalid search engine
    response = client.post(
        "/api/v1/settings/search-engine", json={"engine": "invalid_engine"}
    )
    assert response.status_code == 400
    error_data = response.json()
    assert "engine must be" in error_data.get("detail", "").lower()
    print(f"✓ Invalid engine rejected: {error_data['detail']}")


def test_search_engine_missing_engine_field():
    """Verify that missing 'engine' field is rejected."""
    client = TestClient(app)

    # Try to post without engine field
    response = client.post(
        "/api/v1/settings/search-engine", json={"some_other_field": "value"}
    )
    assert response.status_code == 400
    error_data = response.json()
    assert "engine" in error_data.get("detail", "").lower()
    print(f"✓ Missing engine field rejected: {error_data['detail']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
