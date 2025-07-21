"""Main application for RSS article summarization using direct Ollama tool calling."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
import miniflux
import ollama
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from models import EntriesResponse, ArticleInput, ArticleSummary


# Configure logging
def setup_logging():
    """Configure logging based on environment variables."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set httpx logger to WARNING to suppress INFO level HTTP request logs
    logging.getLogger('httpx').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


def summarize_article(summary: str) -> dict:
    """
    Summarize an article.

    Args:
        summary: A 2-4 sentence summary of the article

    Returns:
        dict: Contains summary
    """
    return {"summary": summary}


async def process_article(article: ArticleInput) -> ArticleSummary:
    """Process a single article using direct Ollama tool calling."""

    try:
        # Use Ollama client directly with tool calling
        client = ollama.Client(host=os.getenv('AI_URL'))

        logger.debug(f"Processing article {article.id}: {article.title}")

        response = client.chat(
            model='llama3.1:8b',
            messages=[{
                'role': 'user',
                'content': f'''
                Please summarize this article using the summarize_article tool:

                Title: "{article.title}"
                Source: {article.source}
                Author: {article.author}
                Published: {article.published_at}
                Content: {article.content[:1000]}...
                '''
            }],
            tools=[summarize_article],
        )

        # Extract tool call results
        if response['message'].get('tool_calls'):
            tool_call = response['message']['tool_calls'][0]
            if tool_call['function']['name'] == 'summarize_article':
                result = summarize_article(**tool_call['function']['arguments'])
                summary_text = result.get('summary', 'Summary generation failed')
            else:
                summary_text = 'Function not found'

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
                feed_id=article.feed_id
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
                feed_id=article.feed_id
            )

    except Exception as e:
        logger.error(f"Error processing article {article.id}: {type(e).__name__}: {e}", exc_info=True)

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
            feed_id=article.feed_id
        )


async def main():
    """Main application function."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='RSS article summarization using Ollama')
    parser.add_argument('--all', action='store_true', 
                        help='Fetch all articles instead of using time filter')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Create Miniflux client
    miniflux_client = miniflux.Client(
        os.getenv("MINIFLUX_URL"),
        api_key=os.getenv("MINIFLUX_API_KEY")
    )

    # Determine fetch parameters based on --all flag
    if args.all:
        logger.debug("fetching all articles")
        get_entries_kwargs = {
            'order': 'published_at',
            'direction': 'desc'
        }
    else:
        # Get time range from environment variable (default to 6 hours)
        hours_back = int(os.getenv('ARTICLE_HOURS_BACK', '6'))
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Convert to Unix timestamp for Miniflux API
        published_after_timestamp = int(time_threshold.timestamp())
        
        logger.debug(f"fetching articles from the last {hours_back} hours")
        
        get_entries_kwargs = {
            'published_after': published_after_timestamp,
            'order': 'published_at',
            'direction': 'desc'
        }

    try:
        # Get entries using Miniflux API
        entries_response = miniflux_client.get_entries(**get_entries_kwargs)

        # Parse the response using our Pydantic model
        entries_data = EntriesResponse.model_validate(entries_response)
        
        if args.all:
            logger.debug(f"got {len(entries_data.entries)} articles total")
        else:
            logger.debug(f"got {len(entries_data.entries)} articles from the last {hours_back} hours")

        if not entries_data.entries:
            if args.all:
                logger.info("No entries found")
            else:
                logger.info(f"No entries found within the last {hours_back} hours")
            return

    except Exception as e:
        logger.error(f"Error fetching entries: {e}", exc_info=True)
        return

    # Convert entries to ArticleInput format (with async processing for content fetching)
    articles_for_ai = []
    for entry in entries_data.entries:
        try:
            article = await ArticleInput.from_entry(entry)
            articles_for_ai.append(article)
        except Exception as e:
            logger.warning(f"Error converting entry {entry.id}: {e}")
            continue

    if not articles_for_ai:
        logger.info("No valid articles to process")
        return

    logger.debug(f"summarizing {len(articles_for_ai)} articles")

    # Process articles sequentially to avoid overwhelming the model
    summaries = []
    for article in articles_for_ai:
        try:
            summary = await process_article(article)
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Error processing article {article.id}: {e}", exc_info=True)

    if not summaries:
        logger.info("no article summaries generated")
        return

    # Create simple report
    categories = {}
    for summary in summaries:
        if summary.category not in categories:
            categories[summary.category] = []
        categories[summary.category].append(summary)

    logger.info(f"summarized {len(summaries)} articles from {len(categories)} categories")

    # Generate HTML output
    try:
        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('summary.html')
        
        # Prepare template data
        template_data = {
            'categories': categories,
            'total_articles': len(summaries),
            'total_categories': len(categories),
            'generation_time': datetime.now(),
            'miniflux_url': os.getenv("MINIFLUX_URL")
        }
        
        # Render HTML
        html_content = template.render(**template_data)
        
        # Write to file
        output_filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"summary generated: {output_filename}")
        
    except Exception as e:
        logger.error(f"Error generating HTML output: {e}", exc_info=True)
        
        # Fallback to console output
        logger.warning("Falling back to console output:")
        for category, articles in categories.items():
            logger.info(f"\n## {category} ({len(articles)} articles)")
            for article in articles:
                logger.info(f"**{article.title}** - *{article.source}*")
                logger.info(f"Published: {article.published_at}")
                logger.info(f"Summary: {article.summary}")
                logger.info(f"URL: {article.url}\n")


if __name__ == "__main__":
    logger.info("starting Miniflux AI agent")
    asyncio.run(main())
    logger.info("Miniflux AI agent shutting down")
