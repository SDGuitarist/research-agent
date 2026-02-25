"""Shared API retry and batching helpers for Claude API calls."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from anthropic import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

# Default retry parameters
DEFAULT_MAX_RETRIES = 1
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_BATCH_BACKOFF = 2.0


async def retry_api_call(
    api_call: Callable[[], Awaitable[T]],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    rate_limit_event: asyncio.Event | None = None,
    retry_on: tuple[type[Exception], ...] = (RateLimitError,),
    context: str = "",
) -> T:
    """Retry an async API call with backoff on specified errors.

    Args:
        api_call: Zero-arg callable returning an awaitable (e.g., lambda: client.messages.create(...))
        max_retries: Number of retries after the first attempt (total attempts = max_retries + 1)
        retry_delay: Seconds to sleep between retries
        rate_limit_event: Optional event to signal when a RateLimitError occurs
        retry_on: Tuple of exception types that trigger a retry. Defaults to (RateLimitError,).
            APITimeoutError and APIConnectionError can be added for transient-error retries.
        context: Short description for log messages (e.g., "Summarizing https://...")

    Returns:
        The result of api_call() on success.

    Raises:
        RateLimitError: If retries exhausted on rate limit.
        APIError / APITimeoutError / APIConnectionError: On non-retryable API failure.
    """
    for attempt in range(max_retries + 1):
        try:
            return await api_call()
        except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as e:
            is_retryable = isinstance(e, retry_on)

            # Signal rate limit to batch coordinator
            if isinstance(e, RateLimitError) and rate_limit_event is not None:
                rate_limit_event.set()

            if is_retryable and attempt < max_retries:
                logger.warning(
                    "%s %s, retrying in %ss...",
                    context, type(e).__name__, retry_delay,
                )
                await asyncio.sleep(retry_delay)
                continue

            # Retries exhausted or non-retryable
            if is_retryable:
                logger.warning("%s %s, exhausted retries", context, type(e).__name__)
            else:
                logger.warning("%s %s: %s", context, type(e).__name__, e)
            raise

    # Unreachable — loop always raises or returns — but satisfies type checker
    raise RuntimeError("retry_api_call: unreachable")  # pragma: no cover


async def process_in_batches(
    items: list[T],
    process_fn: Callable[[T], Awaitable[R]],
    *,
    batch_size: int,
    rate_limit_event: asyncio.Event | None = None,
    backoff_seconds: float = DEFAULT_BATCH_BACKOFF,
) -> list[R | BaseException]:
    """Process items in batches with adaptive rate-limit backoff.

    Between batches, sleeps only if rate_limit_event was set (i.e., a 429
    occurred in the previous batch), then clears the event.

    Args:
        items: List of items to process.
        process_fn: Async function that processes one item.
        batch_size: Number of items per batch.
        rate_limit_event: Shared event that process_fn sets on 429.
        backoff_seconds: Seconds to sleep between batches after a 429.

    Returns:
        Flat list of results (or Exceptions from asyncio.gather).
    """
    results: list[R | BaseException] = []

    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start:batch_start + batch_size]

        if batch_start > 0 and rate_limit_event is not None and rate_limit_event.is_set():
            await asyncio.sleep(backoff_seconds)
            rate_limit_event.clear()

        batch_results = await asyncio.gather(
            *[process_fn(item) for item in batch],
            return_exceptions=True,
        )
        results.extend(batch_results)

    return results
