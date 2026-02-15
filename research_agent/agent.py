"""Main research agent orchestrating the full pipeline."""

import asyncio
import logging
import random
import time

from anthropic import Anthropic, AsyncAnthropic, APIError, RateLimitError, APIConnectionError, APITimeoutError

from .search import search, refine_query, SearchResult
from .fetch import fetch_urls
from .extract import extract_all, ExtractedContent
from .summarize import summarize_all
from .synthesize import synthesize_report, synthesize_draft, synthesize_final
from .relevance import evaluate_sources, generate_insufficient_data_response, RelevanceEvaluation
from .decompose import decompose_query, DecompositionResult
from .context import load_full_context, load_synthesis_context
from .skeptic import run_deep_skeptic_pass, run_skeptic_combined
from .cascade import cascade_recover
from .errors import ResearchError, SearchError, SkepticError
from .modes import ResearchMode

logger = logging.getLogger(__name__)

# Base delay between search passes to avoid rate limits (with jitter added)
SEARCH_PASS_DELAY_BASE = 1.0
SEARCH_PASS_DELAY_JITTER = 0.5

# Maximum concurrent sub-query searches (semaphore cap)
MAX_CONCURRENT_SUB_QUERIES = 2


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

    def __init__(
        self,
        api_key: str | None = None,
        max_sources: int | None = None,
        mode: ResearchMode | None = None,
    ):
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self._start_time = 0.0
        self._step_num = 0
        self._step_total = 0
        self.mode = mode or ResearchMode.standard()

    def _next_step(self, message: str) -> None:
        """Print next step header with auto-incrementing counter."""
        self._step_num += 1
        elapsed = time.monotonic() - self._start_time
        print(f"\n[{self._step_num}/{self._step_total}] {message} ({elapsed:.1f}s)")

    def research(self, query: str) -> str:
        """Perform research on a query and return a markdown report."""
        return asyncio.run(self._research_async(query))

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
        self._start_time = time.monotonic()
        self._step_num = 0
        is_deep = self.mode.name == "deep"

        # Calculate total steps:
        # Quick=6, Standard=9, Deep=10
        # +1 if decomposition step is shown (mode.decompose is True)
        if is_deep:
            base_steps = 9
        elif self.mode.name == "standard":
            base_steps = 8
        else:
            base_steps = 6
        self._step_total = base_steps + (1 if self.mode.decompose else 0)

        # Try query decomposition if mode supports it
        decomposition = None
        if self.mode.decompose:
            self._next_step("Analyzing query...")
            decomposition = await asyncio.to_thread(
                decompose_query, self.client, query, model=self.mode.model
            )
            if decomposition.is_complex:
                sub_queries = decomposition.sub_queries
                reasoning = decomposition.reasoning
                if reasoning:
                    print(f"      {reasoning}")
                print(f"      Decomposed into {len(sub_queries)} sub-queries:")
                for sq in sub_queries:
                    print(f"      → {sq}")
            else:
                print(f"      Simple query — skipping decomposition")

        self._next_step(f"Searching for: {query}")
        print(f"      Mode: {self.mode.name} ({self.mode.max_sources} sources, {self.mode.search_passes} passes)")

        if is_deep:
            return await self._research_deep(query, decomposition)
        else:
            return await self._research_with_refinement(query, decomposition)

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

    @staticmethod
    async def _search_sub_queries(
        sub_queries: list[str],
        per_sq_sources: int,
        seen_urls: set[str],
    ) -> list[SearchResult]:
        """Search sub-queries in parallel with bounded concurrency.

        Uses a semaphore to cap concurrent Tavily API calls, then deduplicates
        results against seen_urls after all searches complete.

        Returns new (unseen) results and updates seen_urls in place.
        """
        sem = asyncio.Semaphore(MAX_CONCURRENT_SUB_QUERIES)

        async def _search_one(sq: str) -> tuple[str, list[SearchResult]]:
            async with sem:
                try:
                    results = await asyncio.to_thread(search, sq, per_sq_sources)
                    return (sq, results)
                except SearchError as e:
                    logger.warning(f"Sub-query search failed: {e}, continuing")
                    return (sq, [])

        completed = await asyncio.gather(*[_search_one(sq) for sq in sub_queries])

        new_results = []
        for sq, sq_results in completed:
            if not sq_results:
                print(f"      \u2192 \"{sq}\": failed, continuing")
                continue
            new = [r for r in sq_results if r.url not in seen_urls]
            for r in new:
                seen_urls.add(r.url)
            new_results.extend(new)
            print(f"      \u2192 \"{sq}\": {len(sq_results)} results ({len(new)} new)")

        return new_results

    @staticmethod
    async def _recover_failed_urls(
        urls_to_fetch: list[str],
        extracted: list[ExtractedContent],
        all_results: list[SearchResult],
    ) -> list[ExtractedContent]:
        """Run cascade fallback on URLs that failed fetch+extract."""
        extracted_urls = {e.url for e in extracted}
        failed = [u for u in urls_to_fetch if u not in extracted_urls]
        if not failed:
            return []
        recovered = await cascade_recover(failed, all_results)
        if recovered:
            cascade_count = sum(
                1 for r in recovered if not r.text.startswith("[Source:")
            )
            snippet_count = sum(
                1 for r in recovered if r.text.startswith("[Source:")
            )
            parts = []
            if cascade_count:
                parts.append(f"{cascade_count} via cascade")
            if snippet_count:
                parts.append(f"{snippet_count} snippet fallbacks")
            print(f"      Cascade recovered: {', '.join(parts)}")
        return recovered

    async def _fetch_extract_summarize(
        self,
        results: list[SearchResult],
        structured: bool = False,
        max_chunks: int = 3,
        quiet: bool = False,
    ) -> list:
        """Shared pipeline: split prefetched, fetch, extract, cascade, summarize.

        Args:
            quiet: If True, suppress step headers (used by deep mode pass 2).
        """
        prefetched, urls_to_fetch = self._split_prefetched(results)
        if not quiet:
            self._next_step(f"Fetching {len(results)} pages...")
        pages = await fetch_urls(urls_to_fetch) if urls_to_fetch else []
        print(f"      Successfully fetched {len(pages)} pages ({len(prefetched)} from search cache)")

        if not pages and not prefetched:
            raise ResearchError("Could not fetch any pages")

        if not quiet:
            self._next_step("Extracting content...")
        extracted = extract_all(pages)

        cascade_contents = await self._recover_failed_urls(
            urls_to_fetch, extracted, results
        )
        all_contents = prefetched + extracted + cascade_contents
        seen_content_urls: set[str] = set()
        contents = []
        for c in all_contents:
            if c.url not in seen_content_urls:
                seen_content_urls.add(c.url)
                contents.append(c)
        if len(contents) < len(all_contents):
            print(f"      Deduplicated: {len(all_contents)} → {len(contents)} unique pages")
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        logger.info(f"Summarizing content with {self.mode.model}...")
        if not quiet:
            self._next_step(f"Summarizing content with {self.mode.model}...")
        summaries = await summarize_all(
            self.async_client,
            contents,
            model=self.mode.model,
            structured=structured,
            max_chunks=max_chunks,
        )
        print(f"      Generated {len(summaries)} summaries")

        if not summaries:
            raise ResearchError("Could not generate any summaries")

        return summaries

    async def _evaluate_and_synthesize(
        self,
        query: str,
        summaries: list,
        refined_query: str,
    ) -> str:
        """Evaluate source relevance and synthesize report."""
        self._next_step("Evaluating source relevance...")
        evaluation = await evaluate_sources(
            query=query,
            summaries=summaries,
            mode=self.mode,
            client=self.async_client,
            refined_query=refined_query,
        )

        # Branch based on relevance gate decision
        if evaluation.decision == "insufficient_data":
            self._next_step("Generating insufficient data response...")
            return await generate_insufficient_data_response(
                query=query,
                refined_query=evaluation.refined_query,
                dropped_sources=evaluation.dropped_sources,
                client=self.async_client,
                model=self.mode.model,
            )

        # Synthesize report (full or short)
        logger.info(f"Synthesizing report with {self.mode.model}...")
        limited_sources = evaluation.decision == "short_report"
        surviving = evaluation.surviving_sources
        dropped_count = len(evaluation.dropped_sources)
        total_count = evaluation.total_scored

        # Quick mode: single-pass synthesis (no skeptic)
        if self.mode.name == "quick":
            label = "short report" if limited_sources else "report"
            self._next_step(f"Synthesizing {label} with {self.mode.model}...")
            print()  # blank line before streaming

            business_context = load_full_context()
            return synthesize_report(
                self.client, query, surviving,
                model=self.mode.model,
                max_tokens=self.mode.max_tokens,
                mode_instructions=self.mode.synthesis_instructions,
                limited_sources=limited_sources,
                dropped_count=dropped_count,
                total_count=total_count,
                business_context=business_context,
            )

        # Standard/deep mode: draft → skeptic → final synthesis
        is_deep = self.mode.name == "deep"

        self._next_step("Generating draft analysis...")
        print()  # blank line before streaming
        draft = await asyncio.to_thread(
            synthesize_draft, self.client, query, surviving,
            model=self.mode.model,
        )

        self._next_step("Running skeptic review...")
        synthesis_context = load_synthesis_context()

        try:
            if is_deep:
                findings = await asyncio.to_thread(
                    run_deep_skeptic_pass,
                    self.client, draft, synthesis_context,
                    model=self.mode.model,
                )
                total_critical = sum(f.critical_count for f in findings)
                total_concern = sum(f.concern_count for f in findings)
                print(f"      3 skeptic passes complete ({total_critical} critical, {total_concern} concerns)")
            else:
                finding = await asyncio.to_thread(
                    run_skeptic_combined,
                    self.client, draft, synthesis_context,
                    model=self.mode.model,
                )
                findings = [finding]
                print(f"      Combined skeptic pass complete ({finding.critical_count} critical, {finding.concern_count} concerns)")
        except SkepticError as e:
            logger.warning(f"Skeptic review failed: {e}, continuing without it")
            print(f"      Skeptic review failed, continuing with standard synthesis")
            findings = []

        self._next_step(f"Synthesizing final report with {self.mode.model}...")
        print()  # blank line before streaming

        return await asyncio.to_thread(
            synthesize_final,
            self.client, query, draft, findings, surviving,
            model=self.mode.model,
            max_tokens=self.mode.max_tokens,
            business_context=synthesis_context,
            limited_sources=limited_sources,
            dropped_count=dropped_count,
            total_count=total_count,
            is_deep=is_deep,
        )

    async def _research_with_refinement(
        self, query: str, decomposition: DecompositionResult | None = None
    ) -> str:
        """Quick/standard mode: refine query using snippets before fetching."""
        # Search pass 1
        print(f"      Original query: {query}")
        try:
            pass1_results = await asyncio.to_thread(
                search, query, self.mode.pass1_sources
            )
            print(f"      Pass 1 found {len(pass1_results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        seen_urls = {r.url for r in pass1_results}

        # Sub-query searches (additive)
        if decomposition and decomposition.is_complex:
            sub_queries = decomposition.sub_queries
            per_sq_sources = max(2, self.mode.pass2_sources // len(sub_queries))
            new_from_subs = await self._search_sub_queries(
                sub_queries, per_sq_sources, seen_urls
            )
            pass1_results.extend(new_from_subs)

        # Refine query using snippets
        snippets = [r.snippet for r in pass1_results if r.snippet]
        refined_query = await asyncio.to_thread(
            refine_query, self.client, query, snippets, model=self.mode.model
        )
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

        all_results = pass1_results + new_results
        print(f"      Total: {len(all_results)} unique sources")

        # Fetch → extract → cascade → summarize
        summaries = await self._fetch_extract_summarize(all_results)

        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
        )

    async def _research_deep(
        self, query: str, decomposition: DecompositionResult | None = None
    ) -> str:
        """Deep mode: two-pass search with full fetch/summarize between passes."""
        # Search pass 1
        try:
            results = await asyncio.to_thread(
                search, query, self.mode.pass1_sources
            )
            print(f"      Found {len(results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        seen_urls = {r.url for r in results}

        # Sub-query searches (additive)
        if decomposition and decomposition.is_complex:
            sub_queries = decomposition.sub_queries
            per_sq_sources = max(2, self.mode.pass1_sources // (len(sub_queries) + 1))
            new_from_subs = await self._search_sub_queries(
                sub_queries, per_sq_sources, seen_urls
            )
            results.extend(new_from_subs)

        # Pass 1: fetch → extract → cascade → summarize
        summaries = await self._fetch_extract_summarize(
            results, structured=True, max_chunks=5
        )

        # Deep mode refinement and pass 2
        self._next_step("Deep mode: refining search...")

        summary_texts = [s.summary for s in summaries]
        refined_query = await asyncio.to_thread(
            refine_query, self.client, query, summary_texts, model=self.mode.model
        )
        if refined_query == query:
            print(f"      Query refinement skipped (using original query)")
        else:
            print(f"      Refined query: {refined_query}")

        delay = SEARCH_PASS_DELAY_BASE + random.uniform(0, SEARCH_PASS_DELAY_JITTER)
        await asyncio.sleep(delay)

        # Search pass 2 (reuses shared pipeline in quiet mode)
        try:
            pass2_results = await asyncio.to_thread(
                search, refined_query, self.mode.pass2_sources
            )
            new_results = [r for r in pass2_results if r.url not in seen_urls]
            print(f"      Pass 2 found {len(pass2_results)} results ({len(new_results)} new)")

            if new_results:
                try:
                    new_summaries = await self._fetch_extract_summarize(
                        new_results, structured=True, max_chunks=5, quiet=True,
                    )
                    summaries.extend(new_summaries)
                    print(f"      Total summaries: {len(summaries)}")
                except (ResearchError, APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
                    logger.warning(f"Pass 2 processing failed: {e}, continuing with pass 1 results")
                    print(f"      Pass 2 failed, continuing with {len(summaries)} summaries")
            else:
                print("      No new unique URLs from pass 2")

        except SearchError as e:
            logger.warning(f"Pass 2 search failed: {e}, continuing with pass 1 results")
            print(f"      Pass 2 search failed, continuing with {len(summaries)} summaries")

        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
        )
