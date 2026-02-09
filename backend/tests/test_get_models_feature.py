#!/usr/bin/env python
"""Test script to verify the Get Models feature works correctly."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.database import init_db, drop_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Clean database before each test."""
    drop_db()
    init_db()
    yield
    drop_db()


def test_get_models_openai():
    """Test fetching OpenAI models."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "openai", "base_url": "https://api.openai.com/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0
    print(f"OpenAI models: {data['models']}")


def test_get_models_anthropic():
    """Test fetching Anthropic models."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={"provider": "anthropic", "base_url": "https://api.anthropic.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0
    print(f"Anthropic models: {data['models']}")


def test_get_models_google():
    """Test fetching Google models."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/settings/get-models",
        json={
            "provider": "google",
            "base_url": "https://generativelanguage.googleapis.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["models"], list)
    assert len(data["models"]) > 0
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
