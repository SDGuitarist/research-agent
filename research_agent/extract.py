"""Content extraction from HTML using trafilatura with fallback."""

import logging
import re
from dataclasses import dataclass
from html import unescape

import trafilatura
from readability import Document

from .fetch import FetchedPage

logger = logging.getLogger(__name__)

# Maximum HTML size to process (5MB) - prevents memory exhaustion attacks
MAX_HTML_SIZE = 5 * 1024 * 1024

# Minimum extracted text length to consider extraction successful
MIN_EXTRACTED_TEXT_LENGTH = 100


@dataclass
class ExtractedContent:
    """Extracted content from a web page."""
    url: str
    title: str
    text: str


def extract_content(page: FetchedPage) -> ExtractedContent | None:
    """
    Extract main content from a fetched page.

    Uses trafilatura as primary extractor, readability-lxml as fallback.

    Args:
        page: The fetched page to extract content from

    Returns:
        ExtractedContent if successful, None if extraction failed
    """
    # Guard against memory exhaustion from oversized HTML
    if len(page.html) > MAX_HTML_SIZE:
        logger.warning(
            f"Skipping oversized HTML ({len(page.html)} bytes) from {page.url}"
        )
        return None

    # Try trafilatura first (highest accuracy)
    result = _extract_with_trafilatura(page)
    if result and len(result.text) > MIN_EXTRACTED_TEXT_LENGTH:
        return result

    # Fallback to readability
    result = _extract_with_readability(page)
    if result and len(result.text) > MIN_EXTRACTED_TEXT_LENGTH:
        return result

    return None


def _extract_with_trafilatura(page: FetchedPage) -> ExtractedContent | None:
    """Extract content using trafilatura."""
    try:
        text = trafilatura.extract(
            page.html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        if not text:
            return None

        # Get metadata for title
        metadata = trafilatura.extract_metadata(page.html)
        title = metadata.title if metadata and metadata.title else ""

        return ExtractedContent(
            url=page.url,
            title=title,
            text=text,
        )

    except (AttributeError, TypeError, ValueError):
        return None


def _extract_with_readability(page: FetchedPage) -> ExtractedContent | None:
    """Extract content using readability-lxml."""
    try:
        doc = Document(page.html)

        # Get clean text from summary HTML
        summary_html = doc.summary()

        # Use trafilatura to convert HTML to text (it handles this well)
        text = trafilatura.extract(summary_html)

        if not text:
            # Manual fallback: strip tags
            text = re.sub(r'<[^>]+>', ' ', summary_html)
            text = unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()

        return ExtractedContent(
            url=page.url,
            title=doc.title() or "",
            text=text,
        )

    except (AttributeError, TypeError, ValueError, UnicodeDecodeError):
        return None


def extract_all(pages: list[FetchedPage]) -> list[ExtractedContent]:
    """
    Extract content from multiple pages.

    Args:
        pages: List of fetched pages

    Returns:
        List of successfully extracted content
    """
    results = []
    for page in pages:
        content = extract_content(page)
        if content:
            results.append(content)
    return results
