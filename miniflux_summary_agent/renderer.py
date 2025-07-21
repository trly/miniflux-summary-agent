"""HTML report rendering functionality."""

import logging
from datetime import datetime

from jinja2 import Environment, PackageLoader, select_autoescape

from .config import get_miniflux_url
from .models import ArticleSummary


def generate_html_output(
    summaries: list[ArticleSummary], logger: logging.Logger
) -> str:
    """Generate HTML output from article summaries."""

    # Create simple report
    categories = {}
    for summary in summaries:
        if summary.category not in categories:
            categories[summary.category] = []
        categories[summary.category].append(summary)

    logger.info(
        f"summarized {len(summaries)} articles from {len(categories)} categories"
    )

    # Generate HTML output
    try:
        # Setup Jinja2 environment using PackageLoader
        env = Environment(
            loader=PackageLoader("miniflux_summary_agent", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template("summary.html")

        # Prepare template data
        template_data = {
            "categories": categories,
            "total_articles": len(summaries),
            "total_categories": len(categories),
            "generation_time": datetime.now(),
            "miniflux_url": get_miniflux_url(),
        }

        # Render HTML
        html_content = template.render(**template_data)

        # Write to file
        output_filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"summary generated: {output_filename}")
        return output_filename

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

        return None
