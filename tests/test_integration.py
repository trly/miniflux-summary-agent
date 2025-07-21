"""Comprehensive integration tests for core functionality."""

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from miniflux_summary_agent.core import run_summarization
from miniflux_summary_agent.models import (
    ArticleInput,
    ArticleSummary,
    Category,
    Entry,
    Feed,
    Icon,
)
from miniflux_summary_agent.summarizer import process_article, summarize_article

# Test data fixtures


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def sample_feed():
    """Sample feed data."""
    return Feed(
        id=42,
        user_id=123,
        title="Tech News Feed",
        site_url="http://example.org",
        feed_url="http://example.org/feed.atom",
        category=Category(id=22, user_id=123, title="Technology"),
        icon=Icon(feed_id=42, icon_id=84),
    )


@pytest.fixture
def sample_entry(sample_feed):
    """Sample entry with HTML content."""
    return Entry(
        id=888,
        user_id=123,
        feed_id=42,
        title="Revolutionary AI Technology Breakthrough",
        url="http://example.org/ai-breakthrough.html",
        author="Dr. Jane Smith",
        content="""
        <div class="article-content">
            <h1>Breaking News</h1>
            <p>Scientists have developed a <strong>revolutionary</strong> new AI system that can process natural language with unprecedented accuracy.</p>
            <p>The breakthrough comes after years of research and development in <em>machine learning</em> and neural networks.</p>
            <ul>
                <li>95% accuracy in language understanding</li>
                <li>Real-time processing capabilities</li>
                <li>Energy-efficient implementation</li>
            </ul>
            <p>This technology could transform how we interact with computers and artificial intelligence systems.</p>
        </div>
        """,
        published_at="2024-01-15T10:30:00Z",
        created_at="2024-01-15T10:35:00Z",
        status="unread",
        starred=False,
        reading_time=3,
        feed=sample_feed,
    )


@pytest.fixture
def sample_entry_long_content(sample_feed):
    """Sample entry with very long content to test truncation."""
    long_content = "<p>" + "This is a very long article content. " * 100 + "</p>"
    return Entry(
        id=999,
        user_id=123,
        feed_id=42,
        title="Very Long Article",
        url="http://example.org/long-article.html",
        author="John Doe",
        content=long_content,
        published_at="2024-01-15T11:00:00Z",
        feed=sample_feed,
    )


@pytest.fixture
def sample_entries_response(sample_entry, sample_entry_long_content):
    """Sample entries response from Miniflux API."""
    # Use recent timestamps to ensure entries pass the 6-hour filter
    recent_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    entry1_dict = sample_entry.model_dump()
    entry1_dict["published_at"] = recent_timestamp

    entry2_dict = sample_entry_long_content.model_dump()
    entry2_dict["published_at"] = recent_timestamp

    return {"total": 2, "entries": [entry1_dict, entry2_dict]}


# Integration Tests


class TestArticleInputFromEntry:
    """Test ArticleInput.from_entry() end-to-end (HTML → plain text → truncation)."""

    @pytest.mark.asyncio
    async def test_html_to_plain_text_conversion(self, sample_entry):
        """Test complete HTML to plain text conversion."""
        article = await ArticleInput.from_entry(sample_entry)

        # Verify HTML tags are removed
        assert "<" not in article.content
        assert ">" not in article.content

        # Verify content is properly cleaned
        assert "Breaking News" in article.content
        assert "revolutionary" in article.content
        assert "machine learning" in article.content
        assert "95% accuracy" in article.content

        # Verify metadata is preserved
        assert article.id == 888
        assert article.title == "Revolutionary AI Technology Breakthrough"
        assert article.url == "http://example.org/ai-breakthrough.html"
        assert article.author == "Dr. Jane Smith"
        assert article.source == "Tech News Feed"
        assert article.published_at == "2024-01-15T10:30:00Z"
        assert article.truncated is False

    @pytest.mark.asyncio
    async def test_content_truncation(self, sample_entry_long_content):
        """Test content truncation when max length is exceeded."""
        # Use small max length to force truncation
        article = await ArticleInput.from_entry(
            sample_entry_long_content, max_content_length=100
        )

        assert len(article.content) == 100
        assert article.content.endswith("…")
        assert article.truncated is True

        # Test no truncation with large max length
        article_no_truncation = await ArticleInput.from_entry(
            sample_entry_long_content, max_content_length=5000
        )
        assert article_no_truncation.truncated is False
        assert not article_no_truncation.content.endswith("…")

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self, sample_feed):
        """Test handling of missing optional fields."""
        entry = Entry(
            id=123,
            user_id=123,
            feed_id=42,
            title=None,  # Missing title
            url=None,  # Missing URL
            author=None,  # Missing author
            content=None,  # Missing content
            feed=sample_feed,
        )

        article = await ArticleInput.from_entry(entry)

        assert article.title == "Untitled"
        assert article.url == ""
        assert article.author == "Unknown"
        assert article.content == ""
        assert article.source == "Tech News Feed"
        assert article.truncated is False

    @pytest.mark.asyncio
    async def test_missing_feed_info(self):
        """Test handling when feed info is missing."""
        entry = Entry(
            id=123,
            user_id=123,
            feed_id=42,
            title="Test Article",
            content="<p>Test content</p>",
            feed=None,
        )

        article = await ArticleInput.from_entry(entry)
        assert article.source == "Unknown"


class TestProcessArticle:
    """Test process_article() with mocked Ollama client - success and error paths."""

    @pytest.fixture
    def sample_article(self):
        """Sample ArticleInput for testing."""
        return ArticleInput(
            id=888,
            title="Revolutionary AI Technology Breakthrough",
            url="http://example.org/ai-breakthrough.html",
            published_at="2024-01-15T10:30:00Z",
            content="Scientists have developed a revolutionary new AI system...",
            source="Tech News Feed",
            author="Dr. Jane Smith",
            category="Technology",
            truncated=False,
            feed_id=123,
        )

    @pytest.mark.asyncio
    async def test_successful_processing(self, sample_article, mock_logger):
        """Test successful article processing with mocked Ollama."""
        mock_response = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "summarize_article",
                            "arguments": {
                                "summary": "Scientists developed a revolutionary AI system with 95% accuracy."
                            },
                        }
                    }
                ]
            }
        }

        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await process_article(sample_article, mock_logger)

            # Verify successful processing
            assert isinstance(result, ArticleSummary)
            assert result.id == 888
            assert result.title == "Revolutionary AI Technology Breakthrough"
            assert (
                result.summary
                == "Scientists developed a revolutionary AI system with 95% accuracy."
            )
            assert result.category == "Technology"  # Uses category from feed data
            assert result.source == "Tech News Feed"
            assert result.author == "Dr. Jane Smith"
            assert result.truncated is False

            # Verify Ollama client was called correctly
            mock_client.chat.assert_called_once()
            call_args = mock_client.chat.call_args
            assert call_args[1]["model"] == "llama3.1:8b"
            assert (
                "Revolutionary AI Technology Breakthrough"
                in call_args[1]["messages"][0]["content"]
            )

    @pytest.mark.asyncio
    async def test_no_tool_calls_fallback(self, sample_article, mock_logger):
        """Test fallback when Ollama doesn't return tool calls."""
        mock_response = {"message": {"content": "Some response without tool calls"}}

        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await process_article(sample_article, mock_logger)

            # Verify fallback behavior
            assert isinstance(result, ArticleSummary)
            assert result.summary == "Tool call failed"
            assert result.category == "Technology"  # Uses category from feed data
            assert result.id == sample_article.id

    @pytest.mark.asyncio
    async def test_unknown_function_fallback(self, sample_article, mock_logger):
        """Test fallback when unknown function is called."""
        mock_response = {
            "message": {
                "tool_calls": [
                    {"function": {"name": "unknown_function", "arguments": {}}}
                ]
            }
        }

        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await process_article(sample_article, mock_logger)

            # Verify fallback behavior
            assert result.summary == "Function not found"
            assert result.category == "Technology"  # Uses category from feed data

    @pytest.mark.asyncio
    async def test_ollama_connection_error(self, sample_article, mock_logger):
        """Test error handling when Ollama is unreachable."""
        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )
            mock_client_class.return_value = mock_client

            result = await process_article(sample_article, mock_logger)

            # Verify error handling
            assert isinstance(result, ArticleSummary)
            assert result.summary == "Processing failed"
            assert result.category == "Technology"  # Uses category from feed data
            assert result.id == sample_article.id

    @pytest.mark.asyncio
    async def test_ollama_timeout_error(self, sample_article, mock_logger):
        """Test error handling when Ollama times out."""
        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(side_effect=TimeoutError("Request timed out"))
            mock_client_class.return_value = mock_client

            result = await process_article(sample_article, mock_logger)

            assert result.summary == "Processing failed"
            assert result.category == "Technology"  # Uses category from feed data


class TestCategoryMapping:
    """Test category mapping logic including fallback when LLM fails."""

    def test_valid_category_mapping(self):
        """Test that categories are now taken from feed categories, not inferred."""
        # With the new implementation, categories come from Miniflux feeds
        # not from AI inference, so this test verifies the function signature
        result = summarize_article("Test summary")
        assert result["summary"] == "Test summary"
        assert "category" not in result  # Category no longer returned by this function

    @pytest.mark.asyncio
    async def test_invalid_category_fallback(self, mock_logger):
        """Test that categories come from feed data."""
        article = ArticleInput(
            id=1,
            title="Test",
            url="http://test.com",
            content="Test content",
            source="Test Source",
            author="Test Author",
            category="Technology",
            truncated=False,
            feed_id=456,
        )

        mock_response = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "summarize_article",
                            "arguments": {"summary": "Test summary"},
                        }
                    }
                ]
            }
        }

        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await process_article(article, mock_logger)

            # Should use the category from the article (feed data)
            assert result.category == "Technology"

    @pytest.mark.asyncio
    async def test_missing_category_fallback(self, mock_logger):
        """Test that category comes from feed data, not LLM response."""
        article = ArticleInput(
            id=1,
            title="Test",
            url="http://test.com",
            content="Test content",
            source="Test Source",
            author="Test Author",
            category="Sports",
            truncated=False,
            feed_id=789,
        )

        mock_response = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "summarize_article",
                            "arguments": {
                                "summary": "Test summary"
                                # Missing category
                            },
                        }
                    }
                ]
            }
        }

        with patch(
            "miniflux_summary_agent.summarizer.AsyncClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await process_article(article, mock_logger)

            # Should use the category from the article (feed data)
            assert result.category == "Sports"


class TestRunSummarizationErrorHandling:
    """Test error handling for Miniflux and Ollama failures in run_summarization function."""

    @pytest.mark.asyncio
    async def test_miniflux_connection_error(self):
        """Test handling of Miniflux API connection errors."""
        with (
            patch("miniflux.Client") as mock_miniflux,
            patch("os.getenv") as mock_getenv,
            patch("miniflux_summary_agent.config.load_dotenv"),
        ):
            mock_getenv.side_effect = lambda key, default=None: {
                "MINIFLUX_URL": "http://localhost:8080",
                "MINIFLUX_API_KEY": "test-key",
                "ARTICLE_HOURS_BACK": "6",
            }.get(key, default)

            mock_client = Mock()
            mock_client.get_entries.side_effect = ConnectionError("Connection refused")
            mock_miniflux.return_value = mock_client

            # Should not raise exception, just print error and return
            result = await run_summarization()
            assert result is None

    @pytest.mark.asyncio
    async def test_miniflux_authentication_error(self):
        """Test handling of Miniflux authentication errors."""
        with (
            patch("miniflux.Client") as mock_miniflux,
            patch("os.getenv") as mock_getenv,
            patch("miniflux_summary_agent.config.load_dotenv"),
        ):
            mock_getenv.side_effect = lambda key, default=None: {
                "MINIFLUX_URL": "http://localhost:8080",
                "MINIFLUX_API_KEY": "invalid-key",
                "ARTICLE_HOURS_BACK": "6",
            }.get(key, default)

            mock_client = Mock()
            mock_client.get_entries.side_effect = Exception("Authentication failed")
            mock_miniflux.return_value = mock_client

            result = await run_summarization()
            assert result is None

    @pytest.mark.asyncio
    async def test_no_recent_entries(self):
        """Test handling when no entries found within time window."""
        # Mock API response with no entries (what would happen when published_after filters everything out)
        empty_entries = {"total": 0, "entries": []}

        with (
            patch("miniflux.Client") as mock_miniflux,
            patch("os.getenv") as mock_getenv,
            patch("miniflux_summary_agent.config.load_dotenv"),
        ):
            mock_getenv.side_effect = lambda key, default=None: {
                "MINIFLUX_URL": "http://localhost:8080",
                "MINIFLUX_API_KEY": "test-key",
                "ARTICLE_HOURS_BACK": "6",
            }.get(key, default)

            mock_client = Mock()
            mock_client.get_entries.return_value = empty_entries
            mock_miniflux.return_value = mock_client

            result = await run_summarization()
            assert result is None

    @pytest.mark.asyncio
    async def test_article_conversion_errors(self, sample_entries_response):
        """Test handling of errors during article conversion."""
        with (
            patch("miniflux.Client") as mock_miniflux,
            patch("os.getenv") as mock_getenv,
            patch("miniflux_summary_agent.config.load_dotenv"),
            patch(
                "miniflux_summary_agent.models.ArticleInput.from_entry"
            ) as mock_from_entry,
        ):
            mock_getenv.side_effect = lambda key, default=None: {
                "MINIFLUX_URL": "http://localhost:8080",
                "MINIFLUX_API_KEY": "test-key",
                "ARTICLE_HOURS_BACK": "6",
            }.get(key, default)

            mock_client = Mock()
            mock_client.get_entries.return_value = sample_entries_response
            mock_miniflux.return_value = mock_client

            # Make from_entry raise an exception (it's now async)
            async def failing_from_entry(*args, **kwargs):
                raise Exception("Conversion failed")

            mock_from_entry.side_effect = failing_from_entry

            result = await run_summarization()
            assert result is None

    @pytest.mark.asyncio
    async def test_successful_end_to_end_processing(self, sample_entries_response):
        """Test successful end-to-end processing with mocked services."""
        with (
            patch("miniflux.Client") as mock_miniflux,
            patch("miniflux_summary_agent.summarizer.AsyncClient") as mock_ollama,
            patch("os.getenv") as mock_getenv,
            patch("miniflux_summary_agent.config.load_dotenv"),
        ):
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                "MINIFLUX_URL": "http://localhost:8080",
                "MINIFLUX_API_KEY": "test-key",
                "ARTICLE_HOURS_BACK": "6",
            }.get(key, default)

            # Mock Miniflux client
            mock_miniflux_client = Mock()
            mock_miniflux_client.get_entries.return_value = sample_entries_response
            mock_miniflux.return_value = mock_miniflux_client

            # Mock Ollama client
            mock_ollama_response = {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "summarize_article",
                                "arguments": {"summary": "Test summary for article"},
                            }
                        }
                    ]
                }
            }

            mock_ollama_client = Mock()
            mock_ollama_client.chat = AsyncMock(return_value=mock_ollama_response)
            mock_ollama.return_value = mock_ollama_client

            # Should complete without error
            result = await run_summarization()
            assert result is not None  # run_summarization() returns filename on success

            # Verify services were called
            mock_miniflux_client.get_entries.assert_called_once()
            assert mock_ollama_client.chat.call_count >= 1


# Utility function tests


def test_summarize_article_function():
    """Test the summarize_article function directly."""
    result = summarize_article("This is a test summary")

    assert result == {"summary": "This is a test summary"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
