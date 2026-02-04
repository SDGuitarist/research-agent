"""Tests for research_agent.summarize module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from research_agent.summarize import (
    _sanitize_content,
    _chunk_text,
    summarize_chunk,
    summarize_content,
    summarize_all,
    Summary,
    CHUNK_SIZE,
    MAX_CHUNKS_PER_SOURCE,
)
from research_agent.extract import ExtractedContent


class TestSanitizeContent:
    """Tests for _sanitize_content() function."""

    def test_sanitize_content_escapes_angle_brackets(self):
        """Angle brackets should be escaped to prevent prompt injection."""
        result = _sanitize_content("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_sanitize_content_handles_empty_string(self):
        """Empty string should return empty string."""
        result = _sanitize_content("")
        assert result == ""

    def test_sanitize_content_handles_multiple_tags(self):
        """Multiple tag pairs should all be escaped."""
        result = _sanitize_content("<div><p>text</p></div>")
        assert result == "&lt;div&gt;&lt;p&gt;text&lt;/p&gt;&lt;/div&gt;"

    def test_sanitize_content_preserves_ampersands_in_text(self):
        """Regular ampersands in text should be preserved."""
        result = _sanitize_content("Tom & Jerry")
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
    async def test_summarize_chunk_propagates_rate_limit_error(self):
        """RateLimitError should be propagated (not swallowed)."""
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

        with pytest.raises(RateLimitError):
            await summarize_chunk(
                client=mock_client,
                chunk="Content",
                url="https://example.com",
                title="Test",
            )

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
