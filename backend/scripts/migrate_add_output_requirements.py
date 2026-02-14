"""
Database migration: Add output_requirements column to grading_contexts table.

Usage (from backend directory):
  python -m scripts.migrate_add_output_requirements

This script adds the missing output_requirements column to the grading_contexts table
if it doesn't already exist. It's safe to run multiple times.
"""

from sqlalchemy import inspect, text
from app.core.database import get_engine
from app.core.logging import get_logger

logger = get_logger()


def migrate_add_output_requirements():
    """Add output_requirements column to grading_contexts table if it doesn't exist."""
    engine = get_engine()

    # Check if column already exists
    inspector = inspect(engine)
    columns = inspector.get_columns("grading_contexts")
    column_names = [col["name"] for col in columns]

    if "output_requirements" in column_names:
        logger.info(
            "Column 'output_requirements' already exists in grading_contexts table"
        )
        return

    # Add the column
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE grading_contexts ADD COLUMN output_requirements TEXT")
        )
        conn.commit()
        logger.info(
            "Successfully added 'output_requirements' column to grading_contexts table"
        )


def main():
    logger.info("Starting database migration: add output_requirements column...")
    try:
        migrate_add_output_requirements()
        logger.info("Migration complete!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
