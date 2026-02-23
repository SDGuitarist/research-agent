"""Tests for research_agent.decompose module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from research_agent.decompose import (
    decompose_query,
    DecompositionResult,
    _validate_sub_queries,
    _parse_decomposition_response,
)
from research_agent.context import load_full_context
from research_agent.context_result import ContextResult, ContextStatus


class TestLoadContext:
    """Tests for load_full_context() function (moved to context module)."""

    def test_returns_content_when_file_exists(self, tmp_path):
        context_file = tmp_path / "research_context.md"
        context_file.write_text("# My Business\nSan Diego weddings")
        result = load_full_context(context_file)
        assert result.status == ContextStatus.LOADED
        assert result.content == "# My Business\nSan Diego weddings"

    def test_returns_not_configured_when_file_missing(self, tmp_path):
        result = load_full_context(tmp_path / "nonexistent.md")
        assert result.status == ContextStatus.NOT_CONFIGURED
        assert result.content is None

    def test_returns_empty_for_empty_file(self, tmp_path):
        context_file = tmp_path / "empty.md"
        context_file.write_text("   \n  ")
        result = load_full_context(context_file)
        assert result.status == ContextStatus.EMPTY
        assert result.content is None

    def test_handles_os_error_gracefully(self, tmp_path):
        # Create a directory where a file is expected to force read_text() to raise
        fake_file = tmp_path / "context.md"
        fake_file.mkdir()
        result = load_full_context(fake_file)
        assert result.status == ContextStatus.FAILED
        assert result.error != ""


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


class TestSubQueryDivergence:
    """Tests for max overlap rejection between sub-queries and original."""

    def test_rejects_restatement_of_original(self):
        """Sub-query that rearranges original words is rejected."""
        result = _validate_sub_queries(
            ["McKinsey luxury wedding market analysis"],  # 4/5 = 80% overlap
            "McKinsey wedding entertainment trends luxury market",
        )
        assert result == ["McKinsey wedding entertainment trends luxury market"]

    def test_accepts_divergent_sub_queries(self):
        """Sub-queries with <80% overlap pass validation."""
        result = _validate_sub_queries(
            [
                "wedding entertainment spending consumer trends",  # 3/5 = 60%
                "luxury event vendor market landscape",            # 2/5 = 40%
            ],
            "McKinsey wedding entertainment trends luxury market",
        )
        assert len(result) == 2

    def test_mixed_overlap_keeps_only_divergent(self):
        """Restatements rejected, divergent queries kept."""
        result = _validate_sub_queries(
            [
                "McKinsey luxury wedding market trends",       # 5/5 = 100% → REJECT
                "luxury event vendor competitive pricing",     # 1/5 = 20%  → KEEP
                "wedding consumer behavior spending data",     # 1/5 = 20%  → KEEP
            ],
            "McKinsey wedding entertainment trends luxury market",
        )
        assert len(result) == 2
        assert "McKinsey luxury wedding market trends" not in result


class TestParseDecompositionResponse:
    """Tests for _parse_decomposition_response() function."""

    def test_parses_simple_response(self):
        text = "TYPE: SIMPLE\nREASONING: This is a single-topic query"
        result = _parse_decomposition_response(text, "Python async best practices")
        assert isinstance(result, DecompositionResult)
        assert result.is_complex is False
        assert result.sub_queries == ("Python async best practices",)
        assert "single-topic" in result.reasoning

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
        assert result.is_complex is True
        assert len(result.sub_queries) >= 2

    def test_handles_missing_type(self):
        text = "REASONING: Something\nSUB_QUERIES:\n- query one\n- query two"
        result = _parse_decomposition_response(text, "original query")
        # Without TYPE: COMPLEX, defaults to SIMPLE
        assert result.is_complex is False
        assert result.sub_queries == ("original query",)

    def test_handles_complex_without_sub_queries(self):
        text = "TYPE: COMPLEX\nREASONING: Multiple angles needed"
        result = _parse_decomposition_response(text, "original query")
        # COMPLEX but no sub-queries → falls back to simple
        assert result.is_complex is False
        assert result.sub_queries == ("original query",)

    def test_handles_empty_response(self):
        result = _parse_decomposition_response("", "original query")
        assert result.is_complex is False
        assert result.sub_queries == ("original query",)


class TestDecomposeQuery:
    """Tests for decompose_query() function."""

    def test_simple_query_passthrough(self, mock_anthropic_response):
        """Simple query should return (original_query,) unchanged."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "TYPE: SIMPLE\nREASONING: Single clear topic about Python"
        )

        result = decompose_query(mock_client, "Python async best practices")

        assert isinstance(result, DecompositionResult)
        assert result.is_complex is False
        assert result.sub_queries == ("Python async best practices",)

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

        assert result.is_complex is True
        assert len(result.sub_queries) >= 2

    def test_api_failure_falls_back_gracefully(self):
        """API errors should return (original_query,), not crash."""
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="Service unavailable",
            request=MagicMock(),
            body=None,
        )

        result = decompose_query(mock_client, "test query")

        assert result.is_complex is False
        assert result.sub_queries == ("test query",)

    def test_empty_response_falls_back(self):
        """Empty API response should return (original_query,)."""
        mock_client = MagicMock()
        response = MagicMock()
        response.content = []
        mock_client.messages.create.return_value = response

        result = decompose_query(mock_client, "test query")

        assert result.is_complex is False
        assert result.sub_queries == ("test query",)

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

        assert result.sub_queries == ("test query",)

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

        assert result.is_complex is False
        assert result.sub_queries == ("test query",)

    def test_timeout_error_falls_back(self):
        """APITimeoutError should fall back gracefully."""
        from anthropic import APITimeoutError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APITimeoutError(
            request=MagicMock(),
        )

        result = decompose_query(mock_client, "test query")

        assert result.is_complex is False
        assert result.sub_queries == ("test query",)


class TestCritiqueGuidanceParam:
    """Tests for critique_guidance parameter in decompose_query."""

    def test_none_produces_same_prompt(self):
        """critique_guidance=None should not add critique block."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="TYPE: SIMPLE\nREASONING: simple query\nSUB_QUERIES:\n")]
        )

        decompose_query(mock_client, "test query", critique_guidance=None)
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "<critique_guidance>" not in prompt

    def test_provided_adds_critique_block(self):
        """critique_guidance should inject critique_guidance block."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="TYPE: SIMPLE\nREASONING: ok\nSUB_QUERIES:\n")]
        )

        decompose_query(
            mock_client, "test query",
            critique_guidance="Improve source diversity",
        )
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "<critique_guidance>" in prompt
        assert "Improve source diversity" in prompt
