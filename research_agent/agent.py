"""Main research agent orchestrating the full pipeline."""

import asyncio
import logging
import time

from anthropic import Anthropic, AsyncAnthropic

from .search import search, refine_query
from .fetch import fetch_urls
from .extract import extract_all
from .summarize import summarize_all
from .synthesize import synthesize_report
from .errors import ResearchError, SearchError
from .modes import ResearchMode

logger = logging.getLogger(__name__)


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
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.mode = mode or ResearchMode.standard()
        # Use explicit max_sources if provided, otherwise use mode's default
        self.max_sources = max_sources if max_sources is not None else self.mode.max_sources
        self.summarize_model = summarize_model
        self.synthesize_model = synthesize_model

    def research(self, query: str) -> str:
        """
        Perform research on a query and return a markdown report.

        Args:
            query: The research question

        Returns:
            Markdown report string

        Raises:
            ResearchError: If research fails
        """
        return asyncio.run(self._research_async(query))

    async def _research_async(self, query: str) -> str:
        """Async implementation of research."""
        is_deep = self.mode.name == "deep"

        # Deep mode: 6 steps (fetch/summarize between passes)
        # Quick/standard: 5 steps (refine before fetch, then fetch all at once)
        step_count = 6 if is_deep else 5

        print(f"\n[1/{step_count}] Searching for: {query}")
        print(f"      Mode: {self.mode.name} ({self.mode.max_sources} sources, {self.mode.search_passes} passes)")

        if is_deep:
            # === DEEP MODE: Original two-pass with fetch between passes ===
            return await self._research_deep(query, step_count)
        else:
            # === QUICK/STANDARD: Refine using snippets, then fetch all ===
            return await self._research_with_refinement(query, step_count)

    async def _research_with_refinement(self, query: str, step_count: int) -> str:
        """Quick/standard mode: refine query using snippets before fetching."""

        # Step 1a: Search pass 1
        print(f"      Original query: {query}")
        try:
            pass1_results = search(query, max_results=self.mode.pass1_sources)
            print(f"      Pass 1 found {len(pass1_results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        # Step 1b: Refine query using snippets
        snippets = [r.snippet for r in pass1_results if r.snippet]
        refined_query = refine_query(self.client, query, snippets)
        print(f"      Refined query: {refined_query}")

        # Step 1c: Search pass 2
        time.sleep(1)  # Brief delay to avoid rate limits
        try:
            pass2_results = search(refined_query, max_results=self.mode.pass2_sources)
            # Deduplicate by URL
            seen_urls = {r.url for r in pass1_results}
            new_results = [r for r in pass2_results if r.url not in seen_urls]
            print(f"      Pass 2 found {len(pass2_results)} results ({len(new_results)} new)")
        except SearchError as e:
            logger.warning(f"Pass 2 search failed: {e}, continuing with pass 1 results")
            print(f"      Pass 2 failed, continuing with pass 1 results")
            new_results = []

        # Combine all results
        all_results = pass1_results + new_results
        print(f"      Total: {len(all_results)} unique sources")

        # Step 2: Fetch pages
        print(f"\n[2/{step_count}] Fetching {len(all_results)} pages...")
        urls = [r.url for r in all_results]
        pages = await fetch_urls(urls)
        print(f"      Successfully fetched {len(pages)} pages")

        if not pages:
            raise ResearchError("Could not fetch any pages")

        # Step 3: Extract content
        print(f"\n[3/{step_count}] Extracting content...")
        contents = extract_all(pages)
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        # Step 4: Summarize
        logger.info(f"Summarizing content with {self.summarize_model}...")
        print(f"\n[4/{step_count}] Summarizing content with {self.summarize_model}...")
        summaries = await summarize_all(
            self.async_client,
            contents,
            model=self.summarize_model,
        )
        print(f"      Generated {len(summaries)} summaries")

        if not summaries:
            raise ResearchError("Could not generate any summaries")

        # Step 5: Synthesize report
        logger.info(f"Synthesizing report with {self.synthesize_model}...")
        print(f"\n[5/{step_count}] Synthesizing report with {self.synthesize_model}...\n")
        report = synthesize_report(
            self.client,
            query,
            summaries,
            model=self.synthesize_model,
            max_tokens=self.mode.max_tokens,
            mode_instructions=self.mode.synthesis_instructions,
        )

        return report

    async def _research_deep(self, query: str, step_count: int) -> str:
        """Deep mode: two-pass search with full fetch/summarize between passes."""

        # Step 1: Search (pass 1)
        try:
            results = search(query, max_results=self.mode.pass1_sources)
            print(f"      Found {len(results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        # Step 2: Fetch pages (pass 1)
        print(f"\n[2/{step_count}] Fetching {len(results)} pages...")
        urls = [r.url for r in results]
        seen_urls = set(urls)
        pages = await fetch_urls(urls)
        print(f"      Successfully fetched {len(pages)} pages")

        if not pages:
            raise ResearchError("Could not fetch any pages")

        # Step 3: Extract content (pass 1)
        print(f"\n[3/{step_count}] Extracting content...")
        contents = extract_all(pages)
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        # Step 4: Summarize (pass 1)
        logger.info(f"Summarizing content with {self.summarize_model}...")
        print(f"\n[4/{step_count}] Summarizing content with {self.summarize_model}...")
        summaries = await summarize_all(
            self.async_client,
            contents,
            model=self.summarize_model,
        )
        print(f"      Generated {len(summaries)} summaries")

        if not summaries:
            raise ResearchError("Could not generate any summaries")

        # Step 5: Deep mode refinement and pass 2
        print(f"\n[5/{step_count}] Deep mode: refining search...")

        # Generate refined query from summaries
        summary_texts = [s.summary for s in summaries]
        refined_query = refine_query(self.client, query, summary_texts)
        print(f"      Refined query: {refined_query}")

        # Brief delay to avoid rate limits
        time.sleep(1)

        # Search pass 2
        try:
            pass2_results = search(refined_query, max_results=self.mode.pass2_sources)
            # Deduplicate by URL
            new_results = [r for r in pass2_results if r.url not in seen_urls]
            print(f"      Pass 2 found {len(pass2_results)} results ({len(new_results)} new)")

            if new_results:
                # Fetch, extract, summarize new URLs
                new_urls = [r.url for r in new_results]
                new_pages = await fetch_urls(new_urls)
                print(f"      Fetched {len(new_pages)} new pages")

                if new_pages:
                    new_contents = extract_all(new_pages)
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

        # Step 6: Synthesize report
        logger.info(f"Synthesizing report with {self.synthesize_model}...")
        print(f"\n[6/{step_count}] Synthesizing report with {self.synthesize_model}...\n")
        report = synthesize_report(
            self.client,
            query,
            summaries,
            model=self.synthesize_model,
            max_tokens=self.mode.max_tokens,
            mode_instructions=self.mode.synthesis_instructions,
        )

        return report
