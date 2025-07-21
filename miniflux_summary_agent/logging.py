"""Logging configuration for the application."""

import logging

from .config import get_log_format, get_log_level


def setup_logging() -> logging.Logger:
    """Configure logging based on environment variables."""
    log_level = get_log_level()
    log_format = get_log_format()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler()],
    )

    # Set httpx logger to WARNING to suppress INFO level HTTP request logs
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logging.getLogger(__name__)
