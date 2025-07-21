"""Command line interface for the RSS article summarization agent."""

import argparse
import asyncio

from .core import run_summarization
from .logging import setup_logging


async def main():
    """Main CLI function."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="RSS article summarization using Ollama"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all articles instead of using time filter",
    )
    args = parser.parse_args()

    # Run the summarization
    output_file = await run_summarization(all_articles=args.all)

    if output_file:
        print(f"Summary generated: {output_file}")
    else:
        print("No summary generated")


def cli_main():
    """Synchronous entry point for console script."""
    logger = setup_logging()
    logger.info("starting Miniflux AI agent")
    asyncio.run(main())
    logger.info("Miniflux AI agent shutting down")


if __name__ == "__main__":
    cli_main()
