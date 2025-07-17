# Agent Instructions

## Commands
- **Run**: `uv run main.py`
- **Install dependencies**: `uv sync`
- **Add dependency**: `uv add <package>`
- **Python version**: Requires Python >=3.13
- **Test**: No test framework configured

## Local Development
- **Start services**: `docker-compose up -d`
- **Stop services**: `docker-compose down`
- **View logs**: `docker-compose logs -f miniflux`
- **Miniflux UI**: http://localhost:8080 (admin/admin123)
- **Setup Ollama model**: `docker-compose exec ollama ollama pull gemma3:4b`

## Architecture
This is a simple RSS article summarization agent that:
1. Fetches recent articles from Miniflux RSS reader API
2. Summarizes them using Ollama AI (gemma3:4b model)
3. Outputs organized summaries by category

**Key components:**
- `main.py`: Single-file application with main logic
- Dependencies: `miniflux` (RSS API), `ollama` (AI client)
- Uses environment variables: `MINIFLUX_API_KEY`, `AI_KEY`
- Hardcoded endpoints: `https://rss.home.trly.dev`, `https://ai.home.trly.dev`

## Code Style
- Use standard Python formatting and conventions
- Import order: standard library, third-party, local imports
- Environment variables for API keys and sensitive data
- Use f-strings for string formatting
- Descriptive variable names (`six_hours_ago`, `ai_client`)
- No existing rules files or specific style guidelines found
