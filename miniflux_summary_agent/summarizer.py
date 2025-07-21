"""Article summarization functionality using Ollama AI."""

import logging

from ollama import AsyncClient

from .config import get_ai_url
from .models import ArticleInput, ArticleSummary


def summarize_article(summary: str) -> dict:
    """
    Summarize an article.

    Args:
        summary: A 2-4 sentence summary of the article

    Returns:
        dict: Contains summary
    """
    return {"summary": summary}


async def process_article(
    article: ArticleInput, logger: logging.Logger
) -> ArticleSummary:
    """Process a single article using direct Ollama tool calling."""

    try:
        # Use Ollama async client directly with tool calling
        client = AsyncClient(host=get_ai_url())

        logger.debug(f"Processing article {article.id}: {article.title}")

        response = await client.chat(
            model="llama3.1:8b",
            messages=[
                {
                    "role": "user",
                    "content": f'''
                Please summarize this article using the summarize_article tool:

                Title: "{article.title}"
                Source: {article.source}
                Author: {article.author}
                Published: {article.published_at}
                Content: {article.content[:1000]}...
                ''',
                }
            ],
            tools=[summarize_article],
        )

        # Extract tool call results
        if response["message"].get("tool_calls"):
            tool_call = response["message"]["tool_calls"][0]
            if tool_call["function"]["name"] == "summarize_article":
                result = summarize_article(**tool_call["function"]["arguments"])
                summary_text = result.get("summary", "Summary generation failed")
            else:
                summary_text = "Function not found"

            # Create ArticleSummary using the actual feed category
            summary = ArticleSummary(
                id=article.id,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                source=article.source,
                author=article.author,
                summary=summary_text,
                category=article.category,
                truncated=article.truncated,
                feed_id=article.feed_id,
            )

            logger.debug(f"Successfully processed article {article.id}")
            return summary
        else:
            logger.warning(f"No tool calls found for article {article.id}")
            logger.debug(f"Response: {response}")

            # Fallback
            return ArticleSummary(
                id=article.id,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                source=article.source,
                author=article.author,
                summary="Tool call failed",
                category=article.category,
                truncated=article.truncated,
                feed_id=article.feed_id,
            )

    except Exception as e:
        logger.error(
            f"Error processing article {article.id}: {type(e).__name__}: {e}",
            exc_info=True,
        )

        # Fallback
        return ArticleSummary(
            id=article.id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            source=article.source,
            author=article.author,
            summary="Processing failed",
            category=article.category,
            truncated=article.truncated,
            feed_id=article.feed_id,
        )


async def process_articles(
    articles: list[ArticleInput], logger: logging.Logger
) -> list[ArticleSummary]:
    """Process multiple articles sequentially to avoid overwhelming the model."""

    summaries = []
    for article in articles:
        try:
            summary = await process_article(article, logger)
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Error processing article {article.id}: {e}", exc_info=True)

    return summaries
