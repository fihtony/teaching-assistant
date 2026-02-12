"""
Initialize database: create all tables and seed templates. Run once manually before first app launch.

Usage (from backend directory):
  python -m scripts.init_db

Do not run this on application startup. The application does not create or migrate the database.
"""

from app.core.database import create_tables_and_seed
from app.core.logging import get_logger

logger = get_logger()


def main():
    logger.info("Initializing database (create tables and seed)...")
    create_tables_and_seed()
    logger.info("Database initialization complete. Run the application with: python -m uvicorn main:app --host 0.0.0.0 --port 8090")


if __name__ == "__main__":
    main()
