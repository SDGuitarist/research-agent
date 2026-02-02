"""Search functionality with DuckDuckGo and fallback support."""

import time
from dataclasses import dataclass

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

from .errors import SearchError


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
                print(f"  Search rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            continue

        except Exception as e:
            last_error = e
            break

    if last_error:
        raise SearchError(f"Search failed: {last_error}")

    return []
