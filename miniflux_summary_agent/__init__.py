"""Miniflux Summary Agent - RSS article summarization using Ollama AI."""

from .core import run_summarization, summarize
from .logging import setup_logging
from .models import ArticleInput, ArticleSummary, EntriesResponse

try:
    from importlib.metadata import version
    __version__ = version("miniflux-summary-agent")
except ImportError:
    __version__ = "unknown"
__all__ = [
    "run_summarization",
    "summarize",
    "setup_logging",
    "EntriesResponse",
    "ArticleInput",
    "ArticleSummary",
]
