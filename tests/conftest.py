"""Shared fixtures for research_agent tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from research_agent.fetch import FetchedPage
from research_agent.extract import ExtractedContent
from research_agent.summarize import Summary
from research_agent.search import SearchResult


# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_html_simple():
    """Basic HTML page with article content."""
    return (FIXTURES_DIR / "sample_html_simple.html").read_text()


@pytest.fixture
def sample_html_complex():
    """HTML page with navigation, footer, ads to test extraction."""
    return (FIXTURES_DIR / "sample_html_complex.html").read_text()


@pytest.fixture
def sample_html_empty():
    """HTML page with only boilerplate (nav, footer)."""
    return (FIXTURES_DIR / "sample_html_empty.html").read_text()


@pytest.fixture
def sample_html_oversized():
    """HTML exceeding 5MB limit."""
    # Generate HTML larger than 5MB (MAX_HTML_SIZE in extract.py)
    return "<html><body>" + "x" * (6 * 1024 * 1024) + "</body></html>"


@pytest.fixture
def sample_search_results():
    """List of SearchResult objects."""
    return [
        SearchResult(
            title="Python Async Best Practices",
            url="https://example1.com/python-async",
            snippet="Learn async/await patterns in Python with practical examples."
        ),
        SearchResult(
            title="Asyncio Tutorial",
            url="https://example2.com/asyncio-guide",
            snippet="Complete guide to Python asyncio for beginners."
        ),
        SearchResult(
            title="Concurrency in Python",
            url="https://example3.com/concurrency",
            snippet="Understanding threading, multiprocessing, and asyncio."
        ),
    ]


@pytest.fixture
def sample_summaries():
    """List of Summary objects."""
    return [
        Summary(
            url="https://example1.com/python-async",
            title="Python Async Best Practices",
            summary="Async/await in Python enables non-blocking I/O operations. "
                    "Key practices include using asyncio.gather for concurrent tasks "
                    "and proper exception handling in coroutines."
        ),
        Summary(
            url="https://example2.com/asyncio-guide",
            title="Asyncio Tutorial",
            summary="The asyncio module provides infrastructure for writing single-threaded "
                    "concurrent code using coroutines. Event loops manage task execution."
        ),
    ]


@pytest.fixture
def sample_fetched_pages(sample_html_simple):
    """List of FetchedPage objects."""
    return [
        FetchedPage(
            url="https://example1.com/python-async",
            html=sample_html_simple,
            status_code=200
        ),
        FetchedPage(
            url="https://example2.com/asyncio-guide",
            html=sample_html_simple,
            status_code=200
        ),
    ]


@pytest.fixture
def sample_extracted_content():
    """List of ExtractedContent objects."""
    return [
        ExtractedContent(
            url="https://example1.com/python-async",
            title="Python Async Best Practices",
            text="This is extracted content about async/await patterns in Python. "
                 "The content covers event loops, coroutines, and best practices "
                 "for writing asynchronous code. It includes examples of using "
                 "asyncio.gather for concurrent operations and proper error handling."
        ),
        ExtractedContent(
            url="https://example2.com/asyncio-guide",
            title="Asyncio Tutorial",
            text="A comprehensive guide to Python's asyncio module. Topics include "
                 "creating coroutines with async def, running tasks with await, "
                 "and managing event loops. The tutorial also covers synchronization "
                 "primitives and common patterns for async programming."
        ),
    ]


@pytest.fixture
def mock_anthropic_response():
    """Factory for creating mock Anthropic API responses."""
    def _create_response(text: str, stop_reason: str = "end_turn"):
        response = MagicMock()
        response.content = [MagicMock(text=text)]
        response.stop_reason = stop_reason
        return response
    return _create_response


@pytest.fixture
def mock_anthropic_stream():
    """Factory for creating mock Anthropic streaming responses."""
    def _create_stream(text_chunks: list[str]):
        stream = MagicMock()
        stream.__enter__ = MagicMock(return_value=stream)
        stream.__exit__ = MagicMock(return_value=False)
        stream.text_stream = iter(text_chunks)
        return stream
    return _create_stream


@pytest.fixture
def mock_ddgs_results():
    """Factory for creating mock DuckDuckGo search results."""
    def _create_results(count: int = 3):
        return [
            {
                "title": f"Result {i}",
                "href": f"https://example{i}.com/page",
                "body": f"Snippet for result {i} with relevant information."
            }
            for i in range(1, count + 1)
        ]
    return _create_results


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses."""
    def _create_response(
        status_code: int = 200,
        text: str = "<html><body>Content</body></html>",
        content_type: str = "text/html",
        url: str = "https://example.com"
    ):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.headers = {"content-type": content_type}
        response.url = url

        # For raise_for_status
        if status_code >= 400:
            from httpx import HTTPStatusError
            response.raise_for_status.side_effect = HTTPStatusError(
                message=f"HTTP {status_code}",
                request=MagicMock(),
                response=response
            )
        else:
            response.raise_for_status = MagicMock()

        return response
    return _create_response


# Relevance gate fixtures

@pytest.fixture
def sample_scored_sources():
    """List of scored source dicts for relevance testing."""
    return [
        {
            "url": "https://example1.com/page",
            "title": "Highly Relevant Article",
            "score": 5,
            "explanation": "Directly answers the query with specific information."
        },
        {
            "url": "https://example2.com/page",
            "title": "Somewhat Relevant Article",
            "score": 3,
            "explanation": "Touches on the topic but missing key specifics."
        },
        {
            "url": "https://example3.com/page",
            "title": "Off-topic Article",
            "score": 1,
            "explanation": "Does not address the research question."
        },
    ]


@pytest.fixture
def mock_evaluate_full_report(sample_summaries):
    """Factory for creating evaluate_sources result for full report."""
    def _create_result(summaries=None):
        summaries = summaries or sample_summaries
        return {
            "decision": "full_report",
            "decision_rationale": f"All {len(summaries)} sources passed relevance threshold",
            "surviving_sources": summaries,
            "dropped_sources": [],
            "total_scored": len(summaries),
            "total_survived": len(summaries),
            "refined_query": None,
        }
    return _create_result


@pytest.fixture
def mock_evaluate_short_report(sample_summaries):
    """Factory for creating evaluate_sources result for short report."""
    def _create_result(surviving=None, dropped_count=2):
        surviving = surviving or sample_summaries[:1]
        dropped = [
            {"url": f"https://dropped{i}.com", "title": f"Dropped {i}", "score": 2, "explanation": "Not relevant"}
            for i in range(dropped_count)
        ]
        return {
            "decision": "short_report",
            "decision_rationale": f"Only {len(surviving)} sources passed, below full report threshold",
            "surviving_sources": surviving,
            "dropped_sources": dropped,
            "total_scored": len(surviving) + dropped_count,
            "total_survived": len(surviving),
            "refined_query": None,
        }
    return _create_result


@pytest.fixture
def mock_evaluate_insufficient(sample_summaries):
    """Factory for creating evaluate_sources result for insufficient data."""
    def _create_result(dropped_count=3):
        dropped = [
            {"url": f"https://dropped{i}.com", "title": f"Dropped {i}", "score": 2, "explanation": "Not relevant"}
            for i in range(dropped_count)
        ]
        return {
            "decision": "insufficient_data",
            "decision_rationale": "No sources passed relevance threshold",
            "surviving_sources": [],
            "dropped_sources": dropped,
            "total_scored": dropped_count,
            "total_survived": 0,
            "refined_query": None,
        }
    return _create_result
