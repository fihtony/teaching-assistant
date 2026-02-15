"""
Database configuration and session management.

Database is automatically initialized on first startup if needed.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import get_database_path

# Create SQLAlchemy base class for models
Base = declarative_base()

# Database engine (initialized on first use)
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


def create_tables_and_seed():
    """
    Create all tables and seed initial data. For use by the init-db script only.
    Must be run manually once before first application run. Do not call on app startup.
    """
    # Import all models so they are registered with Base
    from app.models import (
        teacher,
        assignment,
        template,
        settings,
        cached_article,
        grading_context,
        ai_grading,
        group,
        student,
    )
    from app.core.seed_templates import seed_templates_from_instructions

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    seed_templates_from_instructions(engine)


# Alias for init-db script and tests (run manually; do not call on app startup)
init_db = create_tables_and_seed


def drop_db():
    """Drop all tables. For testing only."""
    Base.metadata.drop_all(bind=get_engine())


def init_db_if_needed():
    """
    Initialize database on startup if it doesn't exist.

    If database file exists, does nothing and returns immediately.
    If database doesn't exist, creates tables and seeds initial data.

    This is called automatically on application startup.
    """
    db_path = get_database_path()

    # Check if database file exists
    if db_path.exists():
        return  # Database already exists, nothing to do

    # Database doesn't exist, initialize it
    create_tables_and_seed()
