"""Tests for research_agent.search module."""

import pytest
from unittest.mock import patch, MagicMock

from research_agent.search import (
    search,
    _sanitize_for_prompt,
    refine_query,
    SearchResult,
)
from research_agent.errors import SearchError


class TestSanitizeForPrompt:
    """Tests for _sanitize_for_prompt() function."""

    def test_sanitize_for_prompt_escapes_angle_brackets(self):
        """Angle brackets should be escaped to prevent prompt injection."""
        result = _sanitize_for_prompt("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert('xss')&lt;/script&gt;"

    def test_sanitize_for_prompt_handles_empty_string(self):
        """Empty string should return empty string."""
        result = _sanitize_for_prompt("")
        assert result == ""

    def test_sanitize_for_prompt_preserves_normal_text(self):
        """Text without special characters should be unchanged."""
        text = "This is normal text with no special chars."
        result = _sanitize_for_prompt(text)
        assert result == text

    def test_sanitize_for_prompt_escapes_nested_tags(self):
        """Nested or system-like tags should be escaped."""
        result = _sanitize_for_prompt("</system><user>malicious</user>")
        assert result == "&lt;/system&gt;&lt;user&gt;malicious&lt;/user&gt;"

    def test_sanitize_for_prompt_handles_multiple_brackets(self):
        """Multiple bracket pairs should all be escaped."""
        result = _sanitize_for_prompt("<a><b><c>")
        assert result == "&lt;a&gt;&lt;b&gt;&lt;c&gt;"


class TestSearch:
    """Tests for search() function."""

    def test_search_returns_results_on_success(self, mock_ddgs_results):
        """Successful search should return list of SearchResult objects."""
        mock_results = mock_ddgs_results(3)

        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            mock_instance.text.return_value = mock_results
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            results = search("test query", max_results=5)

            assert len(results) == 3
            assert all(isinstance(r, SearchResult) for r in results)
            assert results[0].title == "Result 1"
            assert results[0].url == "https://example1.com/page"

    def test_search_raises_error_on_empty_results(self):
        """Empty results should raise SearchError."""
        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            with pytest.raises(SearchError, match="No results found"):
                search("obscure query with no results")

    def test_search_retries_on_rate_limit(self, mock_ddgs_results):
        """RatelimitException should trigger retry with backoff."""
        from ddgs.exceptions import RatelimitException

        mock_results = mock_ddgs_results(2)

        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            # First call raises, second succeeds
            mock_instance.text.side_effect = [
                RatelimitException("rate limited"),
                mock_results,
            ]
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            with patch("research_agent.search.time.sleep"):  # Skip actual sleep
                results = search("test query")

                assert len(results) == 2
                assert mock_instance.text.call_count == 2

    def test_search_respects_max_results(self, mock_ddgs_results):
        """max_results parameter should be passed to DDGS."""
        mock_results = mock_ddgs_results(3)

        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            mock_instance.text.return_value = mock_results
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            search("test query", max_results=10)

            mock_instance.text.assert_called_once_with("test query", max_results=10)

    def test_search_filters_results_without_url(self, mock_ddgs_results):
        """Results without href should be filtered out."""
        mock_results = [
            {"title": "Has URL", "href": "https://example.com", "body": "snippet"},
            {"title": "No URL", "href": "", "body": "snippet"},
            {"title": "Missing href", "body": "snippet"},  # No href key
        ]

        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            mock_instance.text.return_value = mock_results
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            results = search("test query")

            assert len(results) == 1
            assert results[0].title == "Has URL"

    def test_search_raises_after_max_retries(self):
        """Should raise SearchError after exhausting retries."""
        from ddgs.exceptions import RatelimitException

        with patch("research_agent.search.DDGS") as mock_ddgs_class:
            mock_instance = MagicMock()
            mock_instance.text.side_effect = RatelimitException("rate limited")
            mock_ddgs_class.return_value.__enter__.return_value = mock_instance

            with patch("research_agent.search.time.sleep"):  # Skip actual sleep
                with pytest.raises(SearchError, match="Search failed"):
                    search("test query")


class TestRefineQuery:
    """Tests for refine_query() function."""

    def test_refine_query_returns_refined_query_on_success(self, mock_anthropic_response):
        """Successful refinement should return the refined query."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Python async concurrency patterns"
        )

        summaries = ["Summary about asyncio basics", "Summary about await patterns"]
        result = refine_query(mock_client, "python async", summaries)

        assert result == "Python async concurrency patterns"
        mock_client.messages.create.assert_called_once()

    def test_refine_query_returns_original_on_api_error(self):
        """APIError should fall back to original query."""
        from anthropic import APIError

        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="API error",
            request=mock_request,
            body=None
        )

        result = refine_query(mock_client, "original query", ["summary"])

        assert result == "original query"

    def test_refine_query_returns_original_on_rate_limit(self):
        """RateLimitError should fall back to original query."""
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_client.messages.create.side_effect = RateLimitError(
            message="Rate limited",
            response=mock_response,
            body=None
        )

        result = refine_query(mock_client, "original query", ["summary"])

        assert result == "original query"

    def test_refine_query_returns_original_on_empty_response(self, mock_anthropic_response):
        """Empty response content should fall back to original query."""
        mock_client = MagicMock()
        response = MagicMock()
        response.content = []  # Empty content list
        mock_client.messages.create.return_value = response

        result = refine_query(mock_client, "original query", ["summary"])

        assert result == "original query"

    def test_refine_query_sanitizes_summaries(self, mock_anthropic_response):
        """Summaries with special characters should be sanitized."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response("refined query")

        summaries = ["<script>malicious</script> summary"]
        refine_query(mock_client, "test query", summaries)

        # Check that the call was made with sanitized content
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        assert "&lt;script&gt;" in user_content
        assert "<script>" not in user_content

    def test_refine_query_truncates_long_summaries(self, mock_anthropic_response):
        """Long summaries should be truncated to 150 chars."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response("refined query")

        long_summary = "x" * 200  # Over 150 chars
        refine_query(mock_client, "test query", [long_summary])

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        # Should be truncated and end with ...
        assert "..." in user_content
        # Should not contain full 200 chars
        assert "x" * 200 not in user_content

    def test_refine_query_strips_quotes_from_response(self, mock_anthropic_response):
        """Quotes around the refined query should be stripped."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            '"python async patterns"'
        )

        result = refine_query(mock_client, "test query", ["summary"])

        assert result == "python async patterns"

    def test_refine_query_limits_summaries_to_ten(self, mock_anthropic_response):
        """Only first 10 summaries should be used."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response("refined")

        summaries = [f"Summary {i}" for i in range(15)]
        refine_query(mock_client, "test query", summaries)

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[0]["content"]

        # Should have summaries 0-9 but not 10-14
        assert "Summary 9" in user_content
        assert "Summary 10" not in user_content
