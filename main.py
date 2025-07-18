"""Main application for RSS article summarization using direct Ollama tool calling."""

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
import miniflux
import ollama
from dotenv import load_dotenv

from models import EntriesResponse, ArticleInput, ArticleSummary, CategoryEnum


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
    
    return logging.getLogger(__name__)


logger = setup_logging()


def summarize_article(summary: str, category: str) -> dict:
    """
    Summarize an article and assign it a category.
    
    Args:
        summary: A 2-4 sentence summary of the article
        category: Category from: TECHNOLOGY, BUSINESS, POLITICS, SCIENCE, SPORTS, ENTERTAINMENT, HEALTH, OTHER
    
    Returns:
        dict: Contains summary and category
    """
    return {"summary": summary, "category": category}


async def process_article(article: ArticleInput) -> ArticleSummary:
    """Process a single article using direct Ollama tool calling."""
    
    try:
        # Use Ollama client directly with tool calling
        client = ollama.Client(host='http://localhost:11434')
        
        logger.info(f"Processing article {article.id}: {article.title}")
        
        response = client.chat(
            model='llama3.1:8b',
            messages=[{
                'role': 'user', 
                'content': f'''
                Please summarize this article and categorize it using the summarize_article tool:
                
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
                category_text = result.get('category', 'OTHER')
            else:
                summary_text = 'Function not found'
                category_text = 'OTHER'
            
            # Map category to enum
            category_mapping = {
                "TECHNOLOGY": CategoryEnum.TECHNOLOGY,
                "BUSINESS": CategoryEnum.BUSINESS,
                "POLITICS": CategoryEnum.POLITICS,
                "SCIENCE": CategoryEnum.SCIENCE,
                "SPORTS": CategoryEnum.SPORTS,
                "ENTERTAINMENT": CategoryEnum.ENTERTAINMENT,
                "HEALTH": CategoryEnum.HEALTH,
                "OTHER": CategoryEnum.OTHER
            }
            
            category = category_mapping.get(category_text, CategoryEnum.OTHER)
            
            # Create ArticleSummary
            summary = ArticleSummary(
                id=article.id,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                source=article.source,
                author=article.author,
                summary=summary_text,
                category=category,
                truncated=article.truncated
            )
            
            logger.info(f"Successfully processed article {article.id}")
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
                category=CategoryEnum.OTHER,
                truncated=article.truncated
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
            category=CategoryEnum.OTHER,
            truncated=article.truncated
        )


async def main():
    """Main application function."""
    logger.info("Starting RSS summarization agent...")
    
    # Load environment variables
    load_dotenv()
    
    # Create Miniflux client
    miniflux_client = miniflux.Client(
        os.getenv("MINIFLUX_URL"),
        api_key=os.getenv("MINIFLUX_API_KEY")
    )
    
    logger.info("Fetching recent articles...")
    
    try:
        # Get entries from past 6 hours
        entries_response = miniflux_client.get_entries()
        
        # Parse the response using our Pydantic model
        entries_data = EntriesResponse.model_validate(entries_response)
        
        # Filter entries to only include those published within the last 6 hours
        six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
        entries_data.entries = [
            entry for entry in entries_data.entries
            if entry.published_at and datetime.fromisoformat(entry.published_at.replace('Z', '+00:00')) >= six_hours_ago
        ]
        
        if not entries_data.entries:
            logger.info("No entries found within the last 6 hours")
            return
        
    except Exception as e:
        logger.error(f"Error fetching entries: {e}", exc_info=True)
        return
    
    # Convert to ArticleInput format
    articles_for_ai = []
    for entry in entries_data.entries:
        try:
            article = ArticleInput.from_entry(entry)
            articles_for_ai.append(article)
        except Exception as e:
            logger.warning(f"Error converting entry {entry.id}: {e}")
            continue
    
    if not articles_for_ai:
        logger.info("No valid articles to process")
        return
    
    logger.info(f"Processing {len(articles_for_ai)} articles using Ollama tool calling...")
    
    # Process articles sequentially to avoid overwhelming the model
    summaries = []
    for article in articles_for_ai:
        try:
            summary = await process_article(article)
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Error processing article {article.id}: {e}", exc_info=True)
    
    if not summaries:
        logger.info("No article summaries generated")
        return
    
    # Create simple report
    categories = {}
    for summary in summaries:
        if summary.category not in categories:
            categories[summary.category] = []
        categories[summary.category].append(summary)
    
    logger.info(f"Generated {len(summaries)} article summaries across {len(categories)} categories")
    
    # Output formatted results
    for category, articles in categories.items():
        logger.info(f"\n## {category.value} ({len(articles)} articles)")
        for article in articles:
            logger.info(f"**{article.title}** - *{article.source}*")
            logger.info(f"Published: {article.published_at}")
            logger.info(f"Summary: {article.summary}")
            logger.info(f"URL: {article.url}\n")


if __name__ == "__main__":
    asyncio.run(main())
