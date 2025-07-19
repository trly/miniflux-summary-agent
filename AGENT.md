# Agent Instructions

## Commands
- **Run**: `uv run main.py`
- **Install dependencies**: `uv sync`
- **Add dependency**: `uv add <package>`
- **Python version**: Requires Python >=3.13
- **Test**: `uv run pytest`
- **Test with coverage**: `uv run pytest --cov`
- **Coverage report**: `uv run pytest --cov --cov-report=html` (generates htmlcov/ folder)
- **Coverage threshold**: 85% minimum required (currently 98%)
- **Coverage with missing lines**: `uv run pytest --cov --cov-report=term-missing`

## Local Development
- **Start services**: `docker-compose up -d`
- **Stop services**: `docker-compose down`
- **View logs**: `docker-compose logs -f miniflux`
- **Miniflux UI**: http://localhost:8080 (admin/admin123)
- **Setup Ollama model**: `ollama pull deepseek-r1:8b`

## Architecture
This is a simple RSS article summarization agent that:
1. Fetches recent articles from Miniflux RSS reader API
2. Summarizes them using Ollama AI (deepseek-r1:8b model)
3. Outputs organized summaries by category

**Key components:**
- `main.py`: Main application logic with async processing
- `models.py`: Pydantic models for data validation
- `test_*.py`: Comprehensive test suite with 98% coverage
- Dependencies: `miniflux` (RSS API), `ollama` (AI client), `pydantic` (data validation), `pytest-cov` (testing)
- Uses environment variables: `MINIFLUX_API_KEY`, `MINIFLUX_URL`, `LOG_LEVEL`, `LOG_FORMAT`, `ARTICLE_HOURS_BACK` (default: 6)
- Uses local Ollama endpoint: `http://localhost:11434`

## Code Style
- Use standard Python formatting and conventions
- Import order: standard library, third-party, local imports
- Environment variables for API keys and sensitive data
- Use f-strings for string formatting
- Descriptive variable names (`six_hours_ago`, `ai_client`)
- No existing rules files or specific style guidelines found
