"""Miniflux Summary Agent - RSS article summarization using Ollama AI."""

from .core import run_summarization, summarize
from .logging import setup_logging
from .models import ArticleInput, ArticleSummary, EntriesResponse

__version__ = "0.1.0"
__all__ = [
    "run_summarization",
    "summarize",
    "setup_logging",
    "EntriesResponse",
    "ArticleInput",
    "ArticleSummary",
]
