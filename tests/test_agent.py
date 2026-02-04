"""Integration tests for research_agent.agent module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from research_agent.agent import ResearchAgent
from research_agent.modes import ResearchMode
from research_agent.errors import ResearchError
from research_agent.search import SearchResult
from research_agent.fetch import FetchedPage
from research_agent.extract import ExtractedContent
from research_agent.summarize import Summary


class TestResearchAgentQuickMode:
    """Integration tests for ResearchAgent in quick mode."""

    @pytest.fixture
    def mock_search_results(self):
        """Create mock search results."""
        return [
            SearchResult(
                title=f"Result {i}",
                url=f"https://example{i}.com/page",
                snippet=f"Snippet for result {i}."
            )
            for i in range(1, 4)
        ]

    @pytest.fixture
    def mock_fetched_pages(self):
        """Create mock fetched pages."""
        html = """
        <html><head><title>Test</title></head>
        <body><article><p>This is test content with enough text to pass
        the minimum length threshold for extraction. It contains useful
        information about the research topic.</p></article></body></html>
        """
        return [
            FetchedPage(url=f"https://example{i}.com/page", html=html, status_code=200)
            for i in range(1, 3)
        ]

    @pytest.fixture
    def mock_summaries(self):
        """Create mock summaries."""
        return [
            Summary(
                url=f"https://example{i}.com/page",
                title=f"Result {i}",
                summary=f"Summary of result {i} with key findings."
            )
            for i in range(1, 3)
        ]

    @pytest.mark.asyncio
    async def test_research_quick_mode_completes_pipeline(
        self, mock_search_results, mock_fetched_pages, mock_summaries
    ):
        """Quick mode should complete the full research pipeline."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            # Configure mocks
            mock_search.return_value = mock_search_results[:2]  # pass1=2
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = mock_fetched_pages
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="Test", text="Content " * 50)
            ]
            mock_summarize.return_value = mock_summaries
            mock_synthesize.return_value = "# Research Report\n\nContent here."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            result = await agent.research_async("test query")

            assert "Research Report" in result
            mock_search.assert_called()
            mock_synthesize.assert_called_once()

    @pytest.mark.asyncio
    async def test_research_quick_mode_uses_correct_source_count(self, mock_search_results):
        """Quick mode should use pass1=2, pass2=1 sources."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = mock_search_results[:2]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = []
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://example1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Report"
            mock_fetch.return_value = [
                FetchedPage(url="https://example1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            await agent.research_async("test query")

            # First search call should have max_results=2 (pass1_sources)
            first_call = mock_search.call_args_list[0]
            assert first_call.kwargs.get("max_results") == 2 or first_call[1].get("max_results") == 2

    @pytest.mark.asyncio
    async def test_research_quick_mode_deduplicates_urls(self, mock_search_results):
        """Same URL from both passes should appear only once."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            # Pass 1 returns results 1-2
            pass1_results = mock_search_results[:2]
            # Pass 2 returns result 1 (duplicate) + result 3 (new)
            pass2_results = [mock_search_results[0], mock_search_results[2]]

            mock_search.side_effect = [pass1_results, pass2_results]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://example1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://example1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            await agent.research_async("test query")

            # fetch_urls should be called with deduplicated URLs
            fetch_call = mock_fetch.call_args
            urls = fetch_call[0][0]
            # Should have 3 unique URLs (1, 2 from pass1 + 3 from pass2)
            assert len(set(urls)) == len(urls)  # No duplicates

    @pytest.mark.asyncio
    async def test_research_quick_mode_continues_on_pass2_failure(self, mock_search_results):
        """Pass 2 SearchError should be non-fatal."""
        from research_agent.errors import SearchError

        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            # Pass 1 succeeds, Pass 2 fails
            mock_search.side_effect = [
                mock_search_results[:2],
                SearchError("Rate limited"),
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://example1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://example1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Report from pass 1 only"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            result = await agent.research_async("test query")

            # Should still produce a report
            assert "Report" in result
            mock_synthesize.assert_called_once()


class TestResearchAgentStandardMode:
    """Integration tests for ResearchAgent in standard mode."""

    @pytest.mark.asyncio
    async def test_research_standard_mode_completes_pipeline(self):
        """Standard mode should complete with pass1=4, pass2=3."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url=f"https://ex{i}.com", snippet="S")
                for i in range(4)
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://ex1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Standard Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            result = await agent.research_async("test query")

            assert "Report" in result

    @pytest.mark.asyncio
    async def test_research_standard_mode_refines_query_from_snippets(self):
        """Standard mode should refine using snippets (before fetch)."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            search_results = [
                SearchResult(title="R", url=f"https://ex{i}.com", snippet=f"Snippet {i}")
                for i in range(4)
            ]
            mock_search.return_value = search_results
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://ex1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            await agent.research_async("test query")

            # refine_query should be called with snippets
            refine_call = mock_refine.call_args
            snippets_arg = refine_call[0][2]  # Third positional arg
            assert "Snippet 0" in snippets_arg or any("Snippet" in s for s in snippets_arg)

    def test_research_standard_mode_auto_saves_enabled(self):
        """Standard mode should have auto_save=True."""
        mode = ResearchMode.standard()
        assert mode.auto_save is True


class TestResearchAgentDeepMode:
    """Integration tests for ResearchAgent in deep mode."""

    @pytest.mark.asyncio
    async def test_research_deep_mode_completes_pipeline(self):
        """Deep mode should complete with fetch between passes."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url=f"https://ex{i}.com", snippet="S")
                for i in range(10)
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://ex1.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Deep Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
            result = await agent.research_async("test query")

            assert "Report" in result

    @pytest.mark.asyncio
    async def test_research_deep_mode_refines_query_from_summaries(self):
        """Deep mode should refine using summaries (after fetch)."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url=f"https://ex{i}.com", snippet="S")
                for i in range(10)
            ]
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            summaries = [
                Summary(url="https://ex1.com", title="T", summary="Deep summary content")
            ]
            mock_summarize.return_value = summaries
            mock_refine.return_value = "refined query"
            mock_synthesize.return_value = "Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
            await agent.research_async("test query")

            # refine_query should be called with summary texts
            refine_call = mock_refine.call_args
            summaries_arg = refine_call[0][2]
            assert any("Deep summary" in s for s in summaries_arg)

    @pytest.mark.asyncio
    async def test_research_deep_mode_fetches_new_urls_in_pass2(self):
        """Deep mode should fetch new URLs in second pass."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            # Pass 1 results
            pass1_results = [
                SearchResult(title="R", url=f"https://pass1-{i}.com", snippet="S")
                for i in range(10)
            ]
            # Pass 2 results (different URLs)
            pass2_results = [
                SearchResult(title="R", url=f"https://pass2-{i}.com", snippet="S")
                for i in range(10)
            ]

            mock_search.side_effect = [pass1_results, pass2_results]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://pass1-0.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://pass1-0.com", title="T", text="C " * 100)
            ]
            mock_summarize.return_value = [
                Summary(url="https://pass1-0.com", title="T", summary="S")
            ]
            mock_synthesize.return_value = "Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
            await agent.research_async("test query")

            # fetch_urls should be called twice (once for each pass)
            assert mock_fetch.call_count == 2


class TestResearchAgentErrorHandling:
    """Tests for ResearchAgent error handling."""

    @pytest.mark.asyncio
    async def test_research_raises_error_when_search_fails(self):
        """Pass 1 failure should raise ResearchError."""
        from research_agent.errors import SearchError

        with patch("research_agent.agent.search") as mock_search, \
             patch("builtins.print"):

            mock_search.side_effect = SearchError("Search failed completely")

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())

            with pytest.raises(ResearchError, match="Search failed"):
                await agent.research_async("test query")

    @pytest.mark.asyncio
    async def test_research_raises_error_when_no_pages_fetched(self):
        """Empty fetch results should raise ResearchError."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url="https://ex.com", snippet="S")
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = []  # No pages fetched

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())

            with pytest.raises(ResearchError, match="Could not fetch any pages"):
                await agent.research_async("test query")

    @pytest.mark.asyncio
    async def test_research_raises_error_when_no_content_extracted(self):
        """Empty extraction results should raise ResearchError."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.time.sleep"), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url="https://ex.com", snippet="S")
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex.com", html="<html></html>", status_code=200)
            ]
            mock_extract.return_value = []  # No content extracted

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())

            with pytest.raises(ResearchError, match="Could not extract content"):
                await agent.research_async("test query")


class TestResearchAgentRepr:
    """Tests for ResearchAgent repr and safety."""

    def test_repr_does_not_expose_api_key(self):
        """repr should not contain API key."""
        agent = ResearchAgent(api_key="sk-ant-secret-key-12345")
        repr_str = repr(agent)

        assert "sk-ant" not in repr_str
        assert "secret" not in repr_str
        assert "12345" not in repr_str

    def test_repr_shows_mode_and_settings(self):
        """repr should show mode name and settings."""
        agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
        repr_str = repr(agent)

        assert "deep" in repr_str
        assert "max_sources=10" in repr_str
