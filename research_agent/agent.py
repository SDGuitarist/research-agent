"""Main research agent orchestrating the full pipeline."""

import asyncio
import logging
import random

from anthropic import Anthropic, AsyncAnthropic

from .search import search, refine_query, SearchResult
from .fetch import fetch_urls
from .extract import extract_all, ExtractedContent
from .summarize import summarize_all
from .synthesize import synthesize_report
from .relevance import evaluate_sources, generate_insufficient_data_response
from .decompose import decompose_query
from .errors import ResearchError, SearchError
from .modes import ResearchMode

logger = logging.getLogger(__name__)

# Base delay between search passes to avoid rate limits (with jitter added)
SEARCH_PASS_DELAY_BASE = 1.0
SEARCH_PASS_DELAY_JITTER = 0.5

# Stagger delay between sub-query searches to avoid rate limits
SUB_QUERY_STAGGER_BASE = 2.0
SUB_QUERY_STAGGER_JITTER = 0.5


class ResearchAgent:
    """
    A research agent that searches the web and generates markdown reports.

    Usage:
        agent = ResearchAgent(api_key="your-key")
        report = agent.research("What are Python async best practices?")

        # With modes
        agent = ResearchAgent(mode=ResearchMode.deep())
        report = agent.research("Comprehensive analysis of X")
    """

    # Prevent accidental attribute additions that could leak sensitive data
    __slots__ = (
        "_client",
        "_async_client",
        "mode",
        "max_sources",
        "summarize_model",
        "synthesize_model",
    )

    def __init__(
        self,
        api_key: str | None = None,
        max_sources: int | None = None,
        summarize_model: str = "claude-sonnet-4-20250514",
        synthesize_model: str = "claude-sonnet-4-20250514",
        mode: ResearchMode | None = None,
    ):
        """
        Initialize the research agent.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            max_sources: Maximum number of sources (overridden by mode if provided)
            summarize_model: Model for chunk summarization
            synthesize_model: Model for report synthesis
            mode: Research mode configuration (quick, standard, deep)
        """
        # Store clients as private attributes to reduce exposure risk
        # The API key is passed to clients but not stored separately
        self._client = Anthropic(api_key=api_key)
        self._async_client = AsyncAnthropic(api_key=api_key)
        self.mode = mode or ResearchMode.standard()
        # Use explicit max_sources if provided, otherwise use mode's default
        self.max_sources = max_sources if max_sources is not None else self.mode.max_sources
        self.summarize_model = summarize_model
        self.synthesize_model = synthesize_model

    def __repr__(self) -> str:
        """Safe repr that doesn't expose API clients or keys."""
        return (
            f"ResearchAgent(mode={self.mode.name!r}, "
            f"max_sources={self.max_sources}, "
            f"summarize_model={self.summarize_model!r}, "
            f"synthesize_model={self.synthesize_model!r})"
        )

    @property
    def client(self) -> Anthropic:
        """Access the sync Anthropic client."""
        return self._client

    @property
    def async_client(self) -> AsyncAnthropic:
        """Access the async Anthropic client."""
        return self._async_client

    def research(self, query: str) -> str:
        """
        Perform research on a query and return a markdown report.

        Args:
            query: The research question

        Returns:
            Markdown report string

        Raises:
            ResearchError: If research fails
            RuntimeError: If called from within an existing async event loop
        """
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "research() cannot be called from within an async context. "
                "Use 'await agent.research_async(query)' instead."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e):
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(self._research_async(query))
            raise

    async def research_async(self, query: str) -> str:
        """
        Async version of research for use in async contexts.

        Args:
            query: The research question

        Returns:
            Markdown report string

        Raises:
            ResearchError: If research fails
        """
        return await self._research_async(query)

    async def _research_async(self, query: str) -> str:
        """Async implementation of research."""
        is_deep = self.mode.name == "deep"

        # Try query decomposition if mode supports it
        decomposition = None
        if self.mode.decompose:
            print(f"\n[1/?] Analyzing query...")
            decomposition = await asyncio.to_thread(
                decompose_query, self.client, query
            )
            if decomposition["is_complex"]:
                sub_queries = decomposition["sub_queries"]
                reasoning = decomposition.get("reasoning", "")
                if reasoning:
                    print(f"      {reasoning}")
                print(f"      Decomposed into {len(sub_queries)} sub-queries:")
                for sq in sub_queries:
                    print(f"      → {sq}")
            else:
                print(f"      Simple query — skipping decomposition")

        # Calculate step count:
        # Base: deep=7, quick/standard=6
        # +1 if decomposition step is shown (mode.decompose is True)
        base_steps = 7 if is_deep else 6
        step_count = base_steps + (1 if self.mode.decompose else 0)

        search_step = 2 if self.mode.decompose else 1
        print(f"\n[{search_step}/{step_count}] Searching for: {query}")
        print(f"      Mode: {self.mode.name} ({self.mode.max_sources} sources, {self.mode.search_passes} passes)")

        if is_deep:
            return await self._research_deep(query, step_count, decomposition)
        else:
            return await self._research_with_refinement(query, step_count, decomposition)

    @staticmethod
    def _split_prefetched(
        results: list[SearchResult],
    ) -> tuple[list[ExtractedContent], list[str]]:
        """Separate results with raw_content from those needing HTTP fetch."""
        prefetched = []
        urls_to_fetch = []
        for r in results:
            if r.raw_content:
                prefetched.append(ExtractedContent(
                    url=r.url,
                    title=r.title,
                    text=r.raw_content,
                ))
            else:
                urls_to_fetch.append(r.url)
        return prefetched, urls_to_fetch

    async def _evaluate_and_synthesize(
        self,
        query: str,
        summaries: list,
        refined_query: str,
        relevance_step: int,
        synthesis_step: int,
        step_count: int,
    ) -> str:
        """
        Evaluate source relevance and synthesize report.

        This helper extracts common logic between quick/standard and deep modes.

        Args:
            query: Original research query
            summaries: List of Summary objects
            refined_query: The refined query used for pass 2
            relevance_step: Step number for relevance evaluation
            synthesis_step: Step number for synthesis
            step_count: Total step count for progress display

        Returns:
            Final report string (full, short, or insufficient data response)
        """
        print(f"\n[{relevance_step}/{step_count}] Evaluating source relevance...")
        evaluation = await evaluate_sources(
            query=query,
            summaries=summaries,
            mode=self.mode,
            client=self.async_client,
            refined_query=refined_query,
        )

        # Branch based on relevance gate decision
        if evaluation["decision"] == "insufficient_data":
            print(f"\n[{synthesis_step}/{step_count}] Generating insufficient data response...")
            return await generate_insufficient_data_response(
                query=query,
                refined_query=evaluation.get("refined_query"),
                dropped_sources=evaluation["dropped_sources"],
                client=self.async_client,
            )

        # Synthesize report (full or short)
        logger.info(f"Synthesizing report with {self.synthesize_model}...")
        limited_sources = evaluation["decision"] == "short_report"
        if limited_sources:
            print(f"\n[{synthesis_step}/{step_count}] Synthesizing short report with {self.synthesize_model}...\n")
        else:
            print(f"\n[{synthesis_step}/{step_count}] Synthesizing report with {self.synthesize_model}...\n")

        return synthesize_report(
            self.client,
            query,
            evaluation["surviving_sources"],
            model=self.synthesize_model,
            max_tokens=self.mode.max_tokens,
            mode_instructions=self.mode.synthesis_instructions,
            limited_sources=limited_sources,
            dropped_count=len(evaluation["dropped_sources"]),
            total_count=evaluation["total_scored"],
        )

    async def _research_with_refinement(
        self, query: str, step_count: int, decomposition: dict | None = None
    ) -> str:
        """Quick/standard mode: refine query using snippets before fetching."""
        # Step offset: if decomposition step is shown, shift all steps by 1
        offset = 1 if self.mode.decompose else 0

        # Search pass 1: always search the original query
        print(f"      Original query: {query}")
        try:
            pass1_results = await asyncio.to_thread(
                search, query, self.mode.pass1_sources
            )
            print(f"      Pass 1 found {len(pass1_results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        seen_urls = {r.url for r in pass1_results}

        # Sub-query searches (additive — original query already ran above)
        if decomposition and decomposition["is_complex"]:
            sub_queries = decomposition["sub_queries"]
            # Divide pass2 budget across sub-queries for additive coverage
            per_sq_sources = max(2, self.mode.pass2_sources // len(sub_queries))
            for i, sq in enumerate(sub_queries):
                delay = SUB_QUERY_STAGGER_BASE + random.uniform(0, SUB_QUERY_STAGGER_JITTER)
                await asyncio.sleep(delay)
                try:
                    sq_results = await asyncio.to_thread(search, sq, per_sq_sources)
                    new = [r for r in sq_results if r.url not in seen_urls]
                    for r in new:
                        seen_urls.add(r.url)
                        pass1_results.append(r)
                    print(f"      → \"{sq}\": {len(sq_results)} results ({len(new)} new)")
                except SearchError as e:
                    logger.warning(f"Sub-query search failed: {e}, continuing")
                    print(f"      → \"{sq}\": failed, continuing")

        # Refine query using snippets
        snippets = [r.snippet for r in pass1_results if r.snippet]
        refined_query = refine_query(self.client, query, snippets)
        if refined_query == query:
            print(f"      Query refinement skipped (using original query)")
        else:
            print(f"      Refined query: {refined_query}")

        # Search pass 2 with refined query
        delay = SEARCH_PASS_DELAY_BASE + random.uniform(0, SEARCH_PASS_DELAY_JITTER)
        await asyncio.sleep(delay)
        try:
            pass2_results = await asyncio.to_thread(
                search, refined_query, self.mode.pass2_sources
            )
            new_results = [r for r in pass2_results if r.url not in seen_urls]
            print(f"      Refined pass found {len(pass2_results)} results ({len(new_results)} new)")
        except SearchError as e:
            logger.warning(f"Pass 2 search failed: {e}, continuing with existing results")
            print(f"      Refined pass failed, continuing with existing results")
            new_results = []

        # Combine all results
        all_results = pass1_results + new_results
        print(f"      Total: {len(all_results)} unique sources")

        # Fetch pages — skip URLs that already have raw_content from Tavily
        prefetched, urls_to_fetch = self._split_prefetched(all_results)
        fetch_step = 2 + offset
        print(f"\n[{fetch_step}/{step_count}] Fetching {len(all_results)} pages...")
        pages = await fetch_urls(urls_to_fetch) if urls_to_fetch else []
        print(f"      Successfully fetched {len(pages)} pages ({len(prefetched)} from search cache)")

        if not pages and not prefetched:
            raise ResearchError("Could not fetch any pages")

        # Extract content
        extract_step = 3 + offset
        print(f"\n[{extract_step}/{step_count}] Extracting content...")
        extracted = extract_all(pages)
        contents = prefetched + extracted
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        # Summarize
        summarize_step = 4 + offset
        logger.info(f"Summarizing content with {self.summarize_model}...")
        print(f"\n[{summarize_step}/{step_count}] Summarizing content with {self.summarize_model}...")
        summaries = await summarize_all(
            self.async_client,
            contents,
            model=self.summarize_model,
        )
        print(f"      Generated {len(summaries)} summaries")

        if not summaries:
            raise ResearchError("Could not generate any summaries")

        # Relevance gate and synthesis
        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
            relevance_step=5 + offset,
            synthesis_step=6 + offset,
            step_count=step_count,
        )

    async def _research_deep(
        self, query: str, step_count: int, decomposition: dict | None = None
    ) -> str:
        """Deep mode: two-pass search with full fetch/summarize between passes."""
        offset = 1 if self.mode.decompose else 0

        # Search pass 1: always search the original query
        try:
            results = await asyncio.to_thread(
                search, query, self.mode.pass1_sources
            )
            print(f"      Found {len(results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        seen_urls = {r.url for r in results}

        # Sub-query searches (additive)
        if decomposition and decomposition["is_complex"]:
            sub_queries = decomposition["sub_queries"]
            per_sq_sources = max(2, self.mode.pass1_sources // (len(sub_queries) + 1))
            for sq in sub_queries:
                delay = SUB_QUERY_STAGGER_BASE + random.uniform(0, SUB_QUERY_STAGGER_JITTER)
                await asyncio.sleep(delay)
                try:
                    sq_results = await asyncio.to_thread(search, sq, per_sq_sources)
                    new = [r for r in sq_results if r.url not in seen_urls]
                    for r in new:
                        seen_urls.add(r.url)
                        results.append(r)
                    print(f"      → \"{sq}\": {len(sq_results)} results ({len(new)} new)")
                except SearchError as e:
                    logger.warning(f"Sub-query search failed: {e}, continuing")
                    print(f"      → \"{sq}\": failed, continuing")

        # Fetch pages (pass 1) — skip URLs with raw_content from Tavily
        prefetched, urls_to_fetch = self._split_prefetched(results)
        fetch_step = 2 + offset
        print(f"\n[{fetch_step}/{step_count}] Fetching {len(results)} pages...")
        pages = await fetch_urls(urls_to_fetch) if urls_to_fetch else []
        print(f"      Successfully fetched {len(pages)} pages ({len(prefetched)} from search cache)")

        if not pages and not prefetched:
            raise ResearchError("Could not fetch any pages")

        # Extract content (pass 1)
        extract_step = 3 + offset
        print(f"\n[{extract_step}/{step_count}] Extracting content...")
        extracted = extract_all(pages)
        contents = prefetched + extracted
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        # Summarize (pass 1)
        summarize_step = 4 + offset
        logger.info(f"Summarizing content with {self.summarize_model}...")
        print(f"\n[{summarize_step}/{step_count}] Summarizing content with {self.summarize_model}...")
        summaries = await summarize_all(
            self.async_client,
            contents,
            model=self.summarize_model,
        )
        print(f"      Generated {len(summaries)} summaries")

        if not summaries:
            raise ResearchError("Could not generate any summaries")

        # Deep mode refinement and pass 2
        refine_step = 5 + offset
        print(f"\n[{refine_step}/{step_count}] Deep mode: refining search...")

        summary_texts = [s.summary for s in summaries]
        refined_query = refine_query(self.client, query, summary_texts)
        if refined_query == query:
            print(f"      Query refinement skipped (using original query)")
        else:
            print(f"      Refined query: {refined_query}")

        delay = SEARCH_PASS_DELAY_BASE + random.uniform(0, SEARCH_PASS_DELAY_JITTER)
        await asyncio.sleep(delay)

        # Search pass 2
        try:
            pass2_results = await asyncio.to_thread(
                search, refined_query, self.mode.pass2_sources
            )
            new_results = [r for r in pass2_results if r.url not in seen_urls]
            print(f"      Pass 2 found {len(pass2_results)} results ({len(new_results)} new)")

            if new_results:
                new_prefetched, new_urls_to_fetch = self._split_prefetched(new_results)
                new_pages = await fetch_urls(new_urls_to_fetch) if new_urls_to_fetch else []
                print(f"      Fetched {len(new_pages)} new pages ({len(new_prefetched)} from search cache)")

                new_extracted = extract_all(new_pages)
                new_contents = new_prefetched + new_extracted
                if new_contents:
                    print(f"      Extracted {len(new_contents)} new contents")

                    if new_contents:
                        try:
                            new_summaries = await summarize_all(
                                self.async_client,
                                new_contents,
                                model=self.summarize_model,
                            )
                            summaries.extend(new_summaries)
                            print(f"      Total summaries: {len(summaries)}")
                        except Exception as e:
                            logger.warning(f"Pass 2 summarization failed: {e}, continuing with pass 1 results")
                            print(f"      Pass 2 summarization failed, continuing with {len(summaries)} summaries")
            else:
                print("      No new unique URLs from pass 2")

        except SearchError as e:
            logger.warning(f"Pass 2 search failed: {e}, continuing with pass 1 results")
            print(f"      Pass 2 search failed, continuing with {len(summaries)} summaries")

        # Relevance gate and synthesis
        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
            relevance_step=6 + offset,
            synthesis_step=7 + offset,
            step_count=step_count,
        )
