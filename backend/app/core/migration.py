"""
Database migration script to handle schema changes from old UUID-based schema to new Integer-based schema.
"""

import os
import sqlite3
from pathlib import Path
from app.core.config import get_database_path
from app.core.logging import get_logger

logger = get_logger()


def backup_database():
    """Create a backup of the current database."""
    db_path = get_database_path()
    backup_path = db_path.replace(".db", "_backup.db")

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()
            logger.info(f"Database backup created at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return None
    return None


def migrate_database():
    """
    Migrate database from old UUID-based schema to new Integer-based schema.
    This is a fresh database reset - we don't preserve old data.
    """
    db_path = get_database_path()

    logger.info("Starting database migration...")

    try:
        # Backup existing database
        backup_database()

        # Drop existing database if it exists
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Dropped old database at {db_path}")

        # The new tables will be created by init_db() with proper schema
        logger.info("Migration complete - database reset ready for new schema")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def run_migration():
    """Run the migration."""
    return migrate_database()
