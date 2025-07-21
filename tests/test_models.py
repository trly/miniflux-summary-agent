"""Test the Pydantic models with proper pytest assertions."""

import pytest

from miniflux_summary_agent.models import (
    ArticleInput,
    EntriesResponse,
    Entry,
    strip_html,
    truncate_content,
)

# Sample Miniflux response data
sample_response = {
    "total": 1,
    "entries": [
        {
            "id": 888,
            "user_id": 123,
            "feed_id": 42,
            "title": "Entry Title",
            "url": "http://example.org/article.html",
            "comments_url": "",
            "author": "Foobar",
            "content": "<p>HTML contents</p>",
            "hash": "29f99e4074cdacca1766f47697d03c66070ef6a14770a1fd5a867483c207a1bb",
            "published_at": "2016-12-12T16:15:19Z",
            "created_at": "2016-12-27T16:15:19Z",
            "status": "unread",
            "share_code": "",
            "starred": False,
            "reading_time": 1,
            "enclosures": None,
            "feed": {
                "id": 42,
                "user_id": 123,
                "title": "New Feed Title",
                "site_url": "http://example.org",
                "feed_url": "http://example.org/feed.atom",
                "checked_at": "2017-12-22T21:06:03.133839-05:00",
                "etag_header": "KyLxEflwnTGF5ecaiqZ2G0TxBCc",
                "last_modified_header": "Sat, 23 Dec 2017 01:04:21 GMT",
                "parsing_error_message": "",
                "parsing_error_count": 0,
                "scraper_rules": "",
                "rewrite_rules": "",
                "crawler": False,
                "blocklist_rules": "",
                "keeplist_rules": "",
                "user_agent": "",
                "username": "",
                "password": "",
                "disabled": False,
                "ignore_http_cache": False,
                "fetch_via_proxy": False,
                "category": {"id": 22, "user_id": 123, "title": "Another category"},
                "icon": {"feed_id": 42, "icon_id": 84},
            },
        }
    ],
}


def test_entries_response_parsing():
    """Test parsing EntriesResponse from Miniflux API data."""
    entries_response = EntriesResponse.model_validate(sample_response)

    assert entries_response.total == 1
    assert len(entries_response.entries) == 1

    entry = entries_response.entries[0]
    assert entry.id == 888
    assert entry.title == "Entry Title"
    assert entry.url == "http://example.org/article.html"
    assert entry.author == "Foobar"
    assert entry.content == "<p>HTML contents</p>"


def test_nested_models():
    """Test nested Feed and Category model parsing."""
    entries_response = EntriesResponse.model_validate(sample_response)
    entry = entries_response.entries[0]

    # Test Feed
    assert entry.feed is not None
    assert entry.feed.id == 42
    assert entry.feed.title == "New Feed Title"
    assert entry.feed.site_url == "http://example.org"

    # Test Category
    assert entry.feed.category is not None
    assert entry.feed.category.id == 22
    assert entry.feed.category.title == "Another category"


@pytest.mark.asyncio
async def test_article_input_from_entry():
    """Test converting Entry to ArticleInput with HTML stripping."""
    entries_response = EntriesResponse.model_validate(sample_response)
    entry = entries_response.entries[0]

    article = await ArticleInput.from_entry(entry)

    assert article.id == 888
    assert article.title == "Entry Title"
    assert article.url == "http://example.org/article.html"
    assert article.author == "Foobar"
    assert article.source == "New Feed Title"
    assert article.published_at == "2016-12-12T16:15:19Z"
    assert article.content == "HTML contents"  # HTML stripped
    assert article.truncated is False


def test_html_stripping():
    """Test HTML stripping functionality."""
    # Basic HTML stripping
    assert strip_html("<p>Hello world</p>") == "Hello world"

    # Multiple tags
    assert strip_html("<div><p>Hello</p> <span>world</span></div>") == "Hello world"

    # Complex HTML with attributes
    assert strip_html('<a href="http://example.com">Link</a> text') == "Link text"

    # Multiple whitespace cleanup
    assert strip_html("<p>  Hello   </p>  <div>  world  </div>") == "Hello world"

    # Punctuation cleanup
    assert strip_html("<p>Hello</p> <p>,</p> <p>world</p> <p>!</p>") == "Hello, world!"

    # Empty/None input
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_content_truncation():
    """Test content truncation functionality."""
    # Short content - no truncation
    content, truncated = truncate_content("Short text", 100)
    assert content == "Short text"
    assert truncated is False

    # Long content - gets truncated
    long_text = "a" * 100
    content, truncated = truncate_content(long_text, 50)
    assert len(content) == 50
    assert content.endswith("…")
    assert truncated is True

    # Exact length - no truncation
    content, truncated = truncate_content("exactly", 7)
    assert content == "exactly"
    assert truncated is False


@pytest.mark.asyncio
async def test_article_input_with_truncation():
    """Test ArticleInput creation with content truncation."""
    # Create entry with long HTML content
    long_content = "<p>" + "This is a very long paragraph. " * 20 + "</p>"

    entry_data = sample_response["entries"][0].copy()
    entry_data["content"] = long_content

    entry = Entry.model_validate(entry_data)

    # Test with small max_content_length to force truncation
    article = await ArticleInput.from_entry(entry, max_content_length=50)

    assert len(article.content) == 50
    assert article.content.endswith("…")
    assert article.truncated is True


@pytest.mark.asyncio
async def test_article_input_defaults():
    """Test ArticleInput handles missing/None values correctly."""
    # Create minimal entry data
    minimal_entry_data = {
        "id": 999,
        "user_id": 123,
        "feed_id": 42,
        "title": None,
        "url": None,
        "author": None,
        "content": None,
        "feed": None,
    }

    entry = Entry.model_validate(minimal_entry_data)
    article = await ArticleInput.from_entry(entry)

    assert article.id == 999
    assert article.title == "Untitled"
    assert article.url == ""
    assert article.author == "Unknown"
    assert article.source == "Unknown"
    assert article.content == ""
    assert article.truncated is False


@pytest.mark.asyncio
async def test_json_serialization():
    """Test JSON serialization of ArticleInput."""
    entries_response = EntriesResponse.model_validate(sample_response)
    entry = entries_response.entries[0]
    article = await ArticleInput.from_entry(entry)

    json_data = article.model_dump()

    # Verify all expected fields are present
    expected_fields = {
        "id",
        "title",
        "url",
        "published_at",
        "content",
        "source",
        "author",
        "category",
        "truncated",
        "feed_id",
    }
    assert set(json_data.keys()) == expected_fields

    # Verify field values
    assert json_data["id"] == 888
    assert json_data["title"] == "Entry Title"
    assert json_data["source"] == "New Feed Title"
    assert json_data["truncated"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
