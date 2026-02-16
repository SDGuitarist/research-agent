"""Async URL fetching with SSRF-safe redirect handling and size limits."""

import asyncio
import ipaddress
import logging
import random
import socket
import typing
from dataclasses import dataclass
from urllib.parse import urlparse

import httpcore
import httpx


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
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

# Maximum redirects to follow per URL (prevents redirect loops)
MAX_REDIRECTS = 10

# Maximum response body size (10 MB) — enforced via streaming
MAX_RESPONSE_SIZE = 10 * 1024 * 1024


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


class _SSRFSafeBackend(httpcore.AsyncNetworkBackend):
    """Network backend that validates DNS at TCP connect time.

    Resolves DNS, validates all IPs are public, then connects to the
    pinned IP — all in one step. This eliminates the TOCTOU gap where
    an attacker could rebind DNS between validation and connection.
    """

    def __init__(self) -> None:
        self._inner = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable | None = None,
    ) -> httpcore.AsyncNetworkStream:
        loop = asyncio.get_running_loop()
        addrinfo = await loop.getaddrinfo(
            host, port, proto=socket.IPPROTO_TCP,
        )
        if not addrinfo:
            raise httpcore.ConnectError(f"DNS resolution failed for {host}")

        for _, _, _, _, sockaddr in addrinfo:
            if _is_private_ip(sockaddr[0]):
                raise httpcore.ConnectError(
                    f"SSRF blocked: {host} resolves to private IP {sockaddr[0]}"
                )

        pinned_ip = addrinfo[0][4][0]
        return await self._inner.connect_tcp(
            pinned_ip, port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self, path: str, timeout: float | None = None,
        socket_options: typing.Iterable | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("Unix sockets not supported")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


# Per-run DNS validation cache — cleared at the start of each fetch_urls() call
_dns_cache: dict[str, bool] = {}


async def _resolve_and_validate_host(hostname: str, port: int = 443) -> bool:
    """
    Resolve hostname via async DNS and validate all resolved IPs are safe.

    Used as a pre-flight check to reject obviously unsafe URLs before
    opening a connection. The _SSRFSafeBackend provides defense-in-depth
    by re-validating at TCP connect time.

    Results are cached per-run to avoid redundant DNS lookups for the
    same domain across multiple URLs.
    """
    cache_key = f"{hostname}:{port}"
    if cache_key in _dns_cache:
        return _dns_cache[cache_key]

    try:
        loop = asyncio.get_running_loop()
        addrinfo = await loop.getaddrinfo(
            hostname, port, proto=socket.IPPROTO_TCP,
        )

        if not addrinfo:
            _dns_cache[cache_key] = False
            return False

        # Check each resolved IP
        for family, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                logger.warning(f"Blocked private IP {ip_str} for hostname {hostname}")
                _dns_cache[cache_key] = False
                return False

        _dns_cache[cache_key] = True
        return True
    except (socket.gaierror, socket.herror, OSError):
        # DNS resolution failed
        _dns_cache[cache_key] = False
        return False


async def _is_safe_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTP(S) schemes (file://, ftp://, etc.)
    - Localhost and loopback addresses
    - Private IP ranges (checked via async DNS resolution)
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

        # Pre-flight DNS validation (defense-in-depth with _SSRFSafeBackend)
        if not await _resolve_and_validate_host(host, port):
            return False

        return True
    except ValueError:
        return False


async def _fetch_single(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> FetchedPage | None:
    """Fetch a single URL with SSRF-safe redirect handling and size limits.

    Handles redirects manually so each hop is validated against SSRF checks.
    Uses streaming to enforce response size limits before reading into memory.
    """
    # Pre-flight SSRF check on the original URL
    if not await _is_safe_url(url):
        return None

    async with semaphore:
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            try:
                async with client.stream("GET", current_url) as response:
                    # Handle redirects manually — validate each target
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        if not location:
                            return None
                        redirect_url = str(response.url.join(location))
                        if not await _is_safe_url(redirect_url):
                            logger.warning(
                                "Blocked redirect to unsafe URL: %s", redirect_url
                            )
                            return None
                        current_url = redirect_url
                        continue

                    # Non-redirect response
                    if response.status_code in SKIP_STATUS_CODES:
                        return None
                    if response.status_code == 429:
                        return None

                    response.raise_for_status()

                    # Check Content-Type
                    content_type = response.headers.get("content-type", "").lower()
                    media_type = content_type.split(";")[0].strip()
                    if media_type and media_type not in PROCESSABLE_CONTENT_TYPES:
                        logger.debug(
                            "Skipping non-HTML content type '%s' from %s",
                            media_type, current_url,
                        )
                        return None

                    # Early rejection via Content-Length header
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > MAX_RESPONSE_SIZE:
                                logger.warning(
                                    "Response too large (%s bytes) from %s",
                                    content_length, current_url,
                                )
                                return None
                        except ValueError:
                            pass

                    # Stream body with size enforcement
                    chunks: list[bytes] = []
                    total_size = 0
                    async for chunk in response.aiter_bytes():
                        total_size += len(chunk)
                        if total_size > MAX_RESPONSE_SIZE:
                            logger.warning(
                                "Response exceeded %d bytes from %s",
                                MAX_RESPONSE_SIZE, current_url,
                            )
                            return None
                        chunks.append(chunk)

                    body = b"".join(chunks)
                    encoding = response.encoding or "utf-8"
                    text = body.decode(encoding, errors="replace")

                    return FetchedPage(
                        url=str(response.url),
                        html=text,
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

        # Exceeded MAX_REDIRECTS
        logger.warning("Too many redirects for %s", url)
        return None


async def fetch_urls(
    urls: list[str],
    timeout: float = 15.0,
    max_concurrent: int = MAX_CONCURRENT_REQUESTS,
) -> list[FetchedPage]:
    """
    Fetch multiple URLs concurrently with SSRF protection and size limits.

    Args:
        urls: List of URLs to fetch
        timeout: Request timeout per URL
        max_concurrent: Maximum concurrent requests

    Returns:
        List of successfully fetched pages
    """
    _dns_cache.clear()
    semaphore = asyncio.Semaphore(max_concurrent)

    transport = httpx.AsyncHTTPTransport(
        limits=httpx.Limits(max_connections=max_concurrent),
    )
    # Pin DNS resolution at TCP connect time to prevent DNS rebinding
    transport._pool._network_backend = _SSRFSafeBackend()  # noqa: SLF001

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers=_get_random_headers(),
        transport=transport,
    ) as client:
        tasks = [_fetch_single(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
