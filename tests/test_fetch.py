"""Tests for research_agent.fetch module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from research_agent.fetch import (
    _is_private_ip,
    _is_safe_url,
    fetch_urls,
    FetchedPage,
)


class TestIsPrivateIp:
    """Tests for _is_private_ip() function."""

    def test_is_private_ip_returns_true_for_loopback_127_0_0_1(self):
        """127.0.0.1 should be identified as private."""
        assert _is_private_ip("127.0.0.1") is True

    def test_is_private_ip_returns_true_for_loopback_ipv6(self):
        """::1 (IPv6 loopback) should be identified as private."""
        assert _is_private_ip("::1") is True

    def test_is_private_ip_returns_true_for_10_x_range(self):
        """10.x.x.x range should be identified as private."""
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("10.255.255.255") is True

    def test_is_private_ip_returns_true_for_172_16_range(self):
        """172.16.x.x - 172.31.x.x range should be identified as private."""
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True

    def test_is_private_ip_returns_true_for_192_168_range(self):
        """192.168.x.x range should be identified as private."""
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("192.168.0.1") is True

    def test_is_private_ip_returns_true_for_link_local(self):
        """169.254.x.x (link-local/AWS metadata) should be identified as private."""
        assert _is_private_ip("169.254.169.254") is True

    def test_is_private_ip_returns_false_for_public_ip(self):
        """Public IP addresses should not be identified as private."""
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("1.1.1.1") is False
        assert _is_private_ip("93.184.216.34") is False  # example.com

    def test_is_private_ip_returns_true_for_invalid_ip(self):
        """Invalid IP strings should return True (unsafe)."""
        assert _is_private_ip("not-an-ip") is True
        assert _is_private_ip("") is True


class TestIsSafeUrl:
    """Tests for _is_safe_url() function."""

    def test_is_safe_url_allows_https_public_url(self):
        """HTTPS URLs to public hosts should be allowed."""
        # Patch DNS resolution to return a public IP
        with patch("research_agent.fetch._resolve_and_validate_host", return_value=True):
            assert _is_safe_url("https://example.com/page") is True

    def test_is_safe_url_allows_http_public_url(self):
        """HTTP URLs to public hosts should be allowed."""
        with patch("research_agent.fetch._resolve_and_validate_host", return_value=True):
            assert _is_safe_url("http://example.com/page") is True

    def test_is_safe_url_blocks_file_scheme(self):
        """file:// scheme should be blocked."""
        assert _is_safe_url("file:///etc/passwd") is False

    def test_is_safe_url_blocks_ftp_scheme(self):
        """ftp:// scheme should be blocked."""
        assert _is_safe_url("ftp://example.com/file") is False

    def test_is_safe_url_blocks_localhost(self):
        """localhost should be blocked."""
        assert _is_safe_url("http://localhost/admin") is False
        assert _is_safe_url("https://localhost:8080/") is False

    def test_is_safe_url_blocks_127_0_0_1(self):
        """127.0.0.1 should be blocked."""
        assert _is_safe_url("http://127.0.0.1/") is False
        assert _is_safe_url("http://127.0.0.1:3000/api") is False

    def test_is_safe_url_blocks_private_ip_ranges(self):
        """Private IP ranges should be blocked via DNS resolution."""
        # The function resolves DNS, so we test that it rejects when resolution returns private IPs
        with patch("research_agent.fetch._resolve_and_validate_host", return_value=False):
            assert _is_safe_url("http://internal.company.com/") is False

    def test_is_safe_url_returns_false_for_empty_url(self):
        """Empty URL should return False."""
        assert _is_safe_url("") is False

    def test_is_safe_url_returns_false_for_url_without_host(self):
        """URL without host should return False."""
        assert _is_safe_url("http:///path") is False

    def test_is_safe_url_blocks_0_0_0_0(self):
        """0.0.0.0 should be blocked."""
        assert _is_safe_url("http://0.0.0.0/") is False


class TestFetchUrls:
    """Tests for fetch_urls() async function."""

    @pytest.mark.asyncio
    async def test_fetch_urls_returns_fetched_pages_on_success(self, mock_httpx_response):
        """Successful fetch should return FetchedPage objects."""
        mock_response = mock_httpx_response(
            status_code=200,
            text="<html><body>Content</body></html>",
            content_type="text/html",
            url="https://example.com"
        )

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com"])

                assert len(results) == 1
                assert isinstance(results[0], FetchedPage)
                assert results[0].status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_urls_skips_403_forbidden_responses(self, mock_httpx_response):
        """403 responses should be skipped (not in results)."""
        mock_response = mock_httpx_response(status_code=403)
        # Don't raise for 403 since it's in SKIP_STATUS_CODES
        mock_response.raise_for_status = MagicMock()

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com"])

                assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_urls_skips_timeout_errors(self):
        """Timeout errors should result in skipped URLs."""
        import httpx

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com"])

                assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_urls_filters_non_html_content_types(self, mock_httpx_response):
        """Non-HTML content types (PDF, images) should be skipped."""
        mock_response = mock_httpx_response(
            status_code=200,
            text="PDF content",
            content_type="application/pdf",
            url="https://example.com/doc.pdf"
        )

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com/doc.pdf"])

                assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_urls_skips_unsafe_urls(self, mock_httpx_response):
        """Unsafe URLs should be filtered before fetching."""
        with patch("research_agent.fetch._is_safe_url", return_value=False):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["http://localhost/admin"])

                assert len(results) == 0
                # Should not have attempted to fetch
                mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_urls_handles_multiple_urls(self, mock_httpx_response):
        """Multiple URLs should be fetched concurrently."""
        mock_response = mock_httpx_response(
            status_code=200,
            text="<html><body>Content</body></html>",
            content_type="text/html"
        )

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                urls = [
                    "https://example1.com",
                    "https://example2.com",
                    "https://example3.com",
                ]
                results = await fetch_urls(urls)

                assert len(results) == 3
                assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_urls_skips_429_rate_limit_responses(self, mock_httpx_response):
        """429 rate limit responses should be skipped."""
        mock_response = mock_httpx_response(status_code=429)
        mock_response.raise_for_status = MagicMock()  # Don't raise for 429

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com"])

                assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_urls_accepts_text_plain_content_type(self, mock_httpx_response):
        """text/plain content type should be accepted."""
        mock_response = mock_httpx_response(
            status_code=200,
            text="Plain text content here",
            content_type="text/plain",
            url="https://example.com/file.txt"
        )

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com/file.txt"])

                assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_urls_handles_connect_error(self):
        """Connection errors should result in skipped URLs."""
        import httpx

        with patch("research_agent.fetch._is_safe_url", return_value=True):
            with patch("research_agent.fetch.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
                mock_client_class.return_value.__aenter__.return_value = mock_client

                results = await fetch_urls(["https://example.com"])

                assert len(results) == 0
