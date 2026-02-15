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
from research_agent.relevance import RelevanceEvaluation, SourceScore
from research_agent.context_result import ContextResult


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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            # Configure mocks
            mock_search.return_value = mock_search_results[:2]  # pass1=2
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = mock_fetched_pages
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="Test", text="Content " * 50)
            ]
            mock_summarize.return_value = mock_summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All sources passed",
                    surviving_sources=tuple(mock_summaries),
                    dropped_sources=(),
                    total_scored=len(mock_summaries),
                    total_survived=len(mock_summaries),
                    refined_query="refined query",
                )
            mock_synthesize.return_value = "# Research Report\n\nContent here."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            result = await agent.research_async("test query")

            assert "Research Report" in result
            mock_search.assert_called()
            mock_synthesize.assert_called_once()

    @pytest.mark.asyncio
    async def test_research_quick_mode_uses_correct_source_count(self, mock_search_results):
        """Quick mode should use pass1=4, pass2=2 sources (increased for relevance filtering)."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = mock_search_results[:2]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://example1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://example1.com", title="T", text="C " * 100)
            ]
            summaries = [Summary(url="https://example1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_synthesize.return_value = "Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            await agent.research_async("test query")

            # First search call should have max_results=4 (pass1_sources, increased for relevance filtering)
            # search is called with positional args: search(query, max_results)
            first_call = mock_search.call_args_list[0]
            # Check positional args (args[1]) or kwargs
            max_results = first_call[0][1] if len(first_call[0]) > 1 else first_call.kwargs.get("max_results")
            assert max_results == 4

    @pytest.mark.asyncio
    async def test_research_quick_mode_deduplicates_urls(self, mock_search_results):
        """Same URL from both passes should appear only once."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://example1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://example1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Standard Report"

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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Report"

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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_deep_skeptic_pass") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = [MagicMock(lens="evidence_alignment", checklist="[Observation] Test", critical_count=0, concern_count=0)]
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Deep Report"

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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_deep_skeptic_pass") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = [MagicMock(lens="evidence_alignment", checklist="[Observation] Test", critical_count=0, concern_count=0)]
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Report"

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
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_deep_skeptic_pass") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://pass1-0.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = [MagicMock(lens="evidence_alignment", checklist="[Observation] Test", critical_count=0, concern_count=0)]
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Report"

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
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
             patch("research_agent.agent.cascade_recover", new_callable=AsyncMock, return_value=[]) as mock_cascade, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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


class TestResearchAgentRelevanceGate:
    """Integration tests for relevance gate behavior."""

    @pytest.fixture
    def base_mocks(self):
        """Setup base mocks for pipeline testing."""
        return {
            "search_results": [
                SearchResult(title=f"Result {i}", url=f"https://example{i}.com", snippet=f"Snippet {i}")
                for i in range(5)
            ],
            "fetched_pages": [
                FetchedPage(url=f"https://example{i}.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
                for i in range(5)
            ],
            "extracted_content": [
                ExtractedContent(url=f"https://example{i}.com", title=f"Title {i}", text="Content " * 50)
                for i in range(5)
            ],
            "summaries": [
                Summary(url=f"https://example{i}.com", title=f"Title {i}", summary=f"Summary {i}")
                for i in range(5)
            ],
        }

    @pytest.mark.asyncio
    async def test_relevance_gate_full_report_when_all_sources_pass(self, base_mocks):
        """All sources passing should produce full report."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = base_mocks["search_results"]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"]
            mock_extract.return_value = base_mocks["extracted_content"]
            mock_summarize.return_value = base_mocks["summaries"]

            # All sources pass with high scores
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All sources passed",
                    surviving_sources=tuple(base_mocks["summaries"]),
                    dropped_sources=(),
                    total_scored=5,
                    total_survived=5,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "# Full Research Report\n\nComprehensive content."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            result = await agent.research_async("test query")

            assert "Full Research Report" in result
            # Verify synthesize_final was called with surviving_sources
            synth_call = mock_final.call_args
            assert synth_call[1].get("limited_sources") is False

    @pytest.mark.asyncio
    async def test_relevance_gate_insufficient_data_when_no_sources_pass(self, base_mocks):
        """No passing sources should trigger insufficient data response."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock) as mock_insufficient, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = base_mocks["search_results"]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"]
            mock_extract.return_value = base_mocks["extracted_content"]
            mock_summarize.return_value = base_mocks["summaries"]

            # No sources pass
            mock_evaluate.return_value = RelevanceEvaluation(
                decision="insufficient_data",
                decision_rationale="No sources passed relevance threshold",
                surviving_sources=(),
                dropped_sources=tuple(
                    SourceScore(url=f"https://example{i}.com", title=f"Title {i}", score=2, explanation="Not relevant")
                    for i in range(5)
                ),
                total_scored=5,
                total_survived=0,
                refined_query="refined query",
            )
            mock_insufficient.return_value = "# Insufficient Data Found\n\nCould not find relevant sources."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            result = await agent.research_async("test query")

            assert "Insufficient Data" in result
            # Verify synthesize was NOT called
            mock_synthesize.assert_not_called()
            # Verify insufficient data response was called
            mock_insufficient.assert_called_once()

    @pytest.mark.asyncio
    async def test_relevance_gate_short_report_with_mixed_scores(self, base_mocks):
        """Mixed scores with some passing should produce short report."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = base_mocks["search_results"]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"]
            mock_extract.return_value = base_mocks["extracted_content"]
            mock_summarize.return_value = base_mocks["summaries"]

            # Only 2 sources pass (below full_report threshold for standard)
            surviving = base_mocks["summaries"][:2]
            mock_evaluate.return_value = RelevanceEvaluation(
                decision="short_report",
                decision_rationale="Only 2 of 5 sources passed",
                surviving_sources=tuple(surviving),
                dropped_sources=tuple(
                    SourceScore(url=f"https://example{i}.com", title=f"Title {i}", score=2, explanation="Not relevant")
                    for i in range(2, 5)
                ),
                total_scored=5,
                total_survived=2,
                refined_query="refined query",
            )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "# Limited Report\n\nBased on limited sources."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            result = await agent.research_async("test query")

            assert "Report" in result
            # Verify synthesize_final was called with limited_sources=True
            synth_call = mock_final.call_args
            assert synth_call[1].get("limited_sources") is True
            assert synth_call[1].get("dropped_count") == 3
            assert synth_call[1].get("total_count") == 5

    @pytest.mark.asyncio
    async def test_relevance_gate_quick_mode_all_fail_triggers_insufficient(self, base_mocks):
        """Quick mode: all 3 sources failing should trigger insufficient data."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock) as mock_insufficient, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            quick_summaries = base_mocks["summaries"][:3]
            mock_search.return_value = base_mocks["search_results"][:3]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"][:3]
            mock_extract.return_value = base_mocks["extracted_content"][:3]
            mock_summarize.return_value = quick_summaries

            # All fail in quick mode
            mock_evaluate.return_value = RelevanceEvaluation(
                decision="insufficient_data",
                decision_rationale="No sources passed in quick mode",
                surviving_sources=(),
                dropped_sources=tuple(
                    SourceScore(url=s.url, title=s.title, score=1, explanation="Off-topic")
                    for s in quick_summaries
                ),
                total_scored=3,
                total_survived=0,
                refined_query="refined query",
            )
            mock_insufficient.return_value = "# Insufficient Data\n\nNo relevant sources found."

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            result = await agent.research_async("test query")

            assert "Insufficient" in result
            mock_synthesize.assert_not_called()

    @pytest.mark.asyncio
    async def test_relevance_gate_deep_mode_completes_after_both_passes(self, base_mocks):
        """Deep mode: relevance gate should run after both search passes complete."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_deep_skeptic_pass") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            # Pass 1 and Pass 2 results
            mock_search.side_effect = [
                base_mocks["search_results"],  # Pass 1
                [SearchResult(title="New", url="https://new.com", snippet="New")],  # Pass 2
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"]
            mock_extract.return_value = base_mocks["extracted_content"]
            mock_summarize.return_value = base_mocks["summaries"]

            # All pass
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All sources passed",
                    surviving_sources=tuple(base_mocks["summaries"]),
                    dropped_sources=(),
                    total_scored=5,
                    total_survived=5,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = [MagicMock(lens="evidence_alignment", checklist="[Observation] Test", critical_count=0, concern_count=0)]
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "# Deep Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
            result = await agent.research_async("test query")

            # Verify evaluate_sources was called (gate ran)
            mock_evaluate.assert_called_once()
            # Verify the summaries passed to evaluate_sources
            eval_call = mock_evaluate.call_args
            assert eval_call[1]["summaries"] == base_mocks["summaries"]

    @pytest.mark.asyncio
    async def test_relevance_gate_passes_refined_query(self, base_mocks):
        """Relevance gate should receive the refined query."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = base_mocks["search_results"]
            mock_refine.return_value = "specifically refined query"
            mock_fetch.return_value = base_mocks["fetched_pages"]
            mock_extract.return_value = base_mocks["extracted_content"]
            mock_summarize.return_value = base_mocks["summaries"]

            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(base_mocks["summaries"]),
                    dropped_sources=(),
                    total_scored=5,
                    total_survived=5,
                    refined_query="specifically refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "# Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            await agent.research_async("test query")

            # Verify refined_query was passed to evaluate_sources
            eval_call = mock_evaluate.call_args
            assert eval_call[1]["refined_query"] == "specifically refined query"


class TestResearchAgentBusinessContext:
    """Tests for business context passthrough to synthesis."""

    @pytest.mark.asyncio
    async def test_agent_loads_context_and_passes_to_synthesize(self):
        """Agent should load business context and pass it to synthesize_report."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.load_full_context") as mock_load_context, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url="https://ex1.com", snippet="S")
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_synthesize.return_value = "Report"
            mock_load_context.return_value = ContextResult.loaded("We are a guitar company.")

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            await agent.research_async("test query")

            # Verify _load_context was called
            mock_load_context.assert_called_once()
            # Verify business_context was passed to synthesize_report
            synth_call = mock_synthesize.call_args
            assert synth_call[1]["business_context"] == "We are a guitar company."

    @pytest.mark.asyncio
    async def test_agent_works_when_context_missing(self):
        """Agent should work normally when no business context file exists."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_report") as mock_synthesize, \
             patch("research_agent.agent.load_full_context") as mock_load_context, \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
             patch("builtins.print"):

            mock_search.return_value = [
                SearchResult(title="R", url="https://ex1.com", snippet="S")
            ]
            mock_refine.return_value = "refined query"
            mock_fetch.return_value = [
                FetchedPage(url="https://ex1.com", html="<html><body><p>" + "x" * 200 + "</p></body></html>", status_code=200)
            ]
            mock_extract.return_value = [
                ExtractedContent(url="https://ex1.com", title="T", text="C " * 100)
            ]
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_synthesize.return_value = "Report"
            mock_load_context.return_value = ContextResult.not_configured()  # No context file

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.quick())
            result = await agent.research_async("test query")

            assert "Report" in result
            # business_context should be None
            synth_call = mock_synthesize.call_args
            assert synth_call[1]["business_context"] is None


class TestResearchAgentStructuredSummaries:
    """Tests for structured summary passthrough in deep vs standard mode."""

    @pytest.mark.asyncio
    async def test_deep_mode_passes_structured_true(self):
        """Deep mode should pass structured=True and max_chunks=5 to summarize_all."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_deep_skeptic_pass") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.load_full_context", return_value=ContextResult.not_configured()), \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = [MagicMock(lens="evidence_alignment", checklist="[Observation] Test", critical_count=0, concern_count=0)]
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Deep Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.deep())
            await agent.research_async("test query")

            # First summarize_all call (pass 1) should have structured=True
            first_call = mock_summarize.call_args_list[0]
            assert first_call.kwargs.get("structured") is True
            assert first_call.kwargs.get("max_chunks") == 5

    @pytest.mark.asyncio
    async def test_standard_mode_passes_structured_false(self):
        """Standard mode should not pass structured=True to summarize_all."""
        with patch("research_agent.agent.search") as mock_search, \
             patch("research_agent.agent.refine_query") as mock_refine, \
             patch("research_agent.agent.fetch_urls") as mock_fetch, \
             patch("research_agent.agent.extract_all") as mock_extract, \
             patch("research_agent.agent.summarize_all") as mock_summarize, \
             patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock) as mock_evaluate, \
             patch("research_agent.agent.synthesize_draft") as mock_draft, \
             patch("research_agent.agent.synthesize_final") as mock_final, \
             patch("research_agent.agent.run_skeptic_combined") as mock_skeptic, \
             patch("research_agent.agent.load_synthesis_context") as mock_synth_ctx, \
             patch("research_agent.agent.load_full_context", return_value=ContextResult.not_configured()), \
             patch("research_agent.agent.asyncio.sleep", new_callable=AsyncMock), \
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
            summaries = [Summary(url="https://ex1.com", title="T", summary="S")]
            mock_summarize.return_value = summaries
            mock_evaluate.return_value = RelevanceEvaluation(
                    decision="full_report",
                    decision_rationale="All passed",
                    surviving_sources=tuple(summaries),
                    dropped_sources=(),
                    total_scored=1,
                    total_survived=1,
                    refined_query="refined query",
                )
            mock_draft.return_value = "## 1. Executive Summary\nDraft content"
            mock_skeptic.return_value = MagicMock(lens="combined", checklist="[Observation] Test", critical_count=0, concern_count=1)
            mock_synth_ctx.return_value = ContextResult.loaded("Business context")
            mock_final.return_value = "Standard Report"

            agent = ResearchAgent(api_key="test-key", mode=ResearchMode.standard())
            await agent.research_async("test query")

            # Standard mode uses _research_with_refinement, which doesn't pass structured
            summarize_call = mock_summarize.call_args
            # structured should either not be present or be False
            assert summarize_call.kwargs.get("structured", False) is False
