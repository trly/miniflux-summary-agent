# Miniflux Summary Agent

An intelligent RSS article summarization tool that fetches articles from your [Miniflux](https://miniflux.app/) RSS reader and generates concise AI-powered summaries organized by category.

## Quick Start

1. **Prerequisites**: Ensure you have [Miniflux](https://miniflux.app/) running and [Ollama](https://ollama.com/) installed locally
2. **Setup**: Follow the [Development Guide](DEVELOPMENT.md) for detailed setup instructions
3. **Run**: `uv run main.py` to generate summaries for the last 6 hours of articles

## How It Works

The agent follows a simple workflow:

1. **Fetch**: Retrieves articles from your Miniflux RSS reader using the API
2. **Enhance**: Detects brief summaries and fetches full article content when possible, or if needed
3. **Summarize**: Processes each article through Ollama to generate 2-4 sentence summaries
5. **Organize**: Groups summaries by category and generates an HTML report

## Configuration

Configure via environment variables:

- `MINIFLUX_URL`: Your Miniflux instance URL
- `MINIFLUX_API_KEY`: API key from Miniflux settings
- `ARTICLE_HOURS_BACK`: Hours of articles to fetch (default: 6)
- `LOG_LEVEL`: Logging level (default: INFO)

## Requirements

- Python ≥3.13
- [Miniflux](https://miniflux.app/) RSS reader instance
- [Ollama](https://ollama.com/) with uses [llama3.1:8b](https://ollama.com/library/llama3.1:8b)

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete setup instructions, testing, and contribution guidelines.

## License

This project is open source. Please check the repository for license details.
