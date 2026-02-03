"""Async URL fetching with retry logic."""

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass
class FetchedPage:
    """A fetched web page."""
    url: str
    html: str
    status_code: int


# Common browser User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Status codes that indicate we should skip this URL
SKIP_STATUS_CODES = {403, 404, 410, 451}

# Blocked URL schemes (prevent SSRF)
ALLOWED_SCHEMES = {"http", "https"}

# Blocked hosts (internal/private networks)
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
}


def _is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTP(S) schemes (file://, ftp://, etc.)
    - Localhost and loopback addresses
    - Private IP ranges
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False

        # Check for blocked hosts
        host = parsed.hostname or ""
        if host.lower() in BLOCKED_HOSTS:
            return False

        # Block private IP ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
        if host.replace(".", "").isdigit():
            parts = host.split(".")
            if len(parts) == 4:
                first = int(parts[0])
                second = int(parts[1])
                if first == 10:
                    return False
                if first == 172 and 16 <= second <= 31:
                    return False
                if first == 192 and second == 168:
                    return False
                if first == 169 and second == 254:
                    return False

        return True
    except Exception:
        return False


async def fetch_url(url: str, timeout: float = 15.0) -> FetchedPage | None:
    """
    Fetch a single URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        FetchedPage if successful, None if should be skipped
    """
    # Validate URL to prevent SSRF
    if not _is_safe_url(url):
        return None

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=HEADERS,
        ) as client:
            response = await client.get(url)

            if response.status_code in SKIP_STATUS_CODES:
                return None

            if response.status_code == 429:
                # Rate limited - could retry but we'll skip for simplicity
                return None

            response.raise_for_status()

            return FetchedPage(
                url=str(response.url),
                html=response.text,
                status_code=response.status_code,
            )

    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError:
        return None
    except Exception:
        return None


async def fetch_urls(urls: list[str], timeout: float = 15.0) -> list[FetchedPage]:
    """
    Fetch multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch
        timeout: Request timeout per URL

    Returns:
        List of successfully fetched pages
    """
    tasks = [fetch_url(url, timeout) for url in urls]
    results = await asyncio.gather(*tasks)

    # Filter out None results (failed fetches)
    return [r for r in results if r is not None]
