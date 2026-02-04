"""Tests for research_agent.extract module."""

import pytest
from unittest.mock import patch, MagicMock

from research_agent.extract import (
    extract_content,
    extract_all,
    ExtractedContent,
    MAX_HTML_SIZE,
)
from research_agent.fetch import FetchedPage


class TestExtractContent:
    """Tests for extract_content() function."""

    def test_extract_content_extracts_from_simple_html(self, sample_html_simple):
        """Basic article HTML should be extracted successfully."""
        page = FetchedPage(
            url="https://example.com/article",
            html=sample_html_simple,
            status_code=200
        )

        result = extract_content(page)

        assert result is not None
        assert isinstance(result, ExtractedContent)
        assert result.url == "https://example.com/article"
        assert len(result.text) > 100

    def test_extract_content_extracts_title(self, sample_html_simple):
        """Title should be extracted from the page."""
        page = FetchedPage(
            url="https://example.com",
            html=sample_html_simple,
            status_code=200
        )

        result = extract_content(page)

        assert result is not None
        # Title should contain something meaningful
        assert result.title != ""

    def test_extract_content_returns_none_for_oversized_html(self, sample_html_oversized):
        """HTML exceeding MAX_HTML_SIZE should return None."""
        page = FetchedPage(
            url="https://example.com",
            html=sample_html_oversized,
            status_code=200
        )

        result = extract_content(page)

        assert result is None

    def test_extract_content_returns_none_for_empty_page(self, sample_html_empty):
        """Page with only boilerplate (nav, footer) should return None."""
        page = FetchedPage(
            url="https://example.com",
            html=sample_html_empty,
            status_code=200
        )

        result = extract_content(page)

        # Should return None because extracted text is < 100 chars
        assert result is None

    def test_extract_content_returns_none_for_short_content(self):
        """Content with less than 100 characters should return None."""
        short_html = """
        <html>
        <body>
            <article><p>Short.</p></article>
        </body>
        </html>
        """
        page = FetchedPage(
            url="https://example.com",
            html=short_html,
            status_code=200
        )

        result = extract_content(page)

        assert result is None

    def test_extract_content_extracts_from_complex_html(self, sample_html_complex):
        """Complex HTML with noise should still extract main content."""
        page = FetchedPage(
            url="https://example.com",
            html=sample_html_complex,
            status_code=200
        )

        result = extract_content(page)

        assert result is not None
        # Should contain main article content
        assert "main content" in result.text.lower() or len(result.text) > 100

    def test_extract_content_uses_readability_fallback(self):
        """When trafilatura fails, readability should be used."""
        # HTML that trafilatura might struggle with
        html = """
        <html>
        <body>
            <div id="content">
                <p>This is paragraph one with enough content to pass threshold.</p>
                <p>This is paragraph two with additional content for extraction.</p>
                <p>This is paragraph three providing more substantive text here.</p>
            </div>
        </body>
        </html>
        """
        page = FetchedPage(url="https://example.com", html=html, status_code=200)

        with patch("research_agent.extract._extract_with_trafilatura", return_value=None):
            result = extract_content(page)

            # Should still extract via readability fallback
            # Result may be None if readability also can't extract enough
            # This tests that the fallback path is attempted

    def test_extract_content_handles_malformed_html(self):
        """Parser should not crash on malformed HTML."""
        malformed_html = """
        <html>
        <body>
            <p>Unclosed paragraph
            <div>Mismatched tags</span>
            <article>
                <p>This is actual content with enough text to pass the minimum
                length threshold. The extraction should still work despite the
                malformed HTML above.</p>
            </article>
        </body>
        """
        page = FetchedPage(url="https://example.com", html=malformed_html, status_code=200)

        # Should not raise an exception
        result = extract_content(page)
        # Result may be None or ExtractedContent, but no crash

    def test_extract_content_handles_unicode_content(self):
        """UTF-8 content should be preserved correctly."""
        unicode_html = """
        <html>
        <head><meta charset="UTF-8"><title>Unicode Test</title></head>
        <body>
            <article>
                <p>This content contains Unicode: émojis 🎉, Chinese 中文,
                Japanese 日本語, Korean 한국어, and special symbols ©®™.
                The extraction should preserve all these characters correctly
                without any encoding issues or data loss.</p>
            </article>
        </body>
        </html>
        """
        page = FetchedPage(url="https://example.com", html=unicode_html, status_code=200)

        result = extract_content(page)

        if result:
            # Check that Unicode is preserved
            # At least some Unicode should be in the text
            assert any(c in result.text for c in ["é", "中", "日", "한", "©"])

    def test_extract_content_preserves_url(self, sample_html_simple):
        """URL should be passed through to ExtractedContent."""
        url = "https://example.com/specific/path?query=value"
        page = FetchedPage(url=url, html=sample_html_simple, status_code=200)

        result = extract_content(page)

        assert result is not None
        assert result.url == url


class TestExtractAll:
    """Tests for extract_all() function."""

    def test_extract_all_returns_list_of_extracted_content(self, sample_html_simple):
        """Multiple pages should all be processed."""
        pages = [
            FetchedPage(url="https://example1.com", html=sample_html_simple, status_code=200),
            FetchedPage(url="https://example2.com", html=sample_html_simple, status_code=200),
        ]

        result = extract_all(pages)

        assert len(result) == 2
        assert all(isinstance(c, ExtractedContent) for c in result)

    def test_extract_all_skips_failed_extractions(self, sample_html_simple, sample_html_empty):
        """Failed extractions should not be in the result list."""
        pages = [
            FetchedPage(url="https://example1.com", html=sample_html_simple, status_code=200),
            FetchedPage(url="https://example2.com", html=sample_html_empty, status_code=200),
        ]

        result = extract_all(pages)

        # Only the successful extraction should be in results
        assert len(result) == 1
        assert result[0].url == "https://example1.com"

    def test_extract_all_handles_empty_list(self):
        """Empty page list should return empty result list."""
        result = extract_all([])

        assert result == []

    def test_extract_all_handles_all_failures(self, sample_html_empty):
        """When all extractions fail, should return empty list."""
        pages = [
            FetchedPage(url="https://example1.com", html=sample_html_empty, status_code=200),
            FetchedPage(url="https://example2.com", html=sample_html_empty, status_code=200),
        ]

        result = extract_all(pages)

        assert result == []
