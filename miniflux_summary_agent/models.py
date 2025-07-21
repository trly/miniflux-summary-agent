"""Pydantic models for Miniflux API responses and AI processing."""

import logging
import re

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field


class MinifluxBase(BaseModel):
    """Base class for Miniflux API models with forgiving validation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# Note: CategoryEnum removed - categories now come from Miniflux feed categories


class Category(MinifluxBase):
    """Miniflux feed category."""

    id: int = Field(..., description="Category ID")
    user_id: int = Field(..., description="User ID who owns this category")
    title: str | None = Field(None, description="Category title")


class Icon(MinifluxBase):
    """Miniflux feed icon."""

    feed_id: int = Field(..., description="Feed ID this icon belongs to")
    icon_id: int = Field(..., description="Icon ID")


class Feed(MinifluxBase):
    """Miniflux feed information."""

    id: int = Field(..., description="Feed ID")
    user_id: int = Field(..., description="User ID who owns this feed")
    title: str = Field(..., description="Feed title")
    site_url: str | None = Field(None, description="Website URL")
    feed_url: str | None = Field(None, description="Feed URL")
    checked_at: str | None = Field(None, description="Last time feed was checked")
    etag_header: str | None = Field(None, description="ETag header from last request")
    last_modified_header: str | None = Field(
        None, description="Last-Modified header from last request"
    )
    parsing_error_message: str | None = Field(
        None, description="Error message if parsing failed"
    )
    parsing_error_count: int | None = Field(
        None, description="Number of parsing errors"
    )
    scraper_rules: str | None = Field(None, description="Scraper rules")
    rewrite_rules: str | None = Field(None, description="Rewrite rules")
    crawler: bool | None = Field(None, description="Whether crawler is enabled")
    blocklist_rules: str | None = Field(None, description="Blocklist rules")
    keeplist_rules: str | None = Field(None, description="Keeplist rules")
    user_agent: str | None = Field(None, description="User agent string")
    username: str | None = Field(None, description="Authentication username")
    password: str | None = Field(None, description="Authentication password")
    disabled: bool | None = Field(None, description="Whether feed is disabled")
    ignore_http_cache: bool | None = Field(
        None, description="Whether to ignore HTTP cache"
    )
    fetch_via_proxy: bool | None = Field(None, description="Whether to fetch via proxy")
    category: Category | None = Field(None, description="Feed category")
    icon: Icon | None = Field(None, description="Feed icon")


class Entry(MinifluxBase):
    """Miniflux entry (article)."""

    id: int = Field(..., description="Entry ID")
    user_id: int = Field(..., description="User ID who owns this entry")
    feed_id: int = Field(..., description="Feed ID this entry belongs to")
    title: str | None = Field(None, description="Entry title")
    url: str | None = Field(None, description="Entry URL")
    comments_url: str | None = Field(None, description="Comments URL")
    author: str | None = Field(None, description="Entry author")
    content: str | None = Field(None, description="Entry content (HTML)")
    hash: str | None = Field(None, description="Entry hash")
    published_at: str | None = Field(None, description="When entry was published")
    created_at: str | None = Field(
        None, description="When entry was created in Miniflux"
    )
    status: str | None = Field(None, description="Entry status (read/unread)")
    share_code: str | None = Field(None, description="Share code")
    starred: bool | None = Field(None, description="Whether entry is starred")
    reading_time: int | None = Field(
        None, description="Estimated reading time in minutes"
    )
    enclosures: list | None = Field(None, description="Entry enclosures")
    feed: Feed | None = Field(None, description="Feed information")


class EntriesResponse(MinifluxBase):
    """Response from Miniflux get_entries API."""

    total: int = Field(..., description="Total number of entries")
    entries: list[Entry] = Field(..., description="List of entries")


def strip_html(html_content: str) -> str:
    """Strip HTML tags and clean up text content."""
    if not html_content:
        return ""

    # Remove HTML tags, replacing them with spaces only if needed
    clean_text = re.sub(r"<[^>]+>", " ", html_content)

    # Clean up whitespace (multiple spaces become single space)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Fix spaces before punctuation
    clean_text = re.sub(r"\s+([.!?,:;])", r"\1", clean_text)

    return clean_text


def truncate_content(content: str, max_length: int) -> tuple[str, bool]:
    """Truncate content if needed and return (content, was_truncated)."""
    if len(content) <= max_length:
        return content, False

    # Truncate and add ellipsis
    truncated = content[: max_length - 1] + "…"
    return truncated, True


def is_single_sentence_summary(content: str) -> bool:
    """
    Detect if content appears to be just a single sentence summary.

    Args:
        content: The content to analyze

    Returns:
        bool: True if content appears to be a single sentence summary
    """
    if not content or len(content.strip()) < 20:
        return True

    # Clean content for analysis
    clean_content = strip_html(content).strip()

    # Count sentences (look for sentence endings)
    sentence_endings = re.findall(r"[.!?]+(?:\s|$)", clean_content)
    sentence_count = len(sentence_endings)

    # Consider it a summary if:
    # 1. Very short content (less than 100 chars)
    # 2. Only 1-2 sentences and less than 300 chars
    # 3. Contains summary-like keywords and less than 400 chars
    summary_keywords = ["summary", "excerpt", "brief", "overview", "abstract"]
    has_summary_keywords = any(
        keyword in clean_content.lower() for keyword in summary_keywords
    )

    return (
        len(clean_content) < 100
        or (sentence_count <= 2 and len(clean_content) < 300)
        or (has_summary_keywords and len(clean_content) < 400)
    )


async def fetch_article_content(url: str, timeout: int = 10) -> str | None:
    """
    Fetch the full article content from a URL.

    Args:
        url: The article URL to fetch
        timeout: Request timeout in seconds

    Returns:
        str: The article content, or None if fetching failed
    """
    logger = logging.getLogger(__name__)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, timeout=timeout, follow_redirects=True
            )
            response.raise_for_status()

            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Try to find main content area
            content_selectors = [
                "article",
                '[role="main"]',
                ".content",
                ".post-content",
                ".article-content",
                ".entry-content",
                "main",
                ".main-content",
            ]

            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break

            # Fallback to body if no specific content area found
            if not content_element:
                content_element = soup.find("body")

            if content_element:
                # Extract text content
                text_content = content_element.get_text(separator=" ", strip=True)

                # Clean up the text
                text_content = re.sub(r"\s+", " ", text_content).strip()

                # Return content if it's substantial
                if len(text_content) > 200:
                    return text_content

            logger.debug(f"Could not extract substantial content from {url}")
            return None

    except httpx.RequestError as e:
        logger.warning(f"Failed to fetch article content from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching article content from {url}: {e}")
        return None


class ArticleInput(BaseModel):
    """Simplified article input for AI processing."""

    id: int = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_at: str | None = Field(None, description="When article was published")
    content: str = Field(
        ..., description="Article content (plain text, truncated if needed)"
    )
    source: str = Field(..., description="Source feed title")
    author: str = Field(..., description="Article author")
    category: str = Field(..., description="Feed category from Miniflux")
    truncated: bool = Field(False, description="Whether content was truncated")
    feed_id: int = Field(..., description="Feed ID from Miniflux")

    @classmethod
    async def from_entry(
        cls,
        entry: Entry,
        max_content_length: int = 500,
        fetch_full_content: bool = True,
    ) -> "ArticleInput":
        """Create ArticleInput from Miniflux Entry."""
        # Strip HTML and get plain text
        plain_content = strip_html(entry.content or "")

        # Check if we should fetch full content
        should_fetch = (
            fetch_full_content
            and entry.url
            and is_single_sentence_summary(plain_content)
        )

        if should_fetch:
            logger = logging.getLogger(__name__)
            logger.debug(
                f"Detected summary content for article {entry.id}, fetching full content from {entry.url}"
            )

            # Try to fetch full article content
            full_content = await fetch_article_content(entry.url)
            if full_content:
                plain_content = full_content
                logger.debug(
                    f"Successfully fetched {len(full_content)} chars for article {entry.id}"
                )
            else:
                logger.warning(
                    f"Failed to fetch full content for article {entry.id}, using original content"
                )

        # Truncate if needed with ellipsis
        content, truncated = truncate_content(plain_content, max_content_length)

        # Get category from feed
        category = "Uncategorized"
        if entry.feed and entry.feed.category and entry.feed.category.title:
            category = entry.feed.category.title

        return cls(
            id=entry.id,
            title=entry.title or "Untitled",
            url=entry.url or "",
            published_at=entry.published_at,
            content=content,
            source=entry.feed.title if entry.feed else "Unknown",
            author=entry.author or "Unknown",
            category=category,
            truncated=truncated,
            feed_id=entry.feed_id,
        )


class ArticleSummary(BaseModel):
    """AI-generated summary of an article."""

    id: int = Field(..., description="Original article ID")
    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="2-4 sentence summary")
    category: str = Field(..., description="Feed category from Miniflux")
    source: str = Field(..., description="Source feed title")
    url: str = Field(..., description="Article URL")
    published_at: str | None = Field(None, description="When article was published")
    author: str = Field(..., description="Article author")
    truncated: bool = Field(False, description="Whether content was truncated")
    feed_id: int = Field(..., description="Feed ID from Miniflux")


# NOTE: These models are unused but kept for potential future use
# class CategorySummary(BaseModel):
#     """Summary of articles in a category."""
#     category: CategoryEnum = Field(..., description="Category name")
#     count: int = Field(..., description="Number of articles in this category")
#     articles: list[ArticleSummary] = Field(..., description="Articles in this category")


# class SummaryReport(BaseModel):
#     """Final summary report."""
#     total_articles: int = Field(..., description="Total number of articles processed")
#     categories: list[CategorySummary] = Field(..., description="Articles grouped by category")
#     generated_at: datetime = Field(..., description="When this report was generated")
