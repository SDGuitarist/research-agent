"""Tests for research_agent.decompose module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from research_agent.decompose import (
    decompose_query,
    _load_context,
    _validate_sub_queries,
    _parse_decomposition_response,
    _sanitize_for_prompt,
)


class TestSanitizeForPrompt:
    """Tests for _sanitize_for_prompt() function."""

    def test_escapes_angle_brackets(self):
        result = _sanitize_for_prompt("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_preserves_normal_text(self):
        text = "Normal text without special characters"
        assert _sanitize_for_prompt(text) == text

    def test_handles_empty_string(self):
        assert _sanitize_for_prompt("") == ""


class TestLoadContext:
    """Tests for _load_context() function."""

    def test_returns_content_when_file_exists(self, tmp_path):
        context_file = tmp_path / "research_context.md"
        context_file.write_text("# My Business\nSan Diego weddings")
        result = _load_context(context_file)
        assert result == "# My Business\nSan Diego weddings"

    def test_returns_none_when_file_missing(self, tmp_path):
        result = _load_context(tmp_path / "nonexistent.md")
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path):
        context_file = tmp_path / "empty.md"
        context_file.write_text("   \n  ")
        result = _load_context(context_file)
        assert result is None

    def test_handles_os_error_gracefully(self):
        # Path that will cause an OS error (directory, not file)
        result = _load_context(Path("/dev/null/impossible"))
        assert result is None


class TestValidateSubQueries:
    """Tests for _validate_sub_queries() function."""

    def test_accepts_valid_sub_queries(self):
        result = _validate_sub_queries(
            ["luxury wedding entertainment pricing", "San Diego venue music requirements"],
            "luxury wedding music market San Diego",
        )
        assert len(result) == 2

    def test_rejects_too_short_queries(self):
        result = _validate_sub_queries(
            ["wedding"],  # 1 word, below MIN_SUB_QUERY_WORDS
            "luxury wedding music market",
        )
        assert result == ["luxury wedding music market"]  # Falls back to original

    def test_rejects_too_long_queries(self):
        long_query = "this is a very long sub query that has way too many words in it to be useful"
        result = _validate_sub_queries(
            [long_query],
            "luxury wedding music",
        )
        assert result == ["luxury wedding music"]  # Falls back to original

    def test_rejects_queries_with_no_overlap(self):
        result = _validate_sub_queries(
            ["basketball statistics analysis"],  # No overlap with original
            "luxury wedding music market",
        )
        assert result == ["luxury wedding music market"]

    def test_rejects_near_duplicate_queries(self):
        result = _validate_sub_queries(
            [
                "luxury wedding entertainment pricing",
                "luxury wedding entertainment costs",  # Near duplicate
                "San Diego venue music requirements",
            ],
            "luxury wedding entertainment San Diego venue",
        )
        # Should keep first and third, reject second as duplicate
        assert len(result) == 2

    def test_caps_at_max_sub_queries(self):
        result = _validate_sub_queries(
            [
                "luxury wedding pricing data",
                "San Diego venue music needs",
                "live musician market rates",
                "flamenco guitar wedding trends",  # 4th should be capped
            ],
            "luxury wedding music San Diego flamenco",
        )
        assert len(result) <= 3

    def test_strips_formatting_from_queries(self):
        result = _validate_sub_queries(
            ["- luxury wedding pricing data", "• San Diego venue music"],
            "luxury wedding San Diego venue",
        )
        # Should strip leading - and • characters
        for sq in result:
            assert not sq.startswith("-")
            assert not sq.startswith("•")

    def test_returns_original_query_when_all_fail(self):
        result = _validate_sub_queries(
            ["x", "y"],  # All too short
            "luxury wedding music market",
        )
        assert result == ["luxury wedding music market"]


class TestParseDecompositionResponse:
    """Tests for _parse_decomposition_response() function."""

    def test_parses_simple_response(self):
        text = "TYPE: SIMPLE\nREASONING: This is a single-topic query"
        result = _parse_decomposition_response(text, "Python async best practices")
        assert result["is_complex"] is False
        assert result["sub_queries"] == ["Python async best practices"]
        assert "single-topic" in result["reasoning"]

    def test_parses_complex_response(self):
        text = (
            "TYPE: COMPLEX\n"
            "REASONING: This query spans pricing, geography, and market positioning\n"
            "SUB_QUERIES:\n"
            "- luxury wedding entertainment pricing\n"
            "- San Diego venue music requirements\n"
            "- live musician competitive rates"
        )
        result = _parse_decomposition_response(text, "wedding music market")
        assert result["is_complex"] is True
        assert len(result["sub_queries"]) >= 2

    def test_handles_missing_type(self):
        text = "REASONING: Something\nSUB_QUERIES:\n- query one\n- query two"
        result = _parse_decomposition_response(text, "original query")
        # Without TYPE: COMPLEX, defaults to SIMPLE
        assert result["is_complex"] is False
        assert result["sub_queries"] == ["original query"]

    def test_handles_complex_without_sub_queries(self):
        text = "TYPE: COMPLEX\nREASONING: Multiple angles needed"
        result = _parse_decomposition_response(text, "original query")
        # COMPLEX but no sub-queries → falls back to simple
        assert result["is_complex"] is False
        assert result["sub_queries"] == ["original query"]

    def test_handles_empty_response(self):
        result = _parse_decomposition_response("", "original query")
        assert result["is_complex"] is False
        assert result["sub_queries"] == ["original query"]


class TestDecomposeQuery:
    """Tests for decompose_query() function."""

    def test_simple_query_passthrough(self, mock_anthropic_response):
        """Simple query should return [original_query] unchanged."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: SIMPLE\nREASONING: Single clear topic about Python"
        )

        result = decompose_query(mock_client, "Python async best practices")

        assert result["is_complex"] is False
        assert result["sub_queries"] == ["Python async best practices"]

    def test_complex_query_decomposes(self, mock_anthropic_response):
        """Complex query should return multiple sub-queries."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: COMPLEX\n"
            "REASONING: This spans pricing, geography, and market analysis\n"
            "SUB_QUERIES:\n"
            "- luxury wedding entertainment pricing data\n"
            "- San Diego premium wedding venue requirements\n"
            "- live musician market competitive rates"
        )

        result = decompose_query(
            mock_client,
            "McKinsey-level research on San Diego luxury wedding music market",
        )

        assert result["is_complex"] is True
        assert len(result["sub_queries"]) >= 2

    def test_api_failure_falls_back_gracefully(self):
        """API errors should return [original_query], not crash."""
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="Service unavailable",
            request=MagicMock(),
            body=None,
        )

        result = decompose_query(mock_client, "test query")

        assert result["is_complex"] is False
        assert result["sub_queries"] == ["test query"]

    def test_empty_response_falls_back(self):
        """Empty API response should return [original_query]."""
        mock_client = MagicMock()
        response = MagicMock()
        response.content = []
        mock_client.messages.create.return_value = response

        result = decompose_query(mock_client, "test query")

        assert result["is_complex"] is False
        assert result["sub_queries"] == ["test query"]

    def test_loads_context_file_when_present(self, mock_anthropic_response, tmp_path):
        """Context file should be included in the API call."""
        context_file = tmp_path / "context.md"
        context_file.write_text("# My Business\nSan Diego luxury weddings")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: SIMPLE\nREASONING: Clear topic"
        )

        decompose_query(mock_client, "wedding trends", context_path=context_file)

        # Verify the context was included in the API call
        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "San Diego luxury weddings" in message_content

    def test_works_without_context_file(self, mock_anthropic_response):
        """Should work fine when no context file exists."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: SIMPLE\nREASONING: Clear topic"
        )

        result = decompose_query(
            mock_client, "test query",
            context_path=Path("/nonexistent/path.md"),
        )

        assert result["sub_queries"] == ["test query"]

    def test_sanitizes_query_in_prompt(self, mock_anthropic_response):
        """Query with angle brackets should be sanitized."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: SIMPLE\nREASONING: Simple query"
        )

        decompose_query(mock_client, "test <script>alert('xss')</script>")

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<script>" not in message_content
        assert "&lt;script&gt;" in message_content

    def test_rate_limit_error_falls_back(self):
        """RateLimitError should fall back gracefully."""
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        result = decompose_query(mock_client, "test query")

        assert result["is_complex"] is False
        assert result["sub_queries"] == ["test query"]

    def test_timeout_error_falls_back(self):
        """APITimeoutError should fall back gracefully."""
        from anthropic import APITimeoutError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APITimeoutError(
            request=MagicMock(),
        )

        result = decompose_query(mock_client, "test query")

        assert result["is_complex"] is False
        assert result["sub_queries"] == ["test query"]
