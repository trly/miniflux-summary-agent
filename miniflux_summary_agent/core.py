"""Core orchestration for the RSS article summarization process."""

from .config import load_config
from .fetcher import fetch_articles
from .logging import setup_logging
from .renderer import generate_html_output
from .summarizer import process_articles


async def run_summarization(all_articles: bool = False) -> str:
    """Main entry point for the summarization process."""

    logger = setup_logging()

    # Load environment variables
    load_config()

    # Fetch articles
    articles = await fetch_articles(logger, all_articles)

    if not articles:
        logger.info("No valid articles to process")
        return None

    logger.debug(f"summarizing {len(articles)} articles")

    # Process articles
    summaries = await process_articles(articles, logger)

    if not summaries:
        logger.info("no article summaries generated")
        return None

    # Generate output
    output_file = generate_html_output(summaries, logger)
    return output_file


def summarize(all_articles: bool = False) -> str:
    """Synchronous wrapper for run_summarization."""
    import asyncio

    return asyncio.run(run_summarization(all_articles))
