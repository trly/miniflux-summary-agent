"""Test to investigate why category text is not visible in the HTML."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


def test_category_rendering():
    """Test the HTML file to check category rendering."""

    # Look for any summary HTML file
    summary_files = list(Path(__file__).parent.glob("summary_*.html"))
    if not summary_files:
        pytest.skip("No summary HTML files found")

    html_file = summary_files[0]  # Use the first one found

    file_url = f"file://{html_file.resolve()}"

    try:
        with sync_playwright() as p:
            # Use headless mode to avoid missing dependencies
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Navigate to the HTML file
                page.goto(file_url)

                # Wait for the page to load
                page.wait_for_load_state("networkidle")

                # Check if category headers exist and their content
                category_headers = page.locator(".category-header")
                count = category_headers.count()
                print(f"Found {count} category headers")

                for i in range(count):
                    header = category_headers.nth(i)
                    text = header.text_content()
                    inner_html = header.inner_html()
                    print(f"Category header {i}:")
                    print(f"  Text content: '{text}'")
                    print(f"  Inner HTML: {inner_html}")

                # Check article category spans
                article_categories = page.locator(".article-category")
                cat_count = article_categories.count()
                print(f"\nFound {cat_count} article category spans")

                for i in range(cat_count):
                    category = article_categories.nth(i)
                    text = category.text_content()
                    inner_html = category.inner_html()
                    print(f"Article category {i}:")
                    print(f"  Text content: '{text}'")
                    print(f"  Inner HTML: {inner_html}")

                # Get page content to debug
                print("\n=== Debugging category sections ===")
                category_sections = page.locator(".category-section")
                sections_count = category_sections.count()
                print(f"Found {sections_count} category sections")

                for i in range(sections_count):
                    section = category_sections.nth(i)
                    section_html = section.inner_html()
                    print(f"Section {i} HTML (first 200 chars):")
                    print(
                        section_html[:200] + "..."
                        if len(section_html) > 200
                        else section_html
                    )

            finally:
                browser.close()
    except Exception as e:
        pytest.skip(f"Playwright browser not available: {e}")


if __name__ == "__main__":
    test_category_rendering()
