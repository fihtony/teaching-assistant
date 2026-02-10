"""
Database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import get_database_path

# Create SQLAlchemy base class for models
Base = declarative_base()

# Database engine (will be initialized on first use)
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        db_path = get_database_path()
        database_url = f"sqlite:///{db_path}"
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False, "timeout": 30},
            echo=False,
        )
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Yields:
        Database session that will be closed after use.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_instruction_format_column(engine):
    """Add instruction_format to grading_templates if missing (e.g. after upgrade)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(grading_templates)"))
        rows = r.fetchall()
        names = [row[1] for row in rows]
        if "instruction_format" not in names:
            conn.execute(text(
                "ALTER TABLE grading_templates ADD COLUMN instruction_format VARCHAR(20) NOT NULL DEFAULT 'text'"
            ))
            conn.commit()


def _ensure_encouragement_words_column(engine):
    """Add encouragement_words to grading_templates if missing (JSON array)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(grading_templates)"))
        names = [row[1] for row in r.fetchall()]
        if "encouragement_words" not in names:
            conn.execute(text(
                "ALTER TABLE grading_templates ADD COLUMN encouragement_words TEXT DEFAULT '[]'"
            ))
            conn.commit()


def _migrate_question_types_to_objects(engine):
    """Ensure question_types rows store object array; migrate string array to object array."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from app.models import GradingTemplate

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        for t in db.query(GradingTemplate).all():
            qt = t.question_types or []
            if not qt:
                continue
            first = qt[0] if qt else None
            if isinstance(first, dict) and "type" in first:
                continue
            # Legacy: list of strings -> list of {type, name, weight, enabled}
            default_names = {
                "mcq": "Multiple Choice", "true_false": "True/False", "fill_blank": "Fill in the Blank",
                "short_answer": "Short Answer", "reading_comprehension": "Reading Comprehension",
                "picture_description": "Picture Description", "essay": "Essay",
            }
            t.question_types = [
                {"type": s, "name": default_names.get(s, s), "weight": 10, "enabled": True}
                for s in (qt if isinstance(qt, list) else [])
                if isinstance(s, str)
            ]
        db.commit()
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Should be called on application startup.
    Drops legacy ai_provider_config table if present (AI config now in Settings).
    Adds instruction_format to grading_templates if missing; seeds templates from instructions/.
    """
    from sqlalchemy import text

    # Import all models to ensure they are registered with Base
    from app.models import (
        teacher,
        assignment,
        template,
        settings,
        cached_article,
        grading_context,
        grading_history,
    )
    from app.core.seed_templates import seed_templates_from_instructions

    engine = get_engine()
    # Drop legacy table (AI config is now in Settings type=ai-config)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ai_provider_config"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    _ensure_instruction_format_column(engine)
    _ensure_encouragement_words_column(engine)
    _migrate_question_types_to_objects(engine)
    seed_templates_from_instructions(engine)


def drop_db():
    """
    Drop all database tables.
    Use with caution - only for testing purposes.
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
