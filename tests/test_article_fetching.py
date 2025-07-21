"""Tests for article content fetching functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from miniflux_summary_agent.models import (
    ArticleInput,
    Category,
    Entry,
    Feed,
    fetch_article_content,
    is_single_sentence_summary,
)


class TestSingleSentenceSummaryDetection:
    """Test the is_single_sentence_summary function."""

    def test_empty_content(self):
        """Test that empty content is considered a summary."""
        assert is_single_sentence_summary("") is True
        assert is_single_sentence_summary(None) is True
        assert is_single_sentence_summary("   ") is True

    def test_very_short_content(self):
        """Test that very short content is considered a summary."""
        assert is_single_sentence_summary("Short text") is True
        assert is_single_sentence_summary("This is short.") is True

    def test_single_sentence(self):
        """Test that single sentences under 200 chars are considered summaries."""
        short_sentence = "This is a brief summary of the article."
        assert is_single_sentence_summary(short_sentence) is True

        # Even with HTML tags
        html_sentence = "<p>This is a brief summary of the article.</p>"
        assert is_single_sentence_summary(html_sentence) is True

    def test_two_short_sentences(self):
        """Test that two short sentences are considered summaries."""
        two_sentences = "This is sentence one. This is sentence two."
        assert is_single_sentence_summary(two_sentences) is True

    def test_summary_keywords(self):
        """Test that content with summary keywords is detected."""
        with_summary_keyword = (
            "This is a brief summary of the article content and main points."
        )
        assert is_single_sentence_summary(with_summary_keyword) is True

        with_excerpt_keyword = "Excerpt: The main topic discussed in this article."
        assert is_single_sentence_summary(with_excerpt_keyword) is True

    def test_long_content_not_summary(self):
        """Test that long content is not considered a summary."""
        long_content = """
        This is a much longer piece of content that contains multiple sentences.
        It goes on to explain various topics in detail. There are many paragraphs
        and a lot of information presented. This would not be considered just a
        summary because it has substantial content that provides detailed information
        about the topic at hand. The content continues for several more sentences.
        There are even more details here that make this clearly a full article.
        The content spans multiple paragraphs with extensive information and analysis.
        This is definitely not a brief summary or excerpt of the original content.
        """
        assert is_single_sentence_summary(long_content) is False

    def test_multiple_sentences_long(self):
        """Test that multiple long sentences are not summaries."""
        multi_sentence = """
        This is the first sentence which is quite long and detailed.
        This is the second sentence that also contains substantial information.
        This is the third sentence with even more detailed content.
        """
        assert is_single_sentence_summary(multi_sentence) is False


class TestArticleContentFetching:
    """Test the fetch_article_content function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful article content fetching."""
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>This is the main content of the article that provides substantial information about the topic.</p>
                    <p>It contains multiple paragraphs with detailed explanations and comprehensive coverage of the subject matter.</p>
                    <p>This would be considered full article content with enough detail to meet the minimum length requirements for content extraction.</p>
                    <p>Additional content here to ensure we meet the 200+ character threshold for substantial content detection.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            content = await fetch_article_content("https://example.com/article")

            assert content is not None
            assert "main content of the article" in content
            assert "multiple paragraphs" in content
            assert len(content) > 200

    @pytest.mark.asyncio
    async def test_request_failure(self):
        """Test handling of request failures."""
        with patch(
            "httpx.AsyncClient.get",
            side_effect=Exception("Network error"),
        ):
            content = await fetch_article_content("https://example.com/article")
            assert content is None

    @pytest.mark.asyncio
    async def test_insufficient_content(self):
        """Test handling when extracted content is too short."""
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <p>Short</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            content = await fetch_article_content("https://example.com/article")
            assert content is None

    @pytest.mark.asyncio
    async def test_fallback_to_body(self):
        """Test fallback to body when no article element found."""
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <div>
                    <h1>Article Title</h1>
                    <p>This is the main content that should be extracted when no specific article element exists.</p>
                    <p>It should still work by falling back to the body element.</p>
                    <p>This ensures compatibility with various website structures.</p>
                </div>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            content = await fetch_article_content("https://example.com/article")

            assert content is not None
            assert "main content that should be extracted" in content
            assert len(content) > 200


class TestArticleInputWithFetching:
    """Test ArticleInput.from_entry with content fetching."""

    @pytest.mark.asyncio
    async def test_fetch_when_summary_detected(self):
        """Test that full content is fetched when summary is detected."""
        # Create mock entry with summary content
        entry = Entry(
            id=1,
            user_id=1,
            feed_id=1,
            title="Test Article",
            url="https://example.com/article",
            content="<p>Brief summary.</p>",
            feed=Feed(
                id=1,
                user_id=1,
                title="Test Feed",
                category=Category(id=1, user_id=1, title="Tech"),
            ),
        )

        # Mock the fetch_article_content function
        with patch(
            "miniflux_summary_agent.models.fetch_article_content",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = "This is the full article content with much more detail and information."

            article = await ArticleInput.from_entry(entry)

            # Verify fetch was called
            mock_fetch.assert_called_once_with("https://example.com/article")

            # Verify full content was used
            assert "full article content" in article.content

    @pytest.mark.asyncio
    async def test_no_fetch_when_full_content(self):
        """Test that fetching is skipped when content is already substantial."""
        # Create mock entry with full content
        long_content = """
        This is a substantial piece of content that contains multiple sentences.
        It provides detailed information about the topic. There are several
        paragraphs worth of information here. This would not be considered
        just a summary because it contains substantial detail.
        The content continues with even more information and analysis.
        There are multiple points covered in depth with comprehensive explanations.
        This clearly represents the full article content rather than a brief summary.
        """

        entry = Entry(
            id=1,
            user_id=1,
            feed_id=1,
            title="Test Article",
            url="https://example.com/article",
            content=f"<p>{long_content}</p>",
            feed=Feed(
                id=1,
                user_id=1,
                title="Test Feed",
                category=Category(id=1, user_id=1, title="Tech"),
            ),
        )

        # Mock the fetch_article_content function
        with patch(
            "miniflux_summary_agent.models.fetch_article_content",
            new_callable=AsyncMock,
        ) as mock_fetch:
            article = await ArticleInput.from_entry(entry)

            # Verify fetch was NOT called
            mock_fetch.assert_not_called()

            # Verify original content was used
            assert "substantial piece of content" in article.content

    @pytest.mark.asyncio
    async def test_fetch_disabled(self):
        """Test that fetching can be disabled."""
        entry = Entry(
            id=1,
            user_id=1,
            feed_id=1,
            title="Test Article",
            url="https://example.com/article",
            content="<p>Brief summary.</p>",
            feed=Feed(
                id=1,
                user_id=1,
                title="Test Feed",
                category=Category(id=1, user_id=1, title="Tech"),
            ),
        )

        # Mock the fetch_article_content function
        with patch(
            "miniflux_summary_agent.models.fetch_article_content",
            new_callable=AsyncMock,
        ) as mock_fetch:
            article = await ArticleInput.from_entry(entry, fetch_full_content=False)

            # Verify fetch was NOT called
            mock_fetch.assert_not_called()

            # Verify original content was used
            assert "Brief summary" in article.content

    @pytest.mark.asyncio
    async def test_fetch_failure_fallback(self):
        """Test fallback to original content when fetch fails."""
        entry = Entry(
            id=1,
            user_id=1,
            feed_id=1,
            title="Test Article",
            url="https://example.com/article",
            content="<p>Brief summary.</p>",
            feed=Feed(
                id=1,
                user_id=1,
                title="Test Feed",
                category=Category(id=1, user_id=1, title="Tech"),
            ),
        )

        # Mock the fetch_article_content function to return None (failure)
        with patch(
            "miniflux_summary_agent.models.fetch_article_content",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = None

            article = await ArticleInput.from_entry(entry)

            # Verify fetch was called
            mock_fetch.assert_called_once()

            # Verify original content was used as fallback
            assert "Brief summary" in article.content
