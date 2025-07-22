"""Miniflux Summary Agent - RSS article summarization using Ollama AI."""

try:
    from importlib.metadata import version
    __version__ = version("miniflux-summary-agent")
except ImportError:
    __version__ = "unknown"
