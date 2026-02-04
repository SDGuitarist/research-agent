"""Search functionality with DuckDuckGo and fallback support."""

import logging
import time
from dataclasses import dataclass

from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

from .errors import SearchError

logger = logging.getLogger(__name__)

# Model for query refinement (using Sonnet for reliability)
REFINEMENT_MODEL = "claude-sonnet-4-20250514"


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search for a query using DuckDuckGo.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of SearchResult objects

    Raises:
        SearchError: If search fails after retries
    """
    results = _search_duckduckgo(query, max_results)

    if not results:
        raise SearchError(f"No results found for query: {query}")

    return results


def _search_duckduckgo(query: str, max_results: int, retries: int = 2) -> list[SearchResult]:
    """Search using DuckDuckGo with retry logic."""
    last_error = None

    for attempt in range(retries + 1):
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", "")
                )
                for r in raw_results
                if r.get("href")
            ]

        except (DDGSException, RatelimitException) as e:
            last_error = e
            if attempt < retries:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"Search rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            continue

        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            break

    if last_error:
        raise SearchError(f"Search failed: {last_error}")

    return []


def refine_query(
    client: Anthropic,
    original_query: str,
    summaries: list[str],
) -> str:
    """
    Generate a refined follow-up search query based on initial findings.

    Args:
        client: Anthropic client
        original_query: The original research query
        summaries: List of summary snippets from first-pass results

    Returns:
        A refined search query string
    """
    # Truncate summaries to ~100 chars each for the prompt
    truncated = []
    for s in summaries[:10]:  # Max 10 summaries
        snippet = s[:150].rsplit(" ", 1)[0] + "..." if len(s) > 150 else s
        truncated.append(f"- {snippet}")

    findings = "\n".join(truncated)

    prompt = f"""Given this research question: "{original_query}"

And these initial findings:
{findings}

Generate ONE follow-up search query that:
- Fills gaps in the initial research
- Explores a specific angle not yet covered
- Is 3-8 words, suitable for a search engine

Return ONLY the query, nothing else."""

    try:
        response = client.messages.create(
            model=REFINEMENT_MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        if not response.content:
            logger.warning("Empty response from query refinement, using original query")
            return original_query
        refined = response.content[0].text.strip().strip('"').strip("'")
        if not refined:
            logger.warning("Empty refined query, using original query")
            return original_query
        logger.info(f"Refined query: {refined}")
        return refined
    except (APIError, RateLimitError, APIConnectionError) as e:
        logger.warning(f"Query refinement failed: {e}, using original query")
        return original_query
