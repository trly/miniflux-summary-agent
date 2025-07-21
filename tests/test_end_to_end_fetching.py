"""End-to-end test for article fetching functionality."""

import pytest

from miniflux_summary_agent.models import (
    ArticleInput,
    Category,
    Entry,
    Feed,
    is_single_sentence_summary,
)


@pytest.mark.asyncio
async def test_summary_detection_and_fetching_integration():
    """Test the complete flow from summary detection to content fetching."""

    # Test 1: Short summary should trigger fetching (but we'll disable it for testing)
    short_summary_entry = Entry(
        id=1,
        user_id=1,
        feed_id=1,
        title="Breaking News",
        url="https://example.com/article",
        content="<p>This is a brief summary.</p>",
        feed=Feed(
            id=1,
            user_id=1,
            title="News Feed",
            category=Category(id=1, user_id=1, title="News"),
        ),
    )

    # Verify summary detection
    plain_content = "This is a brief summary."
    assert is_single_sentence_summary(plain_content) is True

    # Test with fetching disabled (to avoid network calls in tests)
    article = await ArticleInput.from_entry(
        short_summary_entry, fetch_full_content=False
    )
    assert "brief summary" in article.content
    assert article.id == 1
    assert article.title == "Breaking News"

    # Test 2: Long content should NOT trigger fetching
    long_content = """
    This is a much longer piece of content that contains multiple sentences and substantial information.
    It provides detailed coverage of the topic with comprehensive analysis and extensive details.
    There are multiple paragraphs worth of information that clearly indicate this is full article content.
    The content continues with even more detailed explanations and thorough coverage of all aspects.
    This definitely represents complete article content rather than just a brief summary or excerpt.
    """

    long_content_entry = Entry(
        id=2,
        user_id=1,
        feed_id=1,
        title="Detailed Article",
        url="https://example.com/detailed-article",
        content=f"<div>{long_content}</div>",
        feed=Feed(
            id=1,
            user_id=1,
            title="News Feed",
            category=Category(id=1, user_id=1, title="News"),
        ),
    )

    # Verify long content is NOT detected as summary
    assert is_single_sentence_summary(long_content.strip()) is False

    # Test that fetching is not triggered for long content
    article = await ArticleInput.from_entry(long_content_entry, fetch_full_content=True)
    assert "multiple sentences and substantial information" in article.content
    assert article.id == 2
    assert article.title == "Detailed Article"


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_summary_detection_and_fetching_integration())
    print("✅ End-to-end article fetching test passed!")
