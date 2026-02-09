#!/usr/bin/env python
"""Test script to verify the Get Models feature works correctly."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.database import init_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Ensure tables exist; do not clear user data."""
    init_db()
    yield
    # Get-models tests do not create any records; no teardown cleanup needed


def test_get_models_openai():
    """Test get-models for OpenAI (uses user base_url/api_key; without key may return empty)."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "openai", "base_url": "https://api.openai.com/v1", "api_key": ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data and "models" in data and "message" in data
    assert isinstance(data["models"], list)
    # Without valid API key the list may be empty
    print(f"OpenAI models: {data['models']}")


def test_get_models_anthropic():
    """Test get-models for Anthropic (no fallback; without valid key returns error/empty)."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "anthropic", "base_url": "https://api.anthropic.com", "api_key": ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data and "models" in data and "message" in data
    assert isinstance(data["models"], list)
    # Without valid API key we get empty models and an error message (no dummy list)
    print(f"Anthropic models: {data['models']}, error: {data.get('error')}")


def test_get_models_google():
    """Test get-models for Google Gemini (without key may return empty)."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={
            "provider": "google",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data and "models" in data
    assert isinstance(data["models"], list)
    print(f"Google models: {data['models']}")


def test_get_models_copilot():
    """Test fetching Copilot models (may fail if Copilot Bridge not running)."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "copilot", "base_url": "http://localhost:1287"},
    )
    assert response.status_code == 200
    data = response.json()
    # Copilot may not be available, but response should be valid
    assert "models" in data
    print(f"Copilot models: {data['models']}")
