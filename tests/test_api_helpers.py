"""Tests for shared API retry and batching helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIConnectionError, APIError, APITimeoutError, RateLimitError

from research_agent.api_helpers import (
    DEFAULT_BATCH_BACKOFF,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    process_in_batches,
    retry_api_call,
)


def _make_rate_limit_error():
    """Create a RateLimitError with required mock response."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    return RateLimitError(message="Rate limited", response=mock_response, body=None)


def _make_api_error():
    """Create an APIError with required mock response."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    return APIError(message="Server error", request=MagicMock(), body=None)


# --- retry_api_call tests ---


class TestRetryApiCall:
    """Tests for retry_api_call()."""

    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        """Should return the API call result on first success."""
        api_call = AsyncMock(return_value="result")

        result = await retry_api_call(api_call)

        assert result == "result"
        assert api_call.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_then_succeeds(self):
        """Should retry once on RateLimitError and return success."""
        api_call = AsyncMock(side_effect=[_make_rate_limit_error(), "success"])

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_api_call(api_call)

        assert result == "success"
        assert api_call.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_on_rate_limit_after_retries_exhausted(self):
        """Should raise RateLimitError after exhausting retries."""
        api_call = AsyncMock(side_effect=_make_rate_limit_error())

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RateLimitError):
                await retry_api_call(api_call)

        assert api_call.call_count == DEFAULT_MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_raises_immediately_on_api_error(self):
        """APIError should not be retried (non-retryable by default)."""
        api_call = AsyncMock(side_effect=_make_api_error())

        with pytest.raises(APIError):
            await retry_api_call(api_call)

        assert api_call.call_count == 1

    @pytest.mark.asyncio
    async def test_signals_rate_limit_event(self):
        """Should set rate_limit_event when RateLimitError occurs."""
        event = asyncio.Event()
        api_call = AsyncMock(side_effect=[_make_rate_limit_error(), "success"])

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock):
            await retry_api_call(api_call, rate_limit_event=event)

        assert event.is_set()

    @pytest.mark.asyncio
    async def test_sleeps_between_retries(self):
        """Should sleep for retry_delay between retries."""
        api_call = AsyncMock(side_effect=[_make_rate_limit_error(), "success"])

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await retry_api_call(api_call, retry_delay=3.0)

        mock_sleep.assert_called_once_with(3.0)

    @pytest.mark.asyncio
    async def test_custom_retry_on_includes_timeout(self):
        """Should retry on APITimeoutError when included in retry_on."""
        timeout_error = APITimeoutError(request=MagicMock())
        api_call = AsyncMock(side_effect=[timeout_error, "success"])

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_api_call(
                api_call,
                retry_on=(RateLimitError, APITimeoutError),
            )

        assert result == "success"
        assert api_call.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_retry_on_includes_connection_error(self):
        """Should retry on APIConnectionError when included in retry_on."""
        conn_error = APIConnectionError(request=MagicMock())
        api_call = AsyncMock(side_effect=[conn_error, "success"])

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_api_call(
                api_call,
                retry_on=(RateLimitError, APIConnectionError),
            )

        assert result == "success"
        assert api_call.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_not_retried_by_default(self):
        """APITimeoutError should not be retried with default retry_on."""
        timeout_error = APITimeoutError(request=MagicMock())
        api_call = AsyncMock(side_effect=timeout_error)

        with pytest.raises(APITimeoutError):
            await retry_api_call(api_call)

        assert api_call.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_zero_means_no_retry(self):
        """max_retries=0 should try once and raise on failure."""
        api_call = AsyncMock(side_effect=_make_rate_limit_error())

        with pytest.raises(RateLimitError):
            await retry_api_call(api_call, max_retries=0)

        assert api_call.call_count == 1

    @pytest.mark.asyncio
    async def test_defaults_are_correct(self):
        """Verify module-level defaults."""
        assert DEFAULT_MAX_RETRIES == 1
        assert DEFAULT_RETRY_DELAY == 2.0
        assert DEFAULT_BATCH_BACKOFF == 2.0


# --- process_in_batches tests ---


class TestProcessInBatches:
    """Tests for process_in_batches()."""

    @pytest.mark.asyncio
    async def test_processes_all_items(self):
        """Should process every item and return all results."""
        items = [1, 2, 3, 4, 5]

        async def double(x):
            return x * 2

        results = await process_in_batches(items, double, batch_size=3)

        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_empty_items_returns_empty(self):
        """Should return empty list for empty input."""
        async def noop(x):
            return x

        results = await process_in_batches([], noop, batch_size=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_no_sleep_without_rate_limit(self):
        """Should not sleep between batches when no 429 occurred."""
        items = list(range(10))

        async def identity(x):
            return x

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await process_in_batches(items, identity, batch_size=3)

        mock_sleep.assert_not_called()
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_sleeps_after_rate_limit_event(self):
        """Should sleep between batches when rate_limit_event is set."""
        event = asyncio.Event()
        items = list(range(6))

        call_count = 0

        async def trigger_rate_limit(x):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                event.set()
            return x

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await process_in_batches(
                items, trigger_rate_limit,
                batch_size=3,
                rate_limit_event=event,
                backoff_seconds=5.0,
            )

        mock_sleep.assert_called_once_with(5.0)
        assert len(results) == 6
        # Event should be cleared after backoff
        assert not event.is_set()

    @pytest.mark.asyncio
    async def test_preserves_exceptions(self):
        """Exceptions from process_fn should be captured in results."""
        items = [1, 2, 3]

        async def maybe_fail(x):
            if x == 2:
                raise ValueError("fail")
            return x

        results = await process_in_batches(items, maybe_fail, batch_size=5)

        assert results[0] == 1
        assert isinstance(results[1], ValueError)
        assert results[2] == 3

    @pytest.mark.asyncio
    async def test_single_batch_no_backoff(self):
        """Items fitting in one batch should never trigger backoff sleep."""
        event = asyncio.Event()
        event.set()
        items = [1, 2]

        async def identity(x):
            return x

        with patch("research_agent.api_helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await process_in_batches(
                items, identity,
                batch_size=5,
                rate_limit_event=event,
            )

        # batch_start == 0 for the only batch, so no sleep even with event set
        mock_sleep.assert_not_called()
        assert results == [1, 2]
