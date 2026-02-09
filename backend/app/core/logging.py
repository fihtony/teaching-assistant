"""
Logging configuration for the application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.core.config import get_config, get_log_path

# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logging() -> logging.Logger:
    """
    Set up application logging with both file and console handlers.

    Returns:
        Configured logger instance.
    """
    global _logger

    if _logger is not None:
        return _logger

    config = get_config()
    log_config = config.logging

    # Create logger
    logger = logging.getLogger("teaching_app")
    logger.setLevel(getattr(logging, log_config.level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_config.format)

    # File handler with rotation
    log_path = get_log_path()
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=log_config.max_size * 1024 * 1024,  # Convert MB to bytes
        backupCount=log_config.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_config.level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_config.level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """
    Get the application logger.

    Returns:
        Logger instance.
    """
    global _logger
    if _logger is None:
        return setup_logging()
    return _logger
