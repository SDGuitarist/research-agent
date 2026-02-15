"""Tests for research_agent.cascade module."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx

from research_agent.cascade import (
    cascade_recover,
    _fetch_via_jina,
    _jina_single,
    _fetch_via_tavily_extract,
    _is_extract_domain,
    _snippet_fallback,
    _extract_markdown_title,
    MIN_CONTENT_LENGTH,
)
from research_agent.extract import ExtractedContent
from research_agent.search import SearchResult


# --- Helpers ---


def _make_search_result(url, title="Title", snippet="A snippet with enough chars to pass the 50 char minimum filter.", raw_content=""):
    return SearchResult(title=title, url=url, snippet=snippet, raw_content=raw_content)


def _make_jina_response(status_code=200, text="", url="https://r.jina.ai/https://example.com"):
    """Create a mock httpx Response for Jina Reader."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.url = url
    return resp


# --- TestExtractMarkdownTitle ---


class TestExtractMarkdownTitle:
    """Tests for _extract_markdown_title() function."""

    def test_extracts_h1_title(self):
        text = "# My Page Title\n\nSome content here."
        assert _extract_markdown_title(text) == "My Page Title"

    def test_returns_empty_when_no_h1(self):
        text = "## Not an H1\n\nSome content."
        assert _extract_markdown_title(text) == ""

    def test_extracts_first_h1_only(self):
        text = "Some preamble\n# First Title\n# Second Title"
        assert _extract_markdown_title(text) == "First Title"

    def test_returns_empty_for_empty_string(self):
        assert _extract_markdown_title("") == ""

    def test_strips_whitespace_from_title(self):
        text = "#   Spaced Title   \nContent"
        assert _extract_markdown_title(text) == "Spaced Title"


# --- TestJinaReader ---


class TestJinaReader:
    """Tests for Jina Reader fetching functions."""

    @pytest.mark.asyncio
    async def test_jina_single_returns_content_on_success(self):
        """Successful Jina fetch should return ExtractedContent."""
        long_content = "# Page Title\n\n" + "Content paragraph. " * 20
        mock_resp = _make_jina_response(status_code=200, text=long_content)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        semaphore = asyncio.Semaphore(5)

        result = await _jina_single(mock_client, "https://example.com/page", semaphore)

        assert result is not None
        assert result.url == "https://example.com/page"
        assert result.title == "Page Title"
        assert "Content paragraph" in result.text
        mock_client.get.assert_called_once_with(
            "https://r.jina.ai/https://example.com/page",
            headers={"Accept": "text/markdown"},
        )

    @pytest.mark.asyncio
    async def test_jina_single_returns_none_on_non_200(self):
        """Non-200 response should return None."""
        mock_resp = _make_jina_response(status_code=403, text="Forbidden")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        semaphore = asyncio.Semaphore(5)

        result = await _jina_single(mock_client, "https://blocked.com", semaphore)
        assert result is None

    @pytest.mark.asyncio
    async def test_jina_single_returns_none_on_short_content(self):
        """Content shorter than MIN_CONTENT_LENGTH should return None."""
        mock_resp = _make_jina_response(status_code=200, text="Too short")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        semaphore = asyncio.Semaphore(5)

        result = await _jina_single(mock_client, "https://example.com", semaphore)
        assert result is None

    @pytest.mark.asyncio
    async def test_jina_single_returns_none_on_timeout(self):
        """Timeout should return None, not raise."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        semaphore = asyncio.Semaphore(5)

        result = await _jina_single(mock_client, "https://slow.com", semaphore)
        assert result is None

    @pytest.mark.asyncio
    async def test_jina_single_returns_none_on_connect_error(self):
        """Connection error should return None, not raise."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.ConnectError("connection refused")
        semaphore = asyncio.Semaphore(5)

        result = await _jina_single(mock_client, "https://down.com", semaphore)
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_via_jina_returns_successful_results(self):
        """_fetch_via_jina should return list of successful fetches."""
        long_content = "# Title\n\n" + "x" * 200

        mock_resp_success = _make_jina_response(status_code=200, text=long_content)
        mock_resp_fail = _make_jina_response(status_code=403, text="Blocked")

        async def mock_get(url, **kwargs):
            if "success" in url:
                return mock_resp_success
            return mock_resp_fail

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("research_agent.cascade.httpx.AsyncClient", return_value=mock_client):
            results = await _fetch_via_jina([
                "https://success.com/page",
                "https://blocked.com/page",
            ])

        assert len(results) == 1
        assert results[0].url == "https://success.com/page"

    @pytest.mark.asyncio
    async def test_fetch_via_jina_empty_urls(self):
        """Empty URL list should return empty list without making requests."""
        results = await _fetch_via_jina([])
        assert results == []


# --- TestTavilyExtract ---


class TestTavilyExtract:
    """Tests for Tavily Extract fetching."""

    @pytest.mark.asyncio
    async def test_returns_content_on_success(self):
        """Successful extract should return ExtractedContent list."""
        mock_response = {
            "results": [
                {"url": "https://example.com", "raw_content": "x" * 200},
                {"url": "https://other.com", "raw_content": "y" * 300},
            ]
        }

        with patch("tavily.TavilyClient") as mock_tavily_class:
            mock_client = MagicMock()
            mock_client.extract.return_value = mock_response
            mock_tavily_class.return_value = mock_client

            results = await _fetch_via_tavily_extract(
                ["https://example.com", "https://other.com"],
                "fake-key",
            )

        assert len(results) == 2
        assert results[0].url == "https://example.com"
        assert len(results[0].text) == 200

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_key(self):
        """Missing API key should return empty list."""
        results = await _fetch_via_tavily_extract(
            ["https://example.com"], None
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_urls(self):
        """Empty URL list should return empty list."""
        results = await _fetch_via_tavily_extract([], "fake-key")
        assert results == []

    @pytest.mark.asyncio
    async def test_filters_short_content(self):
        """Content shorter than MIN_CONTENT_LENGTH should be filtered."""
        mock_response = {
            "results": [
                {"url": "https://short.com", "raw_content": "tiny"},
                {"url": "https://long.com", "raw_content": "x" * 200},
            ]
        }

        with patch("tavily.TavilyClient") as mock_tavily_class:
            mock_client = MagicMock()
            mock_client.extract.return_value = mock_response
            mock_tavily_class.return_value = mock_client

            results = await _fetch_via_tavily_extract(
                ["https://short.com", "https://long.com"],
                "fake-key",
            )

        assert len(results) == 1
        assert results[0].url == "https://long.com"

    @pytest.mark.asyncio
    async def test_handles_none_raw_content(self):
        """None raw_content should be treated as empty."""
        mock_response = {
            "results": [
                {"url": "https://example.com", "raw_content": None},
            ]
        }

        with patch("tavily.TavilyClient") as mock_tavily_class:
            mock_client = MagicMock()
            mock_client.extract.return_value = mock_response
            mock_tavily_class.return_value = mock_client

            results = await _fetch_via_tavily_extract(
                ["https://example.com"], "fake-key"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_api_error(self):
        """API errors should return empty list, not raise."""
        from tavily.errors import BadRequestError as TavilyBadRequest
        with patch("tavily.TavilyClient") as mock_tavily_class:
            mock_client = MagicMock()
            mock_client.extract.side_effect = TavilyBadRequest("API error")
            mock_tavily_class.return_value = mock_client

            results = await _fetch_via_tavily_extract(
                ["https://example.com"], "fake-key"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_limits_to_20_urls(self):
        """Should only send first 20 URLs to Extract API."""
        urls = [f"https://example{i}.com" for i in range(25)]
        mock_response = {"results": []}

        with patch("tavily.TavilyClient") as mock_tavily_class:
            mock_client = MagicMock()
            mock_client.extract.return_value = mock_response
            mock_tavily_class.return_value = mock_client

            await _fetch_via_tavily_extract(urls, "fake-key")

            call_args = mock_client.extract.call_args
            assert len(call_args.kwargs["urls"]) == 20


# --- TestIsExtractDomain ---


class TestIsExtractDomain:
    """Tests for _is_extract_domain() function."""

    def test_matches_exact_domain(self):
        assert _is_extract_domain("https://weddingwire.com/vendor/123") is True

    def test_matches_subdomain(self):
        assert _is_extract_domain("https://www.theknot.com/marketplace/band") is True

    def test_rejects_non_matching_domain(self):
        assert _is_extract_domain("https://example.com/page") is False

    def test_matches_all_configured_domains(self):
        from research_agent.cascade import EXTRACT_DOMAINS
        for domain in EXTRACT_DOMAINS:
            assert _is_extract_domain(f"https://www.{domain}/page") is True

    def test_rejects_empty_url(self):
        assert _is_extract_domain("") is False

    def test_rejects_partial_domain_match(self):
        """'notweddingwire.com' should not match 'weddingwire.com'."""
        assert _is_extract_domain("https://notweddingwire.com/page") is False
        assert _is_extract_domain("https://evilyelp.com/biz/123") is False


# --- TestSnippetFallback ---


class TestSnippetFallback:
    """Tests for _snippet_fallback() function."""

    def test_returns_snippet_for_failed_url(self):
        """Should return ExtractedContent with snippet for failed URLs."""
        results = [
            _make_search_result("https://failed.com", title="Failed Page", snippet="A" * 60),
        ]

        contents = _snippet_fallback({"https://failed.com"}, results)

        assert len(contents) == 1
        assert contents[0].url == "https://failed.com"
        assert contents[0].title == "Failed Page"
        assert contents[0].text.startswith("[Source: search snippet]")

    def test_skips_short_snippets(self):
        """Snippets under 50 chars should be skipped."""
        results = [
            _make_search_result("https://short.com", snippet="Too short"),
        ]

        contents = _snippet_fallback({"https://short.com"}, results)
        assert contents == []

    def test_skips_urls_not_in_failed_set(self):
        """Only URLs in the failed set should get snippet fallback."""
        results = [
            _make_search_result("https://succeeded.com", snippet="A" * 60),
            _make_search_result("https://failed.com", snippet="B" * 60),
        ]

        contents = _snippet_fallback({"https://failed.com"}, results)

        assert len(contents) == 1
        assert contents[0].url == "https://failed.com"

    def test_deduplicates_urls(self):
        """Same URL appearing multiple times should only produce one fallback."""
        results = [
            _make_search_result("https://dup.com", snippet="First snippet " + "x" * 50),
            _make_search_result("https://dup.com", snippet="Second snippet " + "x" * 50),
        ]

        contents = _snippet_fallback({"https://dup.com"}, results)
        assert len(contents) == 1

    def test_empty_failed_urls(self):
        """Empty failed set should return empty list."""
        results = [_make_search_result("https://example.com")]
        contents = _snippet_fallback(set(), results)
        assert contents == []

    def test_empty_results(self):
        """Empty results should return empty list."""
        contents = _snippet_fallback({"https://example.com"}, [])
        assert contents == []

    def test_skips_empty_snippets(self):
        """Results with empty snippets should be skipped."""
        results = [
            _make_search_result("https://empty.com", snippet=""),
        ]

        contents = _snippet_fallback({"https://empty.com"}, results)
        assert contents == []


# --- TestCascadeRecover ---


class TestCascadeRecover:
    """Tests for cascade_recover() orchestration."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_failed_urls(self):
        """No failed URLs should return empty list immediately."""
        results = await cascade_recover([], [])
        assert results == []

    @pytest.mark.asyncio
    async def test_jina_recovers_urls(self):
        """Jina Reader should recover content for some failed URLs."""
        long_content = "# Title\n\n" + "x" * 200

        async def mock_fetch_jina(urls):
            return [
                ExtractedContent(url="https://example.com", title="Title", text=long_content)
            ]

        with patch("research_agent.cascade._fetch_via_jina", side_effect=mock_fetch_jina):
            with patch("research_agent.cascade._fetch_via_tavily_extract", new_callable=AsyncMock, return_value=[]):
                results = await cascade_recover(
                    ["https://example.com", "https://blocked.com"],
                    [_make_search_result("https://blocked.com")],
                )

        # Jina recovered 1, snippet fallback for the other
        jina_results = [r for r in results if not r.text.startswith("[Source:")]
        snippet_results = [r for r in results if r.text.startswith("[Source:")]

        assert len(jina_results) == 1
        assert jina_results[0].url == "https://example.com"
        assert len(snippet_results) == 1
        assert snippet_results[0].url == "https://blocked.com"

    @pytest.mark.asyncio
    async def test_tavily_extract_runs_on_remaining_high_value_domains(self):
        """Tavily Extract should run on remaining high-value domains after Jina."""
        async def mock_fetch_jina(urls):
            return []  # Jina fails on everything

        async def mock_tavily_extract(urls, key):
            return [
                ExtractedContent(url="https://www.weddingwire.com/page", title="", text="x" * 200)
            ]

        with patch("research_agent.cascade._fetch_via_jina", side_effect=mock_fetch_jina):
            with patch("research_agent.cascade._fetch_via_tavily_extract", side_effect=mock_tavily_extract):
                with patch.dict("os.environ", {"TAVILY_API_KEY": "fake"}):
                    results = await cascade_recover(
                        [
                            "https://www.weddingwire.com/page",
                            "https://regular-site.com/page",
                        ],
                        [
                            _make_search_result("https://www.weddingwire.com/page"),
                            _make_search_result("https://regular-site.com/page"),
                        ],
                    )

        # Tavily Extract got WeddingWire, snippet fallback for regular site
        assert len(results) == 2
        tavily_result = [r for r in results if r.url == "https://www.weddingwire.com/page"][0]
        assert not tavily_result.text.startswith("[Source:")

    @pytest.mark.asyncio
    async def test_snippet_fallback_for_all_layers_failed(self):
        """When all layers fail, snippet fallback should be used."""
        async def mock_fetch_jina(urls):
            return []

        async def mock_tavily_extract(urls, key):
            return []

        all_results = [
            _make_search_result("https://blocked.com", snippet="Important info about the band. " * 3),
        ]

        with patch("research_agent.cascade._fetch_via_jina", side_effect=mock_fetch_jina):
            with patch("research_agent.cascade._fetch_via_tavily_extract", side_effect=mock_tavily_extract):
                results = await cascade_recover(
                    ["https://blocked.com"],
                    all_results,
                )

        assert len(results) == 1
        assert results[0].text.startswith("[Source: search snippet]")
        assert "Important info about the band" in results[0].text

    @pytest.mark.asyncio
    async def test_full_cascade_ordering(self):
        """Cascade should try Jina → Tavily Extract → snippet in order."""
        call_order = []

        async def mock_fetch_jina(urls):
            call_order.append("jina")
            # Recover one URL
            return [
                ExtractedContent(url="https://site1.com", title="", text="x" * 200)
            ]

        async def mock_tavily_extract(urls, key):
            call_order.append("tavily_extract")
            # site2 is high-value but extract also fails
            return []

        all_results = [
            _make_search_result("https://site1.com"),
            _make_search_result("https://www.yelp.com/biz/band"),
            _make_search_result("https://site3.com"),
        ]

        with patch("research_agent.cascade._fetch_via_jina", side_effect=mock_fetch_jina):
            with patch("research_agent.cascade._fetch_via_tavily_extract", side_effect=mock_tavily_extract):
                results = await cascade_recover(
                    ["https://site1.com", "https://www.yelp.com/biz/band", "https://site3.com"],
                    all_results,
                )

        assert call_order == ["jina", "tavily_extract"]
        # site1 via Jina, yelp.com via snippet (tavily extract failed), site3 via snippet
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_skips_tavily_extract_when_no_high_value_domains(self):
        """Tavily Extract should be skipped when no remaining URLs are high-value."""
        async def mock_fetch_jina(urls):
            return []

        mock_tavily = AsyncMock(return_value=[])

        all_results = [
            _make_search_result("https://regular-site.com"),
        ]

        with patch("research_agent.cascade._fetch_via_jina", side_effect=mock_fetch_jina):
            with patch("research_agent.cascade._fetch_via_tavily_extract", mock_tavily):
                await cascade_recover(
                    ["https://regular-site.com"],
                    all_results,
                )

        # Tavily Extract should NOT have been called
        mock_tavily.assert_not_called()
