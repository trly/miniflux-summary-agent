"""Article fetching functionality using Miniflux API."""

import logging
from datetime import datetime, timedelta, timezone

import miniflux

from .config import get_article_hours_back, get_miniflux_api_key, get_miniflux_url
from .models import ArticleInput, EntriesResponse


async def fetch_articles(
    logger: logging.Logger, all_articles: bool = False
) -> list[ArticleInput]:
    """Fetch articles from Miniflux and convert to ArticleInput format."""

    # Create Miniflux client
    miniflux_client = miniflux.Client(
        get_miniflux_url(), api_key=get_miniflux_api_key()
    )

    # Determine fetch parameters based on all_articles flag
    if all_articles:
        logger.debug("fetching all articles")
        get_entries_kwargs = {"order": "published_at", "direction": "desc"}
    else:
        # Get time range from environment variable (default to 6 hours)
        hours_back = get_article_hours_back()
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        # Convert to Unix timestamp for Miniflux API
        published_after_timestamp = int(time_threshold.timestamp())

        logger.debug(f"fetching articles from the last {hours_back} hours")

        get_entries_kwargs = {
            "published_after": published_after_timestamp,
            "order": "published_at",
            "direction": "desc",
        }

    try:
        # Get entries using Miniflux API
        entries_response = miniflux_client.get_entries(**get_entries_kwargs)

        # Parse the response using our Pydantic model
        entries_data = EntriesResponse.model_validate(entries_response)

        if all_articles:
            logger.debug(f"got {len(entries_data.entries)} articles total")
        else:
            hours_back = get_article_hours_back()
            logger.debug(
                f"got {len(entries_data.entries)} articles from the last {hours_back} hours"
            )

        if not entries_data.entries:
            if all_articles:
                logger.info("No entries found")
            else:
                hours_back = get_article_hours_back()
                logger.info(f"No entries found within the last {hours_back} hours")
            return []

    except Exception as e:
        logger.error(f"Error fetching entries: {e}", exc_info=True)
        return []

    # Convert entries to ArticleInput format (with async processing for content fetching)
    articles_for_ai = []
    for entry in entries_data.entries:
        try:
            article = await ArticleInput.from_entry(entry)
            articles_for_ai.append(article)
        except Exception as e:
            logger.warning(f"Error converting entry {entry.id}: {e}")
            continue

    return articles_for_ai
