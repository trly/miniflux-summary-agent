"""Configuration management for the application."""

import os

from dotenv import load_dotenv


def load_config():
    """Load environment variables from .env file."""
    load_dotenv()


def get_miniflux_url() -> str:
    """Get Miniflux URL from environment."""
    return os.getenv("MINIFLUX_URL", "")


def get_miniflux_api_key() -> str:
    """Get Miniflux API key from environment."""
    return os.getenv("MINIFLUX_API_KEY", "")


def get_ai_url() -> str:
    """Get AI service URL from environment."""
    return os.getenv("AI_URL", "http://localhost:11434")


def get_article_hours_back() -> int:
    """Get number of hours to look back for articles."""
    return int(os.getenv("ARTICLE_HOURS_BACK", "6"))


def get_log_level() -> str:
    """Get log level from environment."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def get_log_format() -> str:
    """Get log format from environment."""
    return os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
