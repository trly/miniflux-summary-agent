"""Test HTML stripping and content truncation."""

import pytest

from miniflux_summary_agent.models import strip_html, truncate_content


def test_strip_html_basic():
    """Test basic HTML tag removal."""
    html = "<p>Hello <b>world</b>!</p>"
    result = strip_html(html)
    assert result == "Hello world!"


def test_strip_html_complex():
    """Test complex HTML with multiple tags."""
    html = """
    <div class="content">
        <h1>Title</h1>
        <p>This is a <a href="link">link</a> and <em>emphasis</em>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
    """
    result = strip_html(html)
    assert "Title" in result
    assert "link" in result
    assert "emphasis" in result
    assert "Item 1" in result
    assert "<" not in result
    assert ">" not in result


def test_strip_html_empty():
    """Test empty or None input."""
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_strip_html_no_tags():
    """Test plain text without HTML tags."""
    text = "Just plain text"
    result = strip_html(text)
    assert result == text


def test_truncate_content_no_truncation():
    """Test content that doesn't need truncation."""
    content = "Short content"
    result, truncated = truncate_content(content, 100)
    assert result == content
    assert truncated is False


def test_truncate_content_with_truncation():
    """Test content that needs truncation."""
    content = "This is a very long piece of content that needs to be truncated"
    result, truncated = truncate_content(content, 20)
    assert len(result) == 20
    assert result.endswith("…")
    assert truncated is True


def test_truncate_content_exact_length():
    """Test content at exact max length."""
    content = "Exact"
    result, truncated = truncate_content(content, 5)
    assert result == content
    assert truncated is False


if __name__ == "__main__":
    pytest.main([__file__])
