from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
import os
import miniflux
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel


class SummaryResult(BaseModel):
    content: str
    generated_at: datetime


@dataclass
class Dependencies:
    miniflux_client: miniflux.Client
    time_filter: datetime


# Create the agent with system prompt
agent = Agent(
    OpenAIModel(
        model_name='qwen3:4b',
        provider=OpenAIProvider(base_url="http://localhost:11434/v1"),
    ),
    deps_type=Dependencies,
    system_prompt="""
You are an intelligent RSS article summarization assistant.
Your primary function is to process lists of RSS articles, create concise summaries, and organize them by relevant tags and categories for easy consumption.

Core Responsibilities:

1. Article Analysis
- Read and analyze each RSS article thoroughly
- Identify key facts, main arguments, and significant developments
- Extract essential information while maintaining accuracy
- Note publication date, source, and author when available

2. Summarization Guidelines
- Create concise summaries (2-4 sentences per article)
- Focus on the most newsworthy and actionable information
- Maintain objectivity and avoid editorial commentary
- Preserve important context and nuance
- Include relevant numbers, dates, and specific details when significant

Use this format for your output:

# RSS Article Summary Report
*Generated on [DATE]*

## [CATEGORY NAME] ([count] articles)

### [Subcategory/Tag]
**[Article Title]** - *[Source, Date]*
[2-4 sentence summary]

---

## Quick Headlines
- [Brief one-line summary of top 3-5 most important stories]

## Trending Topics
- [List of recurring themes or subjects appearing across multiple articles]

Quality Standards:
- Accuracy: Never invent or misrepresent information
- Clarity: Use clear, accessible language
- Brevity: Capture essence without unnecessary detail
- Completeness: Include all critical information

For Breaking News: Mark urgent stories with 🚨
For Analysis/Opinion: Clearly distinguish between facts and opinions
For Technical Content: Explain complex concepts in accessible terms

Remember: Your goal is to help users quickly understand the day's important news across multiple sources while maintaining accuracy and providing useful organization.
""",
)


@agent.tool
async def fetch_recent_articles(ctx: RunContext[Dependencies]) -> List[Dict[str, Any]]:
    """Fetch recent articles from Miniflux RSS reader"""
    return ctx.deps.miniflux_client.get_entries(published_after=ctx.deps.time_filter)

async def main():
    load_dotenv()
    
    # Calculate time filter (6 hours ago)
    six_hours_ago = datetime.now() - timedelta(hours=6)
    
    # Create miniflux client
    miniflux_client = miniflux.Client(
        os.environ["MINIFLUX_URL"], 
        api_key=os.environ["MINIFLUX_API_KEY"]
    )
    
    # Create dependencies
    deps = Dependencies(
        miniflux_client=miniflux_client,
        time_filter=six_hours_ago
    )
    
    # Run the agent
    result = await agent.run(
        "Fetch recent articles and create a comprehensive summary organized by category",
        deps=deps
    )
    
    print(result.output)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
