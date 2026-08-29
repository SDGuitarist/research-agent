"""Shared fixtures for research_agent tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from research_agent.fetch import FetchedPage
from research_agent.extract import ExtractedContent
from research_agent.summarize import Summary
from research_agent.search import SearchResult
from research_agent.relevance import SourceScore, RelevanceEvaluation


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
    """Factory for creating mock httpx streaming responses.

    Returns a response compatible with `client.stream("GET", url)`.
    Includes `is_redirect`, `aiter_bytes()`, and `encoding` for streaming.
    """
    def _create_response(
        status_code: int = 200,
        text: str = "<html><body>Content</body></html>",
        content_type: str = "text/html",
        url: str = "https://example.com",
        is_redirect: bool = False,
        location: str | None = None,
    ):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.is_redirect = is_redirect
        response.encoding = "utf-8"
        headers = {"content-type": content_type}
        if location:
            headers["location"] = location
        response.headers = headers
        response.url = MagicMock()
        response.url.__str__ = MagicMock(return_value=url)
        response.url.join = MagicMock(return_value=MagicMock(__str__=MagicMock(return_value=location or "")))

        # Async byte iterator for streaming
        async def _aiter_bytes():
            yield text.encode("utf-8")
        response.aiter_bytes = _aiter_bytes

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
    """List of SourceScore objects for relevance testing."""
    return [
        SourceScore(
            url="https://example1.com/page",
            title="Highly Relevant Article",
            score=5,
            explanation="Directly answers the query with specific information.",
        ),
        SourceScore(
            url="https://example2.com/page",
            title="Somewhat Relevant Article",
            score=3,
            explanation="Touches on the topic but missing key specifics.",
        ),
        SourceScore(
            url="https://example3.com/page",
            title="Off-topic Article",
            score=1,
            explanation="Does not address the research question.",
        ),
    ]


@pytest.fixture
def mock_evaluate_full_report(sample_summaries):
    """Factory for creating evaluate_sources result for full report."""
    def _create_result(summaries=None):
        summaries = summaries or sample_summaries
        return RelevanceEvaluation(
            decision="full_report",
            decision_rationale=f"All {len(summaries)} sources passed relevance threshold",
            surviving_sources=tuple(summaries),
            dropped_sources=(),
            total_scored=len(summaries),
            total_survived=len(summaries),
            refined_query=None,
        )
    return _create_result


@pytest.fixture
def mock_evaluate_short_report(sample_summaries):
    """Factory for creating evaluate_sources result for short report."""
    def _create_result(surviving=None, dropped_count=2):
        surviving = surviving or sample_summaries[:1]
        dropped = tuple(
            SourceScore(url=f"https://dropped{i}.com", title=f"Dropped {i}", score=2, explanation="Not relevant")
            for i in range(dropped_count)
        )
        return RelevanceEvaluation(
            decision="short_report",
            decision_rationale=f"Only {len(surviving)} sources passed, below full report threshold",
            surviving_sources=tuple(surviving),
            dropped_sources=dropped,
            total_scored=len(surviving) + dropped_count,
            total_survived=len(surviving),
            refined_query=None,
        )
    return _create_result


@pytest.fixture
def mock_evaluate_insufficient(sample_summaries):
    """Factory for creating evaluate_sources result for insufficient data."""
    def _create_result(dropped_count=3):
        dropped = tuple(
            SourceScore(url=f"https://dropped{i}.com", title=f"Dropped {i}", score=2, explanation="Not relevant")
            for i in range(dropped_count)
        )
        return RelevanceEvaluation(
            decision="insufficient_data",
            decision_rationale="No sources passed relevance threshold",
            surviving_sources=(),
            dropped_sources=dropped,
            total_scored=dropped_count,
            total_survived=0,
            refined_query=None,
        )
    return _create_result


# --- Postgres fixtures (Session 1: files→Postgres foundation) --------------
# OPT-IN: only tests that request `db` / `db_pool` / `committed_db` touch
# Postgres, so the rest of the suite runs with no database. Never SQLite —
# the job queue needs SELECT ... FOR UPDATE SKIP LOCKED.

import os
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

# TRUNCATE order (children before parents) for the committed/concurrency path.
_CONCURRENCY_TABLES = ("gap_audit", "reports", "jobs", "gaps", "critiques")


def _assert_disposable_db_url(url: str) -> None:
    """Raise AssertionError unless the URL's *database name* marks it disposable.

    The session setup runs ``DROP SCHEMA public CASCADE``, so the target must be
    a throwaway DB. A substring heuristic on the whole URL is unsafe — a password
    or hostname containing "test", or a real local dev DB on "localhost", would
    pass. Instead we require the database *name itself* to be a test DB
    ("test", or ending in "_test"/"-test"), which a prod/dev DB won't match.
    """
    dbname = urlparse(url).path.lstrip("/")
    assert dbname and (
        dbname == "test" or dbname.endswith("_test") or dbname.endswith("-test")
    ), (
        "Refusing destructive test setup: TEST_DATABASE_URL must point at a "
        "disposable test database whose name is 'test' or ends with '_test'/'-test' "
        f"(got database name {dbname!r})."
    )


@pytest.fixture(scope="session")
def database_url():
    """A disposable Postgres URL: TEST_DATABASE_URL (must name a *_test database)
    if set, else an ephemeral testcontainers Postgres (requires Docker)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        _assert_disposable_db_url(url)
        yield url
        return
    pytest.importorskip("testcontainers")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        # driver=None → a raw psycopg3 URL, not the SQLAlchemy '+psycopg2' form.
        yield pg.get_connection_url(driver=None)


@pytest.fixture(scope="session")
def _db_setup(database_url):
    """Apply migrations once per session against a clean schema."""
    from research_agent.migrate import run_migrations

    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
    run_migrations(database_url)
    yield


@pytest.fixture(scope="session")
def db_pool(_db_setup, database_url):
    """One connection pool for the whole session (connections are reused)."""
    from psycopg_pool import ConnectionPool

    with ConnectionPool(
        database_url,
        min_size=1,
        max_size=4,
        kwargs={"row_factory": dict_row},  # autocommit defaults False → rollback works
        open=True,
    ) as pool:
        yield pool


@pytest.fixture
def db(db_pool):
    """Fast, isolated connection: opens a transaction and always rolls back, so
    tests never see each other's writes. Code under test must accept this
    `conn` and must NOT call conn.commit()."""
    with db_pool.connection() as conn:
        with conn.transaction():
            yield conn
            raise psycopg.Rollback


@pytest.fixture
def committed_db(db_pool):
    """For tests that need committed rows visible across connections (the
    SKIP LOCKED claim). Tests open their own connections and commit; the queue
    tables are truncated afterward."""
    yield db_pool
    with db_pool.connection() as conn:
        conn.execute(
            f"TRUNCATE {', '.join(_CONCURRENCY_TABLES)} RESTART IDENTITY CASCADE"
        )


@pytest.fixture(autouse=True)
def _reset_db_pool():
    """Reset the app's module-global pool between tests (pre + post), mirroring
    the existing _reset_tavily_cache pattern. Close any existing pool BEFORE
    clearing it — close_pool() does close-then-clear atomically — so a leaked
    runtime pool from a prior test is torn down deterministically, never
    orphaned (which the old `_pool = None` pre-step did)."""
    import research_agent.db as db_module

    db_module.close_pool()
    yield
    db_module.close_pool()
