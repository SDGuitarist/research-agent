"""Tests for research_agent.summarize module."""

import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from research_agent.sanitize import sanitize_content
from research_agent.summarize import (
    _chunk_text,
    summarize_chunk,
    summarize_content,
    summarize_all,
    Summary,
    CHUNK_SIZE,
    MAX_CHUNKS_PER_SOURCE,
    BATCH_SIZE,
    BATCH_DELAY,
    MAX_CONCURRENT_CHUNKS,
)
from research_agent.extract import ExtractedContent


class TestSanitizeContent:
    """Tests for sanitize_content() function."""

    def test_sanitize_content_escapes_angle_brackets(self):
        """Angle brackets should be escaped to prevent prompt injection."""
        result = sanitize_content("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_sanitize_content_handles_empty_string(self):
        """Empty string should return empty string."""
        result = sanitize_content("")
        assert result == ""

    def test_sanitize_content_handles_multiple_tags(self):
        """Multiple tag pairs should all be escaped."""
        result = sanitize_content("<div><p>text</p></div>")
        assert result == "&lt;div&gt;&lt;p&gt;text&lt;/p&gt;&lt;/div&gt;"

    def test_sanitize_content_preserves_ampersands_in_text(self):
        """Regular ampersands in text should be preserved."""
        result = sanitize_content("Tom & Jerry")
        assert result == "Tom & Jerry"


class TestChunkText:
    """Tests for _chunk_text() function."""

    def test_chunk_text_returns_single_chunk_for_short_text(self):
        """Text under chunk size should return as single chunk."""
        short_text = "This is a short text."
        result = _chunk_text(short_text, chunk_size=1000)

        assert len(result) == 1
        assert result[0] == short_text

    def test_chunk_text_splits_at_paragraph_boundaries(self):
        """Should prefer splitting at paragraph breaks (double newline)."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = _chunk_text(text, chunk_size=30)

        # Should split at paragraph boundaries
        assert len(result) >= 2
        # Each chunk should end cleanly, not mid-word
        for chunk in result:
            assert not chunk.endswith(" ")

    def test_chunk_text_splits_at_newlines_when_no_paragraphs(self):
        """Should fall back to single newlines if no paragraph breaks."""
        text = "Line one\nLine two\nLine three\nLine four"
        result = _chunk_text(text, chunk_size=20)

        assert len(result) >= 2

    def test_chunk_text_limits_to_max_chunks(self):
        """Should not return more than MAX_CHUNKS_PER_SOURCE chunks."""
        # Create text that would produce many chunks
        long_text = ("This is a paragraph.\n\n" * 100)
        result = _chunk_text(long_text, chunk_size=50)

        assert len(result) <= MAX_CHUNKS_PER_SOURCE

    def test_chunk_text_handles_empty_string(self):
        """Empty string should return list with empty string."""
        result = _chunk_text("")
        assert result == [""]

    def test_chunk_text_handles_text_with_no_break_points(self):
        """Text with no whitespace should still be chunked."""
        text = "x" * 10000  # Long text with no breaks
        result = _chunk_text(text, chunk_size=1000)

        assert len(result) >= 2
        # All text should be captured
        total_length = sum(len(chunk) for chunk in result)
        # May lose some chars at chunk boundaries
        assert total_length >= 3000  # At least MAX_CHUNKS_PER_SOURCE chunks


class TestSummarizeChunk:
    """Tests for summarize_chunk() async function."""

    @pytest.mark.asyncio
    async def test_summarize_chunk_returns_summary_on_success(self):
        """Successful API call should return Summary object."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is the summary.")]
        mock_client.messages.create.return_value = mock_response

        result = await summarize_chunk(
            client=mock_client,
            chunk="Content to summarize",
            url="https://example.com",
            title="Test Article",
        )

        assert isinstance(result, Summary)
        assert result.url == "https://example.com"
        assert result.title == "Test Article"
        assert result.summary == "This is the summary."

    @pytest.mark.asyncio
    async def test_summarize_chunk_returns_none_on_api_error(self):
        """APIError should return None."""
        from anthropic import APIError

        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="API error",
            request=mock_request,
            body=None
        )

        result = await summarize_chunk(
            client=mock_client,
            chunk="Content",
            url="https://example.com",
            title="Test",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_chunk_retries_on_rate_limit_then_returns_none(self):
        """RateLimitError should retry once then return None."""
        from anthropic import RateLimitError

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_client.messages.create.side_effect = RateLimitError(
            message="Rate limited",
            response=mock_response,
            body=None
        )

        with patch("research_agent.summarize.asyncio.sleep", new_callable=AsyncMock):
            result = await summarize_chunk(
                client=mock_client,
                chunk="Content",
                url="https://example.com",
                title="Test",
            )

        assert result is None
        assert mock_client.messages.create.call_count == 2  # Original + 1 retry

    @pytest.mark.asyncio
    async def test_summarize_chunk_retry_succeeds_on_second_attempt(self):
        """RateLimitError on first attempt, success on second should return Summary."""
        from anthropic import RateLimitError

        mock_client = AsyncMock()
        mock_rate_response = MagicMock()
        mock_rate_response.status_code = 429
        mock_rate_response.headers = {}

        mock_success_response = MagicMock()
        mock_success_response.content = [MagicMock(text="Summary after retry")]

        mock_client.messages.create.side_effect = [
            RateLimitError(message="Rate limited", response=mock_rate_response, body=None),
            mock_success_response,
        ]

        with patch("research_agent.summarize.asyncio.sleep", new_callable=AsyncMock):
            result = await summarize_chunk(
                client=mock_client,
                chunk="Content",
                url="https://example.com",
                title="Test",
            )

        assert isinstance(result, Summary)
        assert result.summary == "Summary after retry"
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_summarize_chunk_sanitizes_content(self):
        """Content with special characters should be sanitized."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        await summarize_chunk(
            client=mock_client,
            chunk="<script>malicious</script>",
            url="https://example.com",
            title="<title>Test</title>",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        # Check that angle brackets are escaped
        assert "&lt;script&gt;" in user_content
        assert "<script>" not in user_content

    @pytest.mark.asyncio
    async def test_summarize_chunk_returns_none_on_malformed_response(self):
        """Response without content should return None."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []  # Empty content
        mock_client.messages.create.return_value = mock_response

        result = await summarize_chunk(
            client=mock_client,
            chunk="Content",
            url="https://example.com",
            title="Test",
        )

        assert result is None


class TestSummarizeContent:
    """Tests for summarize_content() async function."""

    @pytest.mark.asyncio
    async def test_summarize_content_returns_summaries(self):
        """Should return list of Summary objects."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary text")]
        mock_client.messages.create.return_value = mock_response

        content = ExtractedContent(
            url="https://example.com",
            title="Test Article",
            text="Short content that fits in one chunk."
        )

        result = await summarize_content(mock_client, content)

        assert len(result) >= 1
        assert all(isinstance(s, Summary) for s in result)

    @pytest.mark.asyncio
    async def test_summarize_content_chunks_long_text(self):
        """Long text should be split into multiple chunks."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        # Create content that will require chunking
        long_text = "This is a paragraph.\n\n" * 500  # ~11000 chars
        content = ExtractedContent(
            url="https://example.com",
            title="Long Article",
            text=long_text
        )

        result = await summarize_content(mock_client, content)

        # Should have multiple summaries from chunks
        assert len(result) >= 2
        assert mock_client.messages.create.call_count >= 2


class TestSummarizeAll:
    """Tests for summarize_all() async function."""

    @pytest.mark.asyncio
    async def test_summarize_all_returns_combined_summaries(self, sample_extracted_content):
        """Should return summaries from all content pieces."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        result = await summarize_all(mock_client, sample_extracted_content)

        assert len(result) >= len(sample_extracted_content)
        assert all(isinstance(s, Summary) for s in result)

    @pytest.mark.asyncio
    async def test_summarize_all_handles_partial_failures(self, sample_extracted_content):
        """Should continue when some summarizations fail."""
        from anthropic import APIError

        mock_client = AsyncMock()
        mock_request = MagicMock()

        # First call succeeds, second fails
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.side_effect = [
            mock_response,
            APIError(message="API error", request=mock_request, body=None),
        ]

        result = await summarize_all(mock_client, sample_extracted_content)

        # Should have at least one summary
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_summarize_all_handles_empty_list(self):
        """Empty content list should return empty summaries."""
        mock_client = AsyncMock()

        result = await summarize_all(mock_client, [])

        assert result == []
        mock_client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_all_sleeps_between_batches(self):
        """Should call asyncio.sleep between batches when more than BATCH_SIZE items."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        # Create more contents than BATCH_SIZE to trigger multiple batches
        contents = [
            ExtractedContent(url=f"https://ex{i}.com", title=f"T{i}", text="Short content")
            for i in range(BATCH_SIZE + 2)
        ]

        with patch("research_agent.summarize.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await summarize_all(mock_client, contents)

        # Should have slept once (between batch 1 and batch 2)
        mock_sleep.assert_called_once_with(BATCH_DELAY)
        assert len(result) == BATCH_SIZE + 2

    @pytest.mark.asyncio
    async def test_summarize_all_no_sleep_for_single_batch(self):
        """Should NOT call asyncio.sleep when all items fit in one batch."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        # Fewer items than BATCH_SIZE
        contents = [
            ExtractedContent(url=f"https://ex{i}.com", title=f"T{i}", text="Short content")
            for i in range(3)
        ]

        with patch("research_agent.summarize.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await summarize_all(mock_client, contents)

        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_all_partial_results_from_batches(self):
        """Should return partial results when one batch has errors."""
        from anthropic import APIError

        mock_client = AsyncMock()
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]

        # Alternate success/failure across many calls
        side_effects = []
        for i in range(BATCH_SIZE + 2):
            if i % 3 == 2:
                side_effects.append(APIError(message="fail", request=mock_request, body=None))
            else:
                side_effects.append(mock_response)
        mock_client.messages.create.side_effect = side_effects

        contents = [
            ExtractedContent(url=f"https://ex{i}.com", title=f"T{i}", text="Short content")
            for i in range(BATCH_SIZE + 2)
        ]

        with patch("research_agent.summarize.asyncio.sleep", new_callable=AsyncMock):
            result = await summarize_all(mock_client, contents)

        # Should have some results (not all failed)
        assert len(result) > 0
        # Should be fewer than total (some failed)
        assert len(result) < BATCH_SIZE + 2

    def test_batch_constants_are_reasonable(self):
        """BATCH_SIZE and BATCH_DELAY should be within sensible ranges."""
        assert 5 <= BATCH_SIZE <= 20
        assert BATCH_DELAY >= 1.0
        assert 1 <= MAX_CONCURRENT_CHUNKS <= 10


    @pytest.mark.asyncio
    async def test_summarize_all_limits_concurrent_chunks(self):
        """Verify that chunk summarization respects the concurrency semaphore."""
        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def tracked_create(**kwargs):
            nonlocal max_concurrent_observed, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
            await asyncio.sleep(0.01)  # Simulate API latency
            async with lock:
                current_concurrent -= 1
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Summary")]
            return mock_response

        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = tracked_create

        # Create enough content to exceed MAX_CONCURRENT_CHUNKS
        contents = [
            ExtractedContent(
                url=f"http://example.com/{i}", title=f"Title {i}",
                text="Word " * 2000,  # Long enough to produce multiple chunks
            )
            for i in range(4)
        ]

        result = await summarize_all(mock_client, contents)
        assert len(result) > 0
        assert max_concurrent_observed <= MAX_CONCURRENT_CHUNKS


class TestStructuredSummaries:
    """Tests for structured summary format (Cycle 10 Step 4)."""

    @pytest.mark.asyncio
    async def test_structured_true_uses_facts_quotes_tone_prompt(self):
        """structured=True should use FACTS/KEY QUOTES/TONE prompt format."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="FACTS: Key facts here.\nKEY QUOTES: None found\nTONE: N/A")]
        mock_client.messages.create.return_value = mock_response

        await summarize_chunk(
            client=mock_client,
            chunk="Content to summarize",
            url="https://example.com",
            title="Test",
            structured=True,
        )

        call_args = mock_client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "FACTS:" in user_content
        assert "KEY QUOTES:" in user_content
        assert "TONE:" in user_content

    @pytest.mark.asyncio
    async def test_structured_false_uses_original_prompt(self):
        """structured=False should use original 2-4 sentences prompt."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary text")]
        mock_client.messages.create.return_value = mock_response

        await summarize_chunk(
            client=mock_client,
            chunk="Content to summarize",
            url="https://example.com",
            title="Test",
            structured=False,
        )

        call_args = mock_client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "2-4 sentences" in user_content
        assert "FACTS:" not in user_content

    @pytest.mark.asyncio
    async def test_structured_true_uses_800_max_tokens(self):
        """structured=True should use max_tokens=800."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        await summarize_chunk(
            client=mock_client,
            chunk="Content",
            url="https://example.com",
            title="Test",
            structured=True,
        )

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 800

    @pytest.mark.asyncio
    async def test_structured_false_uses_500_max_tokens(self):
        """structured=False should use max_tokens=500."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        mock_client.messages.create.return_value = mock_response

        await summarize_chunk(
            client=mock_client,
            chunk="Content",
            url="https://example.com",
            title="Test",
            structured=False,
        )

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_structured_threads_through_summarize_all(self):
        """structured flag should propagate from summarize_all to summarize_chunk."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="FACTS: data\nKEY QUOTES: None\nTONE: N/A")]
        mock_client.messages.create.return_value = mock_response

        contents = [
            ExtractedContent(url="https://ex.com", title="T", text="Short content")
        ]

        await summarize_all(mock_client, contents, structured=True)

        call_args = mock_client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "FACTS:" in user_content

    def test_max_chunks_5_produces_up_to_5_chunks(self):
        """max_chunks=5 should allow up to 5 chunks from long text."""
        long_text = "This is a paragraph.\n\n" * 1500  # ~33000 chars, enough for 5+ chunks at 4000 chars each
        chunks = _chunk_text(long_text, max_chunks=5)

        assert len(chunks) == 5
        # Verify default would have capped at 3
        default_chunks = _chunk_text(long_text)
        assert len(default_chunks) == MAX_CHUNKS_PER_SOURCE

    def test_max_chunks_default_is_3(self):
        """Default max_chunks should be MAX_CHUNKS_PER_SOURCE (3)."""
        long_text = "This is a paragraph.\n\n" * 500
        chunks = _chunk_text(long_text)

        assert len(chunks) <= MAX_CHUNKS_PER_SOURCE
