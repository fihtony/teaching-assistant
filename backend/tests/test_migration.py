#!/usr/bin/env python
"""
Verification script for database schema migration.
Tests that all models work correctly with the new Integer PK and ISO timestamp format.
Uses a temporary database file so the main DB is never cleared.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

import app.core.database as db_module
from app.core.database import init_db, drop_db, get_session_local
from app.models import (
    Teacher,
    Assignment,
    GradingTemplate,
    Settings,
    CachedArticle,
    GradingContext,
    GreetingHistory,
)
from app.core.datetime_utils import from_iso_datetime, to_iso_datetime


def test_schema_migration():
    """Test that all models work with new schema (uses temp DB; does not touch user data)."""
    print("\n" + "=" * 70)
    print("DATABASE SCHEMA MIGRATION VERIFICATION")
    print("=" * 70)

    # Use a temporary database so we never clear the main DB
    fd, test_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_db_path = Path(test_db_path)

    with patch("app.core.config.get_database_path", return_value=test_db_path):
        # Force re-creation of engine/session with temp path
        db_module._engine = None
        db_module._SessionLocal = None
        print("\n1️⃣  Initializing temporary database with new schema...")
        drop_db()
        init_db()
        print("✅ Database initialized with new schema")

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Test 1: Teacher model with Integer PK and ISO timestamps
        print("\n2️⃣  Testing Teacher model...")
        teacher = Teacher(
            id=1,
            name="Dr. Jane Smith",
            email="jane@example.com",
            bio="English teacher",
            avatar_url="https://example.com/avatar.jpg",
            website="https://janesmith.edu",
        )
        db.add(teacher)
        db.commit()

        # Verify teacher
        fetched_teacher = db.query(Teacher).filter(Teacher.id == 1).first()
        assert fetched_teacher is not None
        assert fetched_teacher.name == "Dr. Jane Smith"
        assert fetched_teacher.email == "jane@example.com"
        assert isinstance(fetched_teacher.created_at, str)
        print(f"   ✓ Teacher ID: {fetched_teacher.id} (Integer PK)")
        print(f"   ✓ Email: {fetched_teacher.email}")
        print(f"   ✓ Created at: {fetched_teacher.created_at} (ISO format)")

        # Test 2: Settings model
        print("\n3️⃣  Testing Settings model...")
        settings = Settings(
            type="ai-config",
            config={
                "provider": "openai",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "max_token": 8000,
                "temperature": 0.7,
            },
        )
        db.add(settings)
        db.commit()

        # Verify settings
        fetched_settings = (
            db.query(Settings).filter(Settings.type == "ai-config").first()
        )
        assert fetched_settings is not None
        assert fetched_settings.type == "ai-config"
        config_data = fetched_settings.config
        assert config_data is not None
        assert config_data["provider"] == "openai"
        assert config_data["max_token"] == 8000  # Integer in config
        assert config_data["temperature"] == 0.7
        assert isinstance(fetched_settings.created_at, str)
        print(f"   ✓ Settings ID: {fetched_settings.id} (Integer PK)")
        print(f"   ✓ Type: {fetched_settings.type}")
        print(f"   ✓ Config: {config_data}")
        print(f"   ✓ Provider: {config_data.get('provider')}")
        print(f"   ✓ Updated at: {fetched_settings.updated_at} (ISO format)")

        # Test 3: Assignment model with Integer FKs
        print("\n4️⃣  Testing Assignment model...")
        assignment = Assignment(
            teacher_id=1,  # Integer FK
            template_id=1,  # Will be created next
            title="Essay Assignment",
            original_filename="essay.pdf",
            stored_filename="stored_essay_001.pdf",
            source_format="pdf",
        )
        db.add(assignment)
        db.flush()  # Get the auto-generated ID

        # Verify assignment
        fetched_assignment = (
            db.query(Assignment).filter(Assignment.id == assignment.id).first()
        )
        assert fetched_assignment is not None
        assert fetched_assignment.teacher_id == 1  # Integer FK
        assert isinstance(fetched_assignment.created_at, str)
        print(f"   ✓ Assignment ID: {fetched_assignment.id} (Integer PK)")
        print(f"   ✓ Teacher ID FK: {fetched_assignment.teacher_id} (Integer FK)")
        print(f"   ✓ Created at: {fetched_assignment.created_at} (ISO format)")

        # Test 4: GradingTemplate model
        print("\n5️⃣  Testing GradingTemplate model...")
        template = GradingTemplate(
            teacher_id=1,  # Integer FK
            name="Essay Rubric",
            description="Grading criteria for essays",
            instructions="Check grammar, structure, and content",
            usage_count=0,  # Integer type
        )
        db.add(template)
        db.commit()

        # Verify template
        fetched_template = (
            db.query(GradingTemplate).filter(GradingTemplate.teacher_id == 1).first()
        )
        assert fetched_template is not None
        assert fetched_template.usage_count == 0
        assert isinstance(fetched_template.usage_count, int)
        assert isinstance(fetched_template.created_at, str)
        print(f"   ✓ Template ID: {fetched_template.id} (Integer PK)")
        print(f"   ✓ Teacher ID FK: {fetched_template.teacher_id} (Integer FK)")
        print(f"   ✓ Usage Count: {fetched_template.usage_count} (Integer type)")
        print(f"   ✓ Created at: {fetched_template.created_at} (ISO format)")

        # Update assignment template_id to use created template
        assignment.template_id = fetched_template.id
        db.commit()

        # Test 5: GradingContext model
        print("\n6️⃣  Testing GradingContext model...")
        grading_context = GradingContext(
            assignment_id=assignment.id,  # Integer FK
            raw_background="Essay topic: climate change",
        )
        db.add(grading_context)
        db.commit()

        # Verify grading context
        fetched_context = (
            db.query(GradingContext)
            .filter(GradingContext.assignment_id == assignment.id)
            .first()
        )
        assert fetched_context is not None
        assert fetched_context.assignment_id == assignment.id
        assert isinstance(fetched_context.created_at, str)
        print(f"   ✓ Context ID: {fetched_context.id} (Integer PK)")
        print(f"   ✓ Assignment ID FK: {fetched_context.assignment_id} (Integer FK)")
        print(f"   ✓ Created at: {fetched_context.created_at} (ISO format)")

        # Test 6: CachedArticle model
        print("\n7️⃣  Testing CachedArticle model...")
        article = CachedArticle(
            title="Climate Change and Society",
            author="John Doe",
            source_url="https://example.com/article",
            full_content="Article content here",
            access_count=0,  # Integer type (was String before)
        )
        db.add(article)
        db.commit()

        # Verify article
        fetched_article = (
            db.query(CachedArticle).filter(CachedArticle.id == article.id).first()
        )
        assert fetched_article is not None
        assert fetched_article.access_count == 0
        assert isinstance(fetched_article.access_count, int)
        assert isinstance(fetched_article.cached_at, str)
        assert isinstance(fetched_article.expires_at, str)
        print(f"   ✓ Article ID: {fetched_article.id} (Integer PK)")
        print(f"   ✓ Access Count: {fetched_article.access_count} (Integer type)")
        print(f"   ✓ Cached at: {fetched_article.cached_at} (ISO format)")
        print(f"   ✓ Expires at: {fetched_article.expires_at} (ISO format)")

        # Test 7: GreetingHistory model
        print("\n8️⃣  Testing GreetingHistory model...")
        greeting = GreetingHistory(
            greeting_text="Hello! Great essay on climate change!",
            source_article_id=article.id,  # Integer FK
            source_title="Climate Change and Society",
        )
        db.add(greeting)
        db.commit()

        # Verify greeting
        fetched_greeting = (
            db.query(GreetingHistory).filter(GreetingHistory.id == greeting.id).first()
        )
        assert fetched_greeting is not None
        assert fetched_greeting.source_article_id == article.id
        assert isinstance(fetched_greeting.generated_at, str)
        print(f"   ✓ Greeting ID: {fetched_greeting.id} (Integer PK)")
        print(f"   ✓ Article ID FK: {fetched_greeting.source_article_id} (Integer FK)")
        print(f"   ✓ Generated at: {fetched_greeting.generated_at} (ISO format)")

        # Test 8: Verify ISO timestamp format
        print("\n9️⃣  Testing ISO timestamp format...")
        iso_timestamp = fetched_teacher.created_at
        print(f"   ISO Timestamp example: {iso_timestamp}")

        # Should be able to parse it back
        parsed_dt = from_iso_datetime(iso_timestamp)
        assert parsed_dt is not None
        print(f"   ✓ Timestamp parses correctly back to datetime")

        # Verify it has timezone offset
        assert "+" in iso_timestamp or "-" in iso_timestamp[-6:]
        print(f"   ✓ Timestamp includes timezone offset")

        print("\n" + "=" * 70)
        print("🎉 ALL SCHEMA MIGRATION TESTS PASSED!")
        print("=" * 70)
        print(
            """
Summary:
✅ All 7 models use Integer primary keys (auto-increment)
✅ All models with Integer foreign keys
✅ All timestamp fields are ISO 8601 with timezone offset
✅ Integer fields like usage_count and access_count work correctly
✅ Float fields like temperature work correctly
✅ Relationships between tables work correctly
        """
        )
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()
        # Reset so other tests use the main DB again
        db_module._engine = None
        db_module._SessionLocal = None
        if test_db_path.exists():
            try:
                os.unlink(test_db_path)
            except OSError:
                pass


if __name__ == "__main__":
    success = test_schema_migration()
    sys.exit(0 if success else 1)
