"""
Core configuration module for the English Teaching Assignment Grading System.
Loads configuration from YAML file and environment variables.
"""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8090
    debug: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "data/teaching.db"


class StorageConfig(BaseModel):
    """File storage configuration."""

    uploads_dir: str = "data/uploads"
    graded_dir: str = "data/graded"
    templates_dir: str = "data/templates"
    cache_dir: str = "data/cache"


class LoggingConfig(BaseModel):
    """Logging configuration."""

    file: str = "app.log"
    level: str = os.getenv("LOG_LEVEL", "DEBUG")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_size: int = 10  # MB
    backup_count: int = 5


class AppConfig(BaseModel):
    """Main application configuration.

    AI, search, cache, greeting, OCR are in Settings table (see app.core.settings_db).
    """

    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig = StorageConfig()
    logging: LoggingConfig = LoggingConfig()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file. If None, uses default location.

    Returns:
        AppConfig instance with loaded configuration.
    """
    if config_path is None:
        config_path = os.environ.get("TEACHING_CONFIG")
        if config_path is None:
            config_path = get_project_root() / "config.yaml"

    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            return AppConfig(**config_data)

    return AppConfig()


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_backend_dir() -> Path:
    """Get the backend directory path."""
    return Path(__file__).parent.parent.parent


def get_storage_path(storage_type: str) -> Path:
    """
    Get the absolute path for a storage directory under project root data/.

    All persistent data (uploads, graded output, templates, cache) live under
    project_root/data/ so they are not under backend/ and survive across runs.

    Args:
        storage_type: One of 'uploads', 'graded', 'templates', 'cache'

    Returns:
        Absolute path to the storage directory.
    """
    config = get_config()
    root = get_project_root()

    storage_map = {
        "uploads": config.storage.uploads_dir,
        "graded": config.storage.graded_dir,
        "templates": config.storage.templates_dir,
        "cache": config.storage.cache_dir,
    }

    relative_path = storage_map.get(storage_type, config.storage.uploads_dir)
    absolute_path = (root / relative_path).resolve()
    absolute_path.mkdir(parents=True, exist_ok=True)

    return absolute_path


def get_database_path() -> Path:
    """Get the absolute path to the database file.
    Used by: app.core.database (engine), app.core.migration.
    Default value: config.yaml 'database.path' or DatabaseConfig.path in config.py ('data/teaching.db').
    """
    config = get_config()
    root = get_project_root()
    db_path = (root / config.database.path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_log_path() -> Path:
    """Get the absolute path to the log file. Always under project root logs/ folder."""
    config = get_config()
    root = get_project_root()
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    # Use only the filename from config so logs never go outside logs/
    name = Path(config.logging.file).name or "app.log"
    return log_dir / name
