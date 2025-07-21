# Development Guide

This guide will help you set up a development environment for the Miniflux Summary Agent.

## Prerequisites

- **Python ≥3.10** (check with `python --version`)
- **Docker & Docker Compose** (for running Miniflux locally)
- **Ollama** (for AI processing)

## Quick Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd miniflux-summary-agent
uv sync
```

### 2. Start Local Services

```bash
# Start Miniflux and PostgreSQL
docker-compose up -d

# Verify services are running
docker-compose logs -f miniflux
```

### 3. Setup Ollama Model

```bash
# Install and start Ollama (if not already installed)
# Visit https://ollama.com for installation instructions

# Pull the required model
ollama pull llama3.1:8b
```

### 4. Configure Environment

Create a `.env` file:

```bash
# Miniflux configuration
MINIFLUX_URL=http://localhost:8080
MINIFLUX_API_KEY=your_api_key_here

# Optional: Customize behavior
ARTICLE_HOURS_BACK=6
LOG_LEVEL=INFO
AI_URL=http://localhost:11434
```

### 5. Get Your Miniflux API Key

1. Open http://localhost:8080 in your browser
2. Login with `admin` / `admin123`
3. Go to Settings → API Keys
4. Create a new API key
5. Add it to your `.env` file

### 6. Add Some RSS Feeds

Add a few RSS feeds to test with:
- https://feeds.feedburner.com/oreilly/radar
- https://rss.cnn.com/rss/edition.rss
- https://feeds.npr.org/1001/rss.xml

## Running the Application

### Basic Usage

```bash
# Process articles from last 6 hours (default)
uv run miniflux-summary

# Process all articles
uv run miniflux-summary --all

# Alternative: use legacy main.py entry point
uv run main.py
uv run main.py --all
```

### Development Commands

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser

# See missing coverage lines
uv run pytest --cov --cov-report=term-missing

# Add new dependencies
uv add <package-name>
```

## Testing

The project maintains 98% test coverage. Tests are organized by functionality:

- `test_models.py` - Data model validation
- `test_article_fetching.py` - Content fetching logic
- `test_html_stripping.py` - HTML processing
- `test_category_rendering.py` - Category organization
- `test_integration.py` - End-to-end integration tests
- `test_end_to_end_fetching.py` - Full workflow tests

### Running Specific Tests

```bash
# Run specific test file
uv run pytest test_models.py

# Run specific test function
uv run pytest test_models.py::test_article_input_from_entry

# Run with verbose output
uv run pytest -v
```

## Architecture Overview

### Core Components

- **`main.py`**: Legacy entry point (use `miniflux-summary` command instead)
- **`miniflux_summary_agent/`**: Main package directory
  - **`cli.py`**: Command line interface
  - **`core.py`**: Application orchestration
  - **`models.py`**: Pydantic data models
  - **`fetcher.py`**: Article fetching logic
  - **`summarizer.py`**: AI summarization
  - **`renderer.py`**: HTML output generation
  - **`config.py`**: Environment configuration
  - **`logging.py`**: Logging setup
  - **`templates/`**: Jinja2 HTML templates

### Data Flow

1. **Fetch**: Get articles from Miniflux API using time filters
2. **Process**: Convert entries to `ArticleInput` objects
3. **Enhance**: Detect summaries and fetch full content when needed
4. **Summarize**: Process through Ollama AI with tool calling
5. **Organize**: Group by category and generate HTML output

### Key Features

- **Smart Content Detection**: Automatically detects when RSS content is just a summary
- **Async Processing**: Uses async/await for content fetching
- **Error Handling**: Graceful fallbacks for network and AI processing errors
- **Configurable**: Environment-driven configuration

## Service Management

### Miniflux

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f miniflux

# Access Miniflux UI
# URL: http://localhost:8080
# Default credentials: admin / admin123
```

### Ollama

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# List available models
ollama list

# Pull additional models (if needed)
ollama pull deepseek-r1:8b
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIFLUX_URL` | - | Miniflux instance URL |
| `MINIFLUX_API_KEY` | - | API key from Miniflux settings |
| `ARTICLE_HOURS_BACK` | `6` | Hours of articles to fetch |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | Standard | Log message format |
| `AI_URL` | `http://localhost:11434` | Ollama endpoint |

## Troubleshooting

### Common Issues

**"No articles found"**
- Check if your RSS feeds have recent content
- Try `--all` flag to process all articles
- Verify `ARTICLE_HOURS_BACK` setting

**Ollama connection errors**
- Ensure Ollama is running: `ollama list`
- Check model is available: `ollama pull llama3.1:8b`
- Verify AI_URL in environment

**Miniflux API errors**
- Verify Miniflux is running: `docker-compose ps`
- Check API key is correct
- Ensure Miniflux URL is accessible

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG uv run miniflux-summary

# This will show:
# - Detailed API requests
# - Content processing steps
# - AI model interactions
```

## Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Ensure coverage** stays above 85%: `uv run pytest --cov`
5. **Commit** changes: `git commit -m 'Add amazing feature'`
6. **Push** to branch: `git push origin feature/amazing-feature`
7. **Submit** a pull request

### Code Standards

- Follow existing code style and conventions
- Add docstrings for new functions
- Use type hints where appropriate
- Keep functions focused and testable
- Maintain high test coverage (≥85%)

## Performance Notes

- Articles are processed sequentially to avoid overwhelming the AI model
- Content fetching uses async requests with timeouts
- HTML processing includes smart content detection
- Memory usage is optimized for large article batches

## Security

- API keys are loaded from environment variables
- No sensitive data is logged
- External content fetching includes user-agent headers
- All external requests have timeouts
