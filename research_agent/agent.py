"""Main research agent orchestrating the full pipeline."""

import asyncio
import logging

from anthropic import Anthropic, AsyncAnthropic

from .search import search
from .fetch import fetch_urls
from .extract import extract_all
from .summarize import summarize_all
from .synthesize import synthesize_report
from .errors import ResearchError, SearchError

logger = logging.getLogger(__name__)


class ResearchAgent:
    """
    A research agent that searches the web and generates markdown reports.

    Usage:
        agent = ResearchAgent(api_key="your-key")
        report = agent.research("What are Python async best practices?")
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_sources: int = 5,
        summarize_model: str = "claude-sonnet-4-20250514",
        synthesize_model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the research agent.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            max_sources: Maximum number of sources to research
            summarize_model: Model for chunk summarization
            synthesize_model: Model for report synthesis
        """
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.max_sources = max_sources
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
        print(f"\n[1/5] Searching for: {query}")

        # Step 1: Search
        try:
            results = search(query, max_results=self.max_sources)
            print(f"      Found {len(results)} results")
        except SearchError as e:
            raise ResearchError(f"Search failed: {e}")

        # Step 2: Fetch pages
        print(f"\n[2/5] Fetching {len(results)} pages...")
        urls = [r.url for r in results]
        pages = await fetch_urls(urls)
        print(f"      Successfully fetched {len(pages)} pages")

        if not pages:
            raise ResearchError("Could not fetch any pages")

        # Step 3: Extract content
        print(f"\n[3/5] Extracting content...")
        contents = extract_all(pages)
        print(f"      Extracted content from {len(contents)} pages")

        if not contents:
            raise ResearchError("Could not extract content from any pages")

        # Step 4: Summarize
        logger.info(f"Summarizing content with {self.summarize_model}...")
        print(f"\n[4/5] Summarizing content with {self.summarize_model}...")
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
        print(f"\n[5/5] Synthesizing report with {self.synthesize_model}...\n")
        report = synthesize_report(
            self.client,
            query,
            summaries,
            model=self.synthesize_model,
        )

        return report
