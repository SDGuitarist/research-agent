"""Async URL fetching with retry logic."""

import asyncio
import ipaddress
import logging
import random
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


logger = logging.getLogger(__name__)


@dataclass
class FetchedPage:
    """A fetched web page."""
    url: str
    html: str
    status_code: int


# Pool of common browser User-Agents to rotate through
# This reduces detection by sites that block single static User-Agents
USER_AGENTS = [
    # Chrome on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    # Chrome on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    # Firefox on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    ),
    # Firefox on Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    ),
    # Safari on macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Safari/605.1.15"
    ),
]


def _get_random_headers() -> dict[str, str]:
    """Get headers with a randomly selected User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

# Status codes that indicate we should skip this URL
SKIP_STATUS_CODES = {403, 404, 410, 451}

# Maximum concurrent requests
MAX_CONCURRENT_REQUESTS = 5

# Content types we can process (HTML and plain text)
PROCESSABLE_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}

# Blocked URL schemes (prevent SSRF)
ALLOWED_SCHEMES = {"http", "https"}

# Blocked hosts (internal/private networks)
BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
}


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or otherwise unsafe."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True  # Invalid IP is unsafe


def _resolve_and_validate_host(hostname: str, port: int = 443) -> bool:
    """
    Resolve hostname via DNS and validate all resolved IPs are safe.

    This prevents DNS rebinding attacks by checking resolved IPs,
    not just the hostname string.
    """
    try:
        # Resolve all addresses for the hostname
        addrinfo = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)

        if not addrinfo:
            return False

        # Check each resolved IP
        for family, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                logger.warning(f"Blocked private IP {ip_str} for hostname {hostname}")
                return False

        return True
    except (socket.gaierror, socket.herror, OSError):
        # DNS resolution failed
        return False


def _is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTP(S) schemes (file://, ftp://, etc.)
    - Localhost and loopback addresses
    - Private IP ranges (checked via DNS resolution to prevent rebinding)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return False

        host = parsed.hostname or ""
        if not host:
            return False

        # Check for blocked hostnames
        if host.lower() in BLOCKED_HOSTS:
            return False

        # Determine port for DNS resolution
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Resolve DNS and validate all resolved IPs are safe
        # This prevents DNS rebinding attacks
        if not _resolve_and_validate_host(host, port):
            return False

        return True
    except ValueError:
        return False


async def _fetch_single(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> FetchedPage | None:
    """Fetch a single URL using a shared client with concurrency control."""
    # Validate URL to prevent SSRF
    if not _is_safe_url(url):
        return None

    async with semaphore:
        try:
            response = await client.get(url)

            if response.status_code in SKIP_STATUS_CODES:
                return None

            if response.status_code == 429:
                return None

            response.raise_for_status()

            # Check Content-Type to avoid processing binary files (PDFs, images, etc.)
            content_type = response.headers.get("content-type", "").lower()
            # Extract the media type (ignore charset and other params)
            media_type = content_type.split(";")[0].strip()
            if media_type and media_type not in PROCESSABLE_CONTENT_TYPES:
                logger.debug(f"Skipping non-HTML content type '{media_type}' from {url}")
                return None

            return FetchedPage(
                url=str(response.url),
                html=response.text,
                status_code=response.status_code,
            )

        except httpx.TimeoutException:
            return None
        except httpx.HTTPStatusError:
            return None
        except httpx.ConnectError:
            return None
        except httpx.ReadError:
            return None


async def fetch_urls(
    urls: list[str],
    timeout: float = 15.0,
    max_concurrent: int = MAX_CONCURRENT_REQUESTS,
) -> list[FetchedPage]:
    """
    Fetch multiple URLs concurrently with connection pooling.

    Args:
        urls: List of URLs to fetch
        timeout: Request timeout per URL
        max_concurrent: Maximum concurrent requests

    Returns:
        List of successfully fetched pages
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=_get_random_headers(),
        limits=httpx.Limits(max_connections=max_concurrent),
    ) as client:
        tasks = [_fetch_single(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
