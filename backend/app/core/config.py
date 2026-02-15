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


def _resolve_data_dir() -> Path:
    """
    Resolve the data directory path.

    Supports two modes:
    1. Container mode: DATA_DIR environment variable is set (e.g., /app/data)
    2. Local development: Uses project root/data

    Returns:
        Absolute path to the data directory.
    """
    data_dir_env = os.environ.get("DATA_DIR")

    if data_dir_env:
        # Container mode: use the environment variable
        return Path(data_dir_env).resolve()
    else:
        # Local development: use project root/data
        return (get_project_root() / "data").resolve()


def get_storage_path(storage_type: str) -> Path:
    """
    Get the absolute path for a storage directory.

    Supports both container and local development modes:
    - Container: /app/data/{uploads|graded|templates|cache}
    - Local: project_root/data/{uploads|graded|templates|cache}

    Args:
        storage_type: One of 'uploads', 'graded', 'templates', 'cache'

    Returns:
        Absolute path to the storage directory.
    """
    config = get_config()

    storage_map = {
        "uploads": config.storage.uploads_dir,
        "graded": config.storage.graded_dir,
        "templates": config.storage.templates_dir,
        "cache": config.storage.cache_dir,
    }

    relative_path = storage_map.get(storage_type, config.storage.uploads_dir)

    # Get the base data directory
    data_dir = _resolve_data_dir()

    # Extract the subdirectory name from the config path
    # e.g., "data/uploads" -> "uploads"
    subdirs = Path(relative_path).parts[-1]  # Get the last part of the path

    absolute_path = (data_dir / subdirs).resolve()
    absolute_path.mkdir(parents=True, exist_ok=True)

    return absolute_path


def get_database_path() -> Path:
    """
    Get the absolute path to the database file.

    Supports both container and local development modes:
    - Container: /app/data/teaching.db
    - Local: project_root/data/teaching.db

    Used by: app.core.database (engine).
    Default value: config.yaml 'database.path' or DatabaseConfig.path in config.py.
    """
    config = get_config()

    # Get the base data directory
    data_dir = _resolve_data_dir()

    # Extract the filename from the config path
    # e.g., "data/teaching.db" -> "teaching.db"
    db_filename = Path(config.database.path).name

    db_path = (data_dir / db_filename).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_log_path() -> Path:
    """
    Get the absolute path to the log file.

    Supports both container and local development modes:
    - Container: /app/logs/app.log
    - Local: project_root/logs/app.log
    """
    config = get_config()

    # Check for LOGS_DIR environment variable (set by docker-compose)
    logs_dir_env = os.environ.get("LOGS_DIR")

    if logs_dir_env:
        # Container mode: use the environment variable
        log_dir = Path(logs_dir_env)
    else:
        # Local development: use project root/logs
        log_dir = get_project_root() / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Use only the filename from config so logs never go outside logs/
    name = Path(config.logging.file).name or "app.log"
    return log_dir / name
