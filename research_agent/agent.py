"""Main research agent orchestrating the full pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import yaml

from anthropic import Anthropic, AsyncAnthropic, APIError, RateLimitError, APIConnectionError, APITimeoutError

from .search import search, refine_query, SearchResult
from .fetch import fetch_urls
from .extract import extract_all, ExtractedContent
from .summarize import summarize_all, Summary
from .synthesize import synthesize_report, synthesize_draft, synthesize_final
from .relevance import evaluate_sources, generate_insufficient_data_response, RelevanceEvaluation, SourceScore
from .decompose import decompose_query, DecompositionResult
from .context import load_full_context, load_synthesis_context, load_critique_history, clear_context_cache
from .skeptic import run_deep_skeptic_pass, run_skeptic_combined
from .cascade import cascade_recover
from .coverage import identify_coverage_gaps
from .errors import ResearchError, SearchError, SkepticError, StateError
from .critique import evaluate_report, save_critique, CritiqueResult
from .modes import ResearchMode
from .cycle_config import CycleConfig

from .schema import Gap, GapStatus, SchemaResult, load_schema
from .state import mark_verified, mark_checked, save_schema
from .staleness import detect_stale, select_batch, log_flip

logger = logging.getLogger(__name__)

# Maximum concurrent sub-query searches (semaphore cap)
MAX_CONCURRENT_SUB_QUERIES = 2

# Default directory for critique metadata files
META_DIR = Path("reports/meta")


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
        cycle_config: CycleConfig | None = None,
        schema_path: Path | str | None = None,
        skip_critique: bool = False,
    ):
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self._start_time = 0.0
        self._step_num = 0
        self._step_total = 0
        self.mode = mode or ResearchMode.standard()
        self.cycle_config = cycle_config or CycleConfig()
        self.skip_critique = skip_critique
        self.schema_path = Path(schema_path) if schema_path else None
        self._current_schema_result: SchemaResult | None = None
        self._current_research_batch: tuple[Gap, ...] | None = None
        self._last_source_count: int = 0
        self._last_gate_decision: str = ""
        self._last_critique: CritiqueResult | None = None

    @property
    def last_critique(self) -> CritiqueResult | None:
        """Most recent self-critique result, or None if not run."""
        return self._last_critique

    def _already_covered_response(self, schema_result: SchemaResult) -> str:
        """Generate a response when all gaps are verified and fresh."""
        gap_count = len(schema_result.gaps)
        return (
            f"# All Intelligence Current\n\n"
            f"All {gap_count} gaps in the schema are verified and within their "
            f"freshness windows. No new research needed at this time.\n\n"
            f"Run with `--force` to research anyway, or wait for gaps to become stale."
        )

    def _update_gap_states(self, decision: str) -> None:
        """Update gap schema after research completes.

        - full_report / short_report -> mark_verified() for researched gaps
        - no_new_findings -> mark_checked() (searched but found nothing)
        - insufficient_data -> no state update (search itself failed)
        """
        schema_result = self._current_schema_result
        if not schema_result or self._current_research_batch is None:
            return

        batch_ids = {g.id for g in self._current_research_batch}
        updated_gaps: list[Gap] = []
        audit_log_path = self.schema_path.parent / "gap_audit.log"

        for gap in schema_result.gaps:
            if gap.id not in batch_ids:
                updated_gaps.append(gap)
                continue

            if decision in ("full_report", "short_report"):
                new_gap = mark_verified(gap)
                if gap.status != new_gap.status:
                    log_flip(
                        audit_log_path, gap.id,
                        gap.status, new_gap.status,
                        reason=f"Research completed: {decision}",
                    )
                updated_gaps.append(new_gap)
            elif decision == "no_new_findings":
                new_gap = mark_checked(gap)
                updated_gaps.append(new_gap)
                logger.info("Gap '%s' checked (no new findings)", gap.id)
            else:
                # insufficient_data -- don't update state
                updated_gaps.append(gap)

        try:
            save_schema(self.schema_path, tuple(updated_gaps))
            logger.info("Updated %d gap states in %s", len(batch_ids), self.schema_path)
        except StateError as e:
            logger.warning("Failed to save gap state: %s", e)

    def _run_critique(
        self,
        query: str,
        surviving_count: int,
        dropped_count: int,
        skeptic_findings: list | None,
        gate_decision: str,
    ) -> None:
        """Run self-critique after report synthesis. Never crashes pipeline."""
        if self.mode.is_quick or self.skip_critique:
            return  # Quick mode has no skeptic data; --no-critique opts out

        try:
            result = evaluate_report(
                client=self.client,
                query=query,
                mode_name=self.mode.name,
                surviving_sources=surviving_count,
                dropped_sources=dropped_count,
                skeptic_findings=skeptic_findings,
                gate_decision=gate_decision,
                model=self.mode.model,
            )
            save_critique(result, META_DIR)
            self._last_critique = result
            logger.info(
                "Self-critique: mean=%.1f pass=%s", result.mean_score, result.overall_pass
            )
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Self-critique failed: %s", e)

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
        self._current_schema_result = None
        self._current_research_batch = None
        self._last_source_count = 0
        self._last_gate_decision = ""
        clear_context_cache()
        critique_context: str | None = None
        if not self.mode.is_quick:
            critique_ctx = await asyncio.to_thread(load_critique_history, META_DIR)
            if critique_ctx:
                critique_context = critique_ctx.content
                logger.info("Loaded critique history for adaptive prompts")

        # Calculate total steps:
        # Quick=6, Standard=9, Deep=10
        # +1 if decomposition step is shown (mode.decompose is True)
        if self.mode.is_deep:
            base_steps = 9
        elif self.mode.is_standard:
            base_steps = 8
        else:
            base_steps = 6
        self._step_total = base_steps + (1 if self.mode.decompose else 0)

        # Try query decomposition if mode supports it
        decomposition = None
        if self.mode.decompose:
            self._next_step("Analyzing query...")
            decomposition = await asyncio.to_thread(
                decompose_query, self.client, query, model=self.mode.model,
                critique_guidance=critique_context,
            )
            if decomposition.is_complex:
                sub_queries = decomposition.sub_queries
                reasoning = decomposition.reasoning
                if reasoning:
                    print(f"      {reasoning}")
                print(f"      Decomposed into {len(sub_queries)} sub-queries:")
                for sq in sub_queries:
                    print(f"      \u2192 {sq}")
            else:
                print(f"      Simple query \u2014 skipping decomposition")

        # Pre-research gap check (if schema configured)
        if self.schema_path:
            schema_result = load_schema(self.schema_path)
            if schema_result.is_loaded:
                stale = detect_stale(
                    schema_result.gaps,
                    default_ttl_days=self.cycle_config.default_ttl_days,
                )
                stale_ids = {g.id for g in stale}
                candidates = tuple(
                    g for g in schema_result.gaps
                    if g.id in stale_ids or g.status == GapStatus.UNKNOWN
                )
                if not candidates:
                    return self._already_covered_response(schema_result)
                research_batch = select_batch(candidates, self.cycle_config.max_gaps_per_run)
                unknown_count = sum(1 for g in candidates if g.status == GapStatus.UNKNOWN)
                print(f"      Gap schema: {len(research_batch)} gaps to research "
                      f"({len(stale)} stale, {unknown_count} unknown)")
                self._current_schema_result = schema_result
                self._current_research_batch = research_batch

        self._next_step(f"Searching for: {query}")
        print(f"      Mode: {self.mode.name} ({self.mode.max_sources} sources, {self.mode.search_passes} passes)")

        if self.mode.is_deep:
            return await self._research_deep(query, decomposition, critique_context)
        else:
            return await self._research_with_refinement(query, decomposition, critique_context)

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

    async def _fetch_extract_summarize(
        self,
        results: list[SearchResult],
        structured: bool = False,
        max_chunks: int = 3,
        quiet: bool = False,
    ) -> list[Summary]:
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

        # Determine URLs that failed fetching (distinct from extraction failures)
        fetched_page_urls = {p.url for p in pages}
        fetch_failed = [u for u in urls_to_fetch if u not in fetched_page_urls]

        # Run extraction and cascade for fetch-failed URLs concurrently
        if fetch_failed:
            extracted, cascade_from_fetch = await asyncio.gather(
                asyncio.to_thread(extract_all, pages),
                cascade_recover(fetch_failed, results),
            )
        else:
            extracted = await asyncio.to_thread(extract_all, pages)
            cascade_from_fetch = []

        # Second pass: cascade for URLs that fetched OK but extraction failed
        extracted_urls = {e.url for e in extracted}
        extract_failed = [u for u in fetched_page_urls if u not in extracted_urls]
        if extract_failed:
            cascade_from_extract = await cascade_recover(extract_failed, results)
        else:
            cascade_from_extract = []

        cascade_contents = list(cascade_from_fetch) + list(cascade_from_extract)
        if cascade_contents:
            full_count = sum(1 for r in cascade_contents if not r.text.startswith("[Source:"))
            snippet_count = sum(1 for r in cascade_contents if r.text.startswith("[Source:"))
            parts = []
            if full_count:
                parts.append(f"{full_count} via cascade")
            if snippet_count:
                parts.append(f"{snippet_count} snippet fallbacks")
            print(f"      Cascade recovered: {', '.join(parts)}")

        all_contents = prefetched + extracted + cascade_contents
        seen_content_urls: set[str] = set()
        contents = []
        for c in all_contents:
            if c.url not in seen_content_urls:
                seen_content_urls.add(c.url)
                contents.append(c)
        if len(contents) < len(all_contents):
            print(f"      Deduplicated: {len(all_contents)} \u2192 {len(contents)} unique pages")
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

    async def _try_coverage_retry(
        self,
        query: str,
        existing_summaries: list[Summary],
        evaluation: RelevanceEvaluation,
        tried_queries: list[str],
        critique_context: str | None = None,
    ) -> tuple[list[Summary], RelevanceEvaluation] | None:
        """Attempt one coverage gap retry when relevance gate under-delivers.

        Calls identify_coverage_gaps() to diagnose why results are thin,
        then searches with any RETRY queries and re-evaluates.

        Returns:
            (combined_summaries, new_evaluation) if retry improved results,
            None if retry was skipped or found nothing new.
        """
        gap = await identify_coverage_gaps(
            query=query,
            summaries=list(evaluation.surviving_sources),
            tried_queries=tried_queries,
            client=self.async_client,
            model=self.mode.model,
        )

        logger.info(
            "Coverage gap: %s (%s) \u2014 %s",
            gap.gap_type, gap.description, gap.retry_recommendation,
        )
        print(f"      Coverage gap: {gap.gap_type} \u2014 {gap.retry_recommendation}")

        if gap.retry_recommendation != "RETRY" or not gap.retry_queries:
            if gap.retry_recommendation == "MAYBE_RETRY":
                print(f"      Skipping retry (conservative \u2014 MAYBE_RETRY)")
            return None

        print(f"      Retrying with {len(gap.retry_queries)} new queries:")
        for rq in gap.retry_queries:
            print(f"        \u2192 {rq}")

        # Search retry queries in parallel (reuses _search_sub_queries)
        seen_urls = {s.url for s in existing_summaries}
        retry_results = await self._search_sub_queries(
            gap.retry_queries, self.mode.retry_sources_per_query, seen_urls,
        )

        if not retry_results:
            print(f"      No new results from retry queries")
            return None

        # Fetch, extract, summarize new results (quiet -- no step headers)
        try:
            new_summaries = await self._fetch_extract_summarize(
                retry_results, quiet=True,
            )
        except ResearchError as e:
            logger.warning("Retry fetch/summarize failed: %s", e)
            return None

        # Score ONLY new summaries (preserve existing scores)
        combined = existing_summaries + new_summaries
        print(f"      Retry added {len(new_summaries)} summaries (total: {len(combined)})")

        retry_eval = await evaluate_sources(
            query=query,
            summaries=new_summaries,
            mode=self.mode,
            client=self.async_client,
            refined_query=evaluation.refined_query,
            critique_guidance=critique_context,
        )

        # Merge surviving/dropped from original + retry evaluations
        merged_surviving = evaluation.surviving_sources + retry_eval.surviving_sources
        merged_dropped = evaluation.dropped_sources + retry_eval.dropped_sources
        total_scored = evaluation.total_scored + retry_eval.total_scored
        total_survived = evaluation.total_survived + retry_eval.total_survived

        # Determine combined decision using mode thresholds
        mode = self.mode
        if total_survived >= mode.min_sources_full_report:
            decision = "full_report"
            rationale = f"{total_survived}/{total_scored} sources passed after retry merge"
        elif total_survived >= mode.min_sources_short_report:
            decision = "short_report"
            rationale = f"{total_survived}/{total_scored} sources passed after retry merge (below full threshold)"
        elif total_scored > 0 and total_survived == 0:
            decision = "no_new_findings"
            rationale = f"All {total_scored} sources below cutoff after retry"
        else:
            decision = "insufficient_data"
            rationale = f"Only {total_survived}/{total_scored} sources passed after retry"

        print(f"      Merged decision: {decision} ({total_survived}/{total_scored} sources passed)")

        merged_eval = RelevanceEvaluation(
            decision=decision,
            decision_rationale=rationale,
            surviving_sources=merged_surviving,
            dropped_sources=merged_dropped,
            total_scored=total_scored,
            total_survived=total_survived,
            refined_query=evaluation.refined_query,
        )

        return combined, merged_eval

    async def _evaluate_and_synthesize(
        self,
        query: str,
        summaries: list[Summary],
        refined_query: str,
        critique_context: str | None = None,
        tried_queries: list[str] | None = None,
    ) -> str:
        """Evaluate source relevance and synthesize report."""
        self._next_step("Evaluating source relevance...")
        evaluation = await evaluate_sources(
            query=query,
            summaries=summaries,
            mode=self.mode,
            client=self.async_client,
            refined_query=refined_query,
            critique_guidance=critique_context,
        )

        # Coverage gap retry for insufficient_data or short_report
        if not self.mode.is_quick and evaluation.decision in ("insufficient_data", "short_report"):
            retry_result = await self._try_coverage_retry(
                query, summaries, evaluation,
                tried_queries or [],
                critique_context=critique_context,
            )
            if retry_result is not None:
                summaries, evaluation = retry_result

        # Branch based on relevance gate decision
        if evaluation.decision in ("insufficient_data", "no_new_findings"):
            self._last_source_count = 0
            self._last_gate_decision = evaluation.decision
            if evaluation.decision == "no_new_findings" and self.schema_path and self._current_research_batch:
                self._update_gap_states("no_new_findings")
            self._next_step("Generating insufficient data response...")
            return await generate_insufficient_data_response(
                query=query,
                refined_query=evaluation.refined_query,
                dropped_sources=evaluation.dropped_sources,
                client=self.async_client,
                model=self.mode.model,
            )

        # Synthesize report (full or short)
        self._last_source_count = len(evaluation.surviving_sources)
        self._last_gate_decision = evaluation.decision
        logger.info(f"Synthesizing report with {self.mode.model}...")
        limited_sources = evaluation.decision == "short_report"
        surviving = evaluation.surviving_sources
        dropped_count = len(evaluation.dropped_sources)
        total_count = evaluation.total_scored

        # Quick mode: single-pass synthesis (no skeptic)
        if self.mode.is_quick:
            label = "short report" if limited_sources else "report"
            self._next_step(f"Synthesizing {label} with {self.mode.model}...")
            print()  # blank line before streaming

            ctx_result = load_full_context()
            business_context = ctx_result.content
            report = synthesize_report(
                self.client, query, surviving,
                model=self.mode.model,
                max_tokens=self.mode.max_tokens,
                mode_instructions=self.mode.synthesis_instructions,
                limited_sources=limited_sources,
                dropped_count=dropped_count,
                total_count=total_count,
                business_context=business_context,
            )
            if self.schema_path and self._current_research_batch:
                self._update_gap_states(evaluation.decision)
            return report

        # Standard/deep mode: draft -> skeptic -> final synthesis
        # Check for business context early so draft uses the right template
        synth_result = load_synthesis_context()
        synthesis_context = synth_result.content

        self._next_step("Generating draft analysis...")
        print()  # blank line before streaming
        draft = await asyncio.to_thread(
            synthesize_draft, self.client, query, surviving,
            model=self.mode.model,
            has_business_context=bool(synthesis_context),
        )

        self._next_step("Running skeptic review...")

        try:
            if self.mode.is_deep:
                findings = await run_deep_skeptic_pass(
                    self.async_client, draft, synthesis_context,
                    model=self.mode.model,
                )
                total_critical = sum(f.critical_count for f in findings)
                total_concern = sum(f.concern_count for f in findings)
                print(f"      3 skeptic passes complete ({total_critical} critical, {total_concern} concerns)")
            else:
                finding = await run_skeptic_combined(
                    self.async_client, draft, synthesis_context,
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

        result = await asyncio.to_thread(
            synthesize_final,
            self.client, query, draft, findings, surviving,
            model=self.mode.model,
            max_tokens=self.mode.max_tokens,
            business_context=synthesis_context,
            limited_sources=limited_sources,
            dropped_count=dropped_count,
            total_count=total_count,
            is_deep=self.mode.is_deep,
            critique_guidance=critique_context,
        )
        await asyncio.to_thread(
            self._run_critique,
            query=query,
            surviving_count=len(surviving),
            dropped_count=dropped_count,
            skeptic_findings=findings,
            gate_decision=evaluation.decision,
        )
        if self.schema_path and self._current_research_batch:
            self._update_gap_states(evaluation.decision)
        return result

    async def _research_with_refinement(
        self, query: str, decomposition: DecompositionResult | None = None,
        critique_context: str | None = None,
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

        # Fetch -> extract -> cascade -> summarize
        summaries = await self._fetch_extract_summarize(all_results)

        # Build tried_queries list for coverage gap analysis
        tried = [query]
        if refined_query != query:
            tried.append(refined_query)
        if decomposition and decomposition.is_complex:
            tried.extend(decomposition.sub_queries)

        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
            critique_context=critique_context,
            tried_queries=tried,
        )

    async def _research_deep(
        self, query: str, decomposition: DecompositionResult | None = None,
        critique_context: str | None = None,
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

        # Pass 1: fetch -> extract -> cascade -> summarize
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

        # Build tried_queries list for coverage gap analysis
        tried = [query]
        if refined_query != query:
            tried.append(refined_query)
        if decomposition and decomposition.is_complex:
            tried.extend(decomposition.sub_queries)

        return await self._evaluate_and_synthesize(
            query=query,
            summaries=summaries,
            refined_query=refined_query,
            critique_context=critique_context,
            tried_queries=tried,
        )
