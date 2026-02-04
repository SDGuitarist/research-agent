"""Tests for research_agent.synthesize module."""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.synthesize import (
    _sanitize_content,
    _deduplicate_summaries,
    _build_sources_context,
    synthesize_report,
)
from research_agent.summarize import Summary
from research_agent.errors import SynthesisError


class TestSanitizeContent:
    """Tests for _sanitize_content() function."""

    def test_sanitize_content_escapes_angle_brackets(self):
        """Angle brackets should be escaped."""
        result = _sanitize_content("<malicious>content</malicious>")
        assert result == "&lt;malicious&gt;content&lt;/malicious&gt;"

    def test_sanitize_content_handles_empty_string(self):
        """Empty string should return empty string."""
        result = _sanitize_content("")
        assert result == ""


class TestDeduplicateSummaries:
    """Tests for _deduplicate_summaries() function."""

    def test_deduplicate_summaries_removes_exact_duplicates(self):
        """Identical strings should be deduplicated."""
        summaries = [
            "First summary about topic.",
            "First summary about topic.",
            "Second summary with different content.",
        ]

        result = _deduplicate_summaries(summaries)

        assert len(result) == 2
        assert "First summary about topic." in result
        assert "Second summary with different content." in result

    def test_deduplicate_summaries_normalizes_whitespace(self):
        """Summaries differing only in whitespace should match."""
        summaries = [
            "Summary  with   extra spaces.",
            "Summary with extra spaces.",
            "Different summary.",
        ]

        result = _deduplicate_summaries(summaries)

        assert len(result) == 2

    def test_deduplicate_summaries_preserves_order(self):
        """First occurrence should be kept, maintaining order."""
        summaries = [
            "First",
            "Second",
            "First",  # Duplicate
            "Third",
        ]

        result = _deduplicate_summaries(summaries)

        assert result == ["First", "Second", "Third"]

    def test_deduplicate_summaries_handles_empty_list(self):
        """Empty list should return empty list."""
        result = _deduplicate_summaries([])
        assert result == []

    def test_deduplicate_summaries_keeps_unique_summaries(self):
        """Distinct summaries should all be preserved."""
        summaries = [
            "Summary one.",
            "Summary two.",
            "Summary three.",
        ]

        result = _deduplicate_summaries(summaries)

        assert len(result) == 3
        assert result == summaries


class TestBuildSourcesContext:
    """Tests for _build_sources_context() function."""

    def test_build_sources_context_formats_summaries(self, sample_summaries):
        """Should format summaries with source tags and IDs."""
        result = _build_sources_context(sample_summaries)

        assert '<source id="1">' in result
        assert '<source id="2">' in result
        assert "<title>" in result
        assert "<url>" in result
        assert "<summary>" in result

    def test_build_sources_context_groups_by_url(self):
        """Multiple summaries from same URL should be combined."""
        summaries = [
            Summary(url="https://example.com", title="Title", summary="Part 1"),
            Summary(url="https://example.com", title="Title", summary="Part 2"),
            Summary(url="https://other.com", title="Other", summary="Different"),
        ]

        result = _build_sources_context(summaries)

        # Should have 2 sources, not 3
        assert result.count('<source id="') == 2
        # First source should contain both parts
        assert "Part 1" in result
        assert "Part 2" in result

    def test_build_sources_context_sanitizes_content(self):
        """Titles and summaries should be sanitized."""
        summaries = [
            Summary(
                url="https://example.com",
                title="<script>Title</script>",
                summary="<malicious>Summary</malicious>"
            ),
        ]

        result = _build_sources_context(summaries)

        assert "&lt;script&gt;" in result
        assert "<script>" not in result
        assert "&lt;malicious&gt;" in result

    def test_build_sources_context_handles_missing_title(self):
        """Missing title should default to 'Untitled'."""
        summaries = [
            Summary(url="https://example.com", title="", summary="Summary text"),
        ]

        result = _build_sources_context(summaries)

        assert "<title>Untitled</title>" in result


class TestSynthesizeReport:
    """Tests for synthesize_report() function."""

    def test_synthesize_report_returns_markdown_on_success(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Successful synthesis should return markdown report."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream([
            "# Research Report\n\n",
            "## Summary\n\n",
            "Key findings from research.",
        ])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):  # Suppress streaming output
            result = synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
            )

        assert "# Research Report" in result
        assert "Key findings" in result

    def test_synthesize_report_raises_on_empty_summaries(self):
        """Empty summaries list should raise SynthesisError."""
        mock_client = MagicMock()

        with pytest.raises(SynthesisError, match="No summaries to synthesize"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=[],
            )

    def test_synthesize_report_raises_on_rate_limit(self, sample_summaries):
        """RateLimitError should be wrapped in SynthesisError."""
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_client.messages.stream.side_effect = RateLimitError(
            message="Rate limited",
            response=mock_response,
            body=None
        )

        with pytest.raises(SynthesisError, match="Rate limited"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
            )

    def test_synthesize_report_raises_on_timeout(self, sample_summaries):
        """APITimeoutError should be wrapped in SynthesisError."""
        from anthropic import APITimeoutError

        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.messages.stream.side_effect = APITimeoutError(request=mock_request)

        with pytest.raises(SynthesisError, match="timed out"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
            )

    def test_synthesize_report_raises_on_empty_response(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Empty stream response should raise SynthesisError."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream([])  # Empty stream
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            with pytest.raises(SynthesisError, match="empty response"):
                synthesize_report(
                    client=mock_client,
                    query="test query",
                    summaries=sample_summaries,
                )

    def test_synthesize_report_uses_mode_instructions(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Mode instructions should be included in the prompt."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        custom_instructions = "Write a brief 100 word summary."

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                mode_instructions=custom_instructions,
            )

        call_args = mock_client.messages.stream.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        assert custom_instructions in user_content

    def test_synthesize_report_sanitizes_query(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Query with special characters should be sanitized."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="<malicious>query</malicious>",
                summaries=sample_summaries,
            )

        call_args = mock_client.messages.stream.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        assert "&lt;malicious&gt;" in user_content
        assert "<malicious>" not in user_content
