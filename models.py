"""Pydantic models for Miniflux API responses and AI processing."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, AnyHttpUrl, ConfigDict
import re


class MinifluxBase(BaseModel):
    """Base class for Miniflux API models with forgiving validation."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class CategoryEnum(str, Enum):
    """Predefined categories for article classification."""
    TECHNOLOGY = "Technology"
    BUSINESS = "Business"
    POLITICS = "Politics"
    SCIENCE = "Science"
    SPORTS = "Sports"
    ENTERTAINMENT = "Entertainment"
    HEALTH = "Health"
    OTHER = "Other"


class Category(MinifluxBase):
    """Miniflux feed category."""
    id: int = Field(..., description="Category ID")
    user_id: int = Field(..., description="User ID who owns this category")
    title: Optional[str] = Field(None, description="Category title")


class Icon(MinifluxBase):
    """Miniflux feed icon."""
    feed_id: int = Field(..., description="Feed ID this icon belongs to")
    icon_id: int = Field(..., description="Icon ID")


class Feed(MinifluxBase):
    """Miniflux feed information."""
    id: int = Field(..., description="Feed ID")
    user_id: int = Field(..., description="User ID who owns this feed")
    title: str = Field(..., description="Feed title")
    site_url: Optional[str] = Field(None, description="Website URL")
    feed_url: Optional[str] = Field(None, description="Feed URL")
    checked_at: Optional[str] = Field(None, description="Last time feed was checked")
    etag_header: Optional[str] = Field(None, description="ETag header from last request")
    last_modified_header: Optional[str] = Field(None, description="Last-Modified header from last request")
    parsing_error_message: Optional[str] = Field(None, description="Error message if parsing failed")
    parsing_error_count: Optional[int] = Field(None, description="Number of parsing errors")
    scraper_rules: Optional[str] = Field(None, description="Scraper rules")
    rewrite_rules: Optional[str] = Field(None, description="Rewrite rules")
    crawler: Optional[bool] = Field(None, description="Whether crawler is enabled")
    blocklist_rules: Optional[str] = Field(None, description="Blocklist rules")
    keeplist_rules: Optional[str] = Field(None, description="Keeplist rules")
    user_agent: Optional[str] = Field(None, description="User agent string")
    username: Optional[str] = Field(None, description="Authentication username")
    password: Optional[str] = Field(None, description="Authentication password")
    disabled: Optional[bool] = Field(None, description="Whether feed is disabled")
    ignore_http_cache: Optional[bool] = Field(None, description="Whether to ignore HTTP cache")
    fetch_via_proxy: Optional[bool] = Field(None, description="Whether to fetch via proxy")
    category: Optional[Category] = Field(None, description="Feed category")
    icon: Optional[Icon] = Field(None, description="Feed icon")


class Entry(MinifluxBase):
    """Miniflux entry (article)."""
    id: int = Field(..., description="Entry ID")
    user_id: int = Field(..., description="User ID who owns this entry")
    feed_id: int = Field(..., description="Feed ID this entry belongs to")
    title: Optional[str] = Field(None, description="Entry title")
    url: Optional[str] = Field(None, description="Entry URL")
    comments_url: Optional[str] = Field(None, description="Comments URL")
    author: Optional[str] = Field(None, description="Entry author")
    content: Optional[str] = Field(None, description="Entry content (HTML)")
    hash: Optional[str] = Field(None, description="Entry hash")
    published_at: Optional[str] = Field(None, description="When entry was published")
    created_at: Optional[str] = Field(None, description="When entry was created in Miniflux")
    status: Optional[str] = Field(None, description="Entry status (read/unread)")
    share_code: Optional[str] = Field(None, description="Share code")
    starred: Optional[bool] = Field(None, description="Whether entry is starred")
    reading_time: Optional[int] = Field(None, description="Estimated reading time in minutes")
    enclosures: Optional[list] = Field(None, description="Entry enclosures")
    feed: Optional[Feed] = Field(None, description="Feed information")


class EntriesResponse(MinifluxBase):
    """Response from Miniflux get_entries API."""
    total: int = Field(..., description="Total number of entries")
    entries: list[Entry] = Field(..., description="List of entries")


def strip_html(html_content: str) -> str:
    """Strip HTML tags and clean up text content."""
    if not html_content:
        return ""
    
    # Remove HTML tags, replacing them with spaces only if needed
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Clean up whitespace (multiple spaces become single space)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Fix spaces before punctuation
    clean_text = re.sub(r'\s+([.!?,:;])', r'\1', clean_text)
    
    return clean_text


def truncate_content(content: str, max_length: int) -> tuple[str, bool]:
    """Truncate content if needed and return (content, was_truncated)."""
    if len(content) <= max_length:
        return content, False
    
    # Truncate and add ellipsis
    truncated = content[:max_length - 1] + "…"
    return truncated, True


class ArticleInput(BaseModel):
    """Simplified article input for AI processing."""
    id: int = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    published_at: Optional[str] = Field(None, description="When article was published")
    content: str = Field(..., description="Article content (plain text, truncated if needed)")
    source: str = Field(..., description="Source feed title")
    author: str = Field(..., description="Article author")
    truncated: bool = Field(False, description="Whether content was truncated")
    
    @classmethod
    def from_entry(cls, entry: Entry, max_content_length: int = 500) -> "ArticleInput":
        """Create ArticleInput from Miniflux Entry."""
        # Strip HTML and get plain text
        plain_content = strip_html(entry.content or "")
        
        # Truncate if needed with ellipsis
        content, truncated = truncate_content(plain_content, max_content_length)
        
        return cls(
            id=entry.id,
            title=entry.title or "Untitled",
            url=entry.url or "",
            published_at=entry.published_at,
            content=content,
            source=entry.feed.title if entry.feed else "Unknown",
            author=entry.author or "Unknown",
            truncated=truncated
        )


class ArticleSummary(BaseModel):
    """AI-generated summary of an article."""
    id: int = Field(..., description="Original article ID")
    title: str = Field(..., description="Article title")
    summary: str = Field(..., description="2-4 sentence summary")
    category: CategoryEnum = Field(..., description="Article category")
    source: str = Field(..., description="Source feed title")
    url: str = Field(..., description="Article URL")
    published_at: Optional[str] = Field(None, description="When article was published")
    author: str = Field(..., description="Article author")
    truncated: bool = Field(False, description="Whether content was truncated")


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
