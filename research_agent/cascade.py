"""Cascade fallback fetching: Jina Reader → Tavily Extract → snippet."""

import asyncio
import logging
import os
from urllib.parse import urlparse

import httpx
from tavily.errors import (
    BadRequestError as TavilyBadRequest,
    InvalidAPIKeyError as TavilyInvalidKey,
    MissingAPIKeyError as TavilyMissingKey,
    UsageLimitExceededError as TavilyUsageLimit,
    ForbiddenError as TavilyForbidden,
    TimeoutError as TavilyTimeout,
)

from .extract import ExtractedContent
from .search import SearchResult

logger = logging.getLogger(__name__)

JINA_CONCURRENT = 5
JINA_TIMEOUT = 20.0
MIN_CONTENT_LENGTH = 100

# Domains worth spending Tavily Extract credits on
# Cached TavilyClient instance (avoids re-instantiation per extract call)
_tavily_client: object | None = None
_tavily_client_key: str | None = None
_tavily_client_class: type | None = None

# Domains worth spending Tavily Extract credits on
EXTRACT_DOMAINS = frozenset({
    "weddingwire.com",
    "theknot.com",
    "thebash.com",
    "gigsalad.com",
    "yelp.com",
    "instagram.com",
    "facebook.com",
    "youtube.com",
})


def _get_tavily_client(api_key: str):
    """Return a cached TavilyClient, creating one if needed."""
    global _tavily_client, _tavily_client_key, _tavily_client_class
    from tavily import TavilyClient
    if _tavily_client is None or _tavily_client_key != api_key or _tavily_client_class is not TavilyClient:
        _tavily_client = TavilyClient(api_key=api_key)
        _tavily_client_key = api_key
        _tavily_client_class = TavilyClient
    return _tavily_client


async def cascade_recover(
    failed_urls: list[str],
    all_results: list[SearchResult],
) -> list[ExtractedContent]:
    """
    Try to recover content for URLs that failed direct fetch + extract.

    Layer 1: Jina Reader (free, async HTTP)
    Layer 2: Tavily Extract (1 credit/5 URLs, high-value domains only)
    Layer 3: Snippet fallback (use search snippet as thin content)
    """
    if not failed_urls:
        return []

    recovered = []
    remaining = set(failed_urls)

    # Layer 1: Jina Reader
    jina_results = await _fetch_via_jina(list(remaining))
    for content in jina_results:
        recovered.append(content)
        remaining.discard(content.url)
    if jina_results:
        logger.info(f"Jina Reader recovered {len(jina_results)} pages")

    # Layer 2: Tavily Extract (high-value domains only, costs credits)
    if remaining:
        extract_urls = [u for u in remaining if _is_extract_domain(u)]
        if extract_urls:
            tavily_key = os.environ.get("TAVILY_API_KEY")
            extract_results = await _fetch_via_tavily_extract(
                extract_urls, tavily_key
            )
            for content in extract_results:
                recovered.append(content)
                remaining.discard(content.url)
            if extract_results:
                logger.info(
                    f"Tavily Extract recovered {len(extract_results)} pages"
                )

    # Layer 3: Snippet fallback
    if remaining:
        snippets = _snippet_fallback(remaining, all_results)
        recovered.extend(snippets)
        if snippets:
            logger.info(f"Snippet fallback: {len(snippets)} thin sources")

    return recovered


async def _fetch_via_jina(urls: list[str]) -> list[ExtractedContent]:
    """Fetch URLs via Jina Reader proxy (free, returns markdown)."""
    if not urls:
        return []

    semaphore = asyncio.Semaphore(JINA_CONCURRENT)
    async with httpx.AsyncClient(
        timeout=JINA_TIMEOUT, follow_redirects=True
    ) as client:
        tasks = [_jina_single(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def _jina_single(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> ExtractedContent | None:
    """Fetch a single URL via Jina Reader."""
    async with semaphore:
        try:
            resp = await client.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "text/markdown"},
            )
            if resp.status_code != 200:
                return None
            text = resp.text
            if len(text) < MIN_CONTENT_LENGTH:
                return None
            title = _extract_markdown_title(text)
            return ExtractedContent(url=url, title=title, text=text)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
            return None


def _extract_markdown_title(text: str) -> str:
    """Extract title from first markdown H1 heading."""
    for line in text.split("\n", 10):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


async def _fetch_via_tavily_extract(
    urls: list[str], tavily_key: str | None
) -> list[ExtractedContent]:
    """Fetch URLs via Tavily Extract API (1 credit per 5 URLs)."""
    if not tavily_key or not urls:
        return []

    try:
        client = _get_tavily_client(tavily_key)
        result = await asyncio.to_thread(client.extract, urls=urls[:20])

        contents = []
        for r in result.get("results", []):
            raw = r.get("raw_content") or ""
            if len(raw) < MIN_CONTENT_LENGTH:
                continue
            contents.append(
                ExtractedContent(
                    url=r.get("url", ""),
                    title="",
                    text=raw,
                )
            )
        return contents
    except (
        TavilyBadRequest, TavilyInvalidKey, TavilyMissingKey,
        TavilyUsageLimit, TavilyForbidden, TavilyTimeout,
        ConnectionError, OSError,
    ) as e:
        logger.warning(f"Tavily Extract failed: {e}")
        return []


def _is_extract_domain(url: str) -> bool:
    """Check if URL belongs to a high-value domain for Tavily Extract."""
    host = urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in EXTRACT_DOMAINS)


def _snippet_fallback(
    failed_urls: set[str],
    all_results: list[SearchResult],
) -> list[ExtractedContent]:
    """Use search snippets as last-resort content for failed URLs."""
    snippet_map: dict[str, SearchResult] = {}
    for r in all_results:
        if r.url in failed_urls and r.snippet and len(r.snippet) > 50:
            if r.url not in snippet_map:
                snippet_map[r.url] = r

    contents = []
    for r in snippet_map.values():
        contents.append(
            ExtractedContent(
                url=r.url,
                title=r.title,
                text=f"[Source: search snippet] {r.snippet}",
            )
        )
    return contents
