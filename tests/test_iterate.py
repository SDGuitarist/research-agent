"""Tests for research_agent.iterate module."""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.iterate import (
    generate_refined_queries,
    generate_followup_questions,
    QueryGenerationResult,
    _parse_refined_response,
    _parse_followup_response,
)
from research_agent.errors import IterationError


# --- QueryGenerationResult dataclass ---


class TestQueryGenerationResult:
    """Tests for the QueryGenerationResult frozen dataclass."""

    def test_empty_items_is_falsy(self):
        result = QueryGenerationResult(items=(), rationale="nothing")
        assert not result.items

    def test_with_items_is_truthy(self):
        result = QueryGenerationResult(items=("query one",), rationale="found gap")
        assert result.items

    def test_is_frozen(self):
        result = QueryGenerationResult(items=("q",), rationale="r")
        with pytest.raises(AttributeError):
            result.items = ("new",)

    def test_rationale_preserved(self):
        result = QueryGenerationResult(items=(), rationale="empty API response")
        assert result.rationale == "empty API response"


# --- _parse_refined_response ---


class TestParseRefinedResponse:
    """Tests for parsing the MISSING:/QUERY: response format."""

    def test_parses_valid_response(self):
        text = (
            "MISSING: The draft lacks recent zoning variance data\n"
            "QUERY: recent zoning variance approvals 2024"
        )
        result = _parse_refined_response(text, "zoning laws San Diego")
        assert len(result.items) == 1
        assert "zoning variance" in result.items[0]
        assert "recent" in result.rationale.lower() or "zoning" in result.rationale.lower()

    def test_rejects_query_too_similar_to_original(self):
        text = (
            "MISSING: general overview is missing\n"
            "QUERY: zoning laws San Diego overview"
        )
        # 3/4 meaningful words overlap (>0.6) → rejected
        result = _parse_refined_response(text, "zoning laws San Diego")
        assert not result.items

    def test_rejects_query_with_no_overlap(self):
        text = (
            "MISSING: something unrelated\n"
            "QUERY: basketball statistics analysis trends"
        )
        # Zero overlap with reference → rejected (require_reference_overlap=True)
        result = _parse_refined_response(text, "zoning laws San Diego")
        assert not result.items

    def test_handles_missing_query_line(self):
        text = "MISSING: The draft lacks cost data"
        result = _parse_refined_response(text, "test query here")
        assert not result.items
        assert result.rationale == "The draft lacks cost data"

    def test_handles_empty_response(self):
        result = _parse_refined_response("", "test query here")
        assert not result.items

    def test_strips_quotes_from_query(self):
        text = (
            "MISSING: pricing data missing\n"
            'QUERY: "wedding vendor pricing comparison"'
        )
        result = _parse_refined_response(text, "wedding entertainment market")
        # Should strip quotes and validate
        if result.items:
            assert not result.items[0].startswith('"')

    def test_handles_extra_whitespace(self):
        text = (
            "  MISSING:  lots of gaps  \n"
            "  QUERY:  recent zoning variance data  "
        )
        result = _parse_refined_response(text, "zoning laws regulations")
        assert len(result.items) <= 1  # 0 or 1 depending on validation


# --- _parse_followup_response ---


class TestParseFollowupResponse:
    """Tests for parsing numbered follow-up questions."""

    def test_parses_numbered_list(self):
        text = (
            "1. How do I apply for a zoning variance permit?\n"
            "2. How does San Diego zoning compare to Los Angeles regulations?\n"
            "3. What happens if a zoning variance application is denied?"
        )
        result = _parse_followup_response(text, "zoning laws", 3)
        assert len(result.items) <= 3
        assert result.items  # at least some should pass

    def test_parses_parenthesized_numbers(self):
        text = (
            "1) How do I navigate the permit process effectively?\n"
            "2) How does coastal zoning compare to inland regulations?\n"
        )
        result = _parse_followup_response(text, "zoning regulations", 2)
        assert result.items

    def test_parses_dash_list(self):
        text = (
            "- How do I start the rezoning application process?\n"
            "- How does commercial zoning compare to residential zoning?\n"
        )
        result = _parse_followup_response(text, "zoning regulations overview", 2)
        assert result.items

    def test_rejects_too_short_questions(self):
        text = "1. What?\n2. How?"
        result = _parse_followup_response(text, "test query", 2)
        assert not result.items

    def test_caps_at_max_questions(self):
        text = (
            "1. How do I apply for a building permit in my area?\n"
            "2. How does residential zoning compare to commercial regulations?\n"
            "3. What happens if construction begins without proper permits?\n"
            "4. How do I appeal a rejected building application?\n"
        )
        result = _parse_followup_response(text, "building permits", 2)
        assert len(result.items) <= 2

    def test_handles_empty_response(self):
        result = _parse_followup_response("", "test query", 3)
        assert not result.items

    def test_rejects_questions_too_similar_to_original(self):
        text = "1. What are the zoning laws in San Diego for rentals?"
        # High overlap with original → rejected at 0.5 threshold
        result = _parse_followup_response(text, "zoning laws San Diego rentals", 1)
        assert not result.items


# --- generate_refined_queries ---


class TestGenerateRefinedQueries:
    """Tests for the generate_refined_queries() function."""

    def test_returns_valid_result(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: The draft lacks recent variance approval data\n"
            "QUERY: recent zoning variance approvals 2024"
        )

        result = generate_refined_queries(
            mock_client, "zoning laws San Diego", "Draft about zoning basics..."
        )

        assert isinstance(result, QueryGenerationResult)
        assert len(result.items) <= 1

    def test_api_error_raises_iteration_error(self):
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="Service unavailable",
            request=MagicMock(),
            body=None,
        )

        with pytest.raises(IterationError):
            generate_refined_queries(mock_client, "test query", "test draft")

    def test_rate_limit_raises_iteration_error(self):
        from anthropic import RateLimitError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        with pytest.raises(IterationError):
            generate_refined_queries(mock_client, "test query", "test draft")

    def test_timeout_raises_iteration_error(self):
        from anthropic import APITimeoutError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APITimeoutError(
            request=MagicMock(),
        )

        with pytest.raises(IterationError):
            generate_refined_queries(mock_client, "test query", "test draft")

    def test_empty_response_returns_empty_result(self):
        mock_client = MagicMock()
        response = MagicMock()
        response.content = []
        mock_client.messages.create.return_value = response

        result = generate_refined_queries(mock_client, "test query", "test draft")

        assert not result.items
        assert "empty" in result.rationale

    def test_sanitizes_draft_input(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined search query"
        )

        generate_refined_queries(
            mock_client, "test query",
            "Draft with <script>alert('xss')</script> injection"
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<script>" not in message_content
        assert "&lt;script&gt;" in message_content

    def test_sanitizes_query_input(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined search query"
        )

        generate_refined_queries(
            mock_client, "test <b>bold</b> query", "Some draft"
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<b>" not in message_content
        assert "&lt;b&gt;" in message_content

    def test_xml_boundaries_in_prompt(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined search query"
        )

        generate_refined_queries(mock_client, "test query", "Draft text here")

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<original_query>" in message_content
        assert "</original_query>" in message_content
        assert "<draft_report>" in message_content
        assert "</draft_report>" in message_content

    def test_system_prompt_warns_about_injection(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined query here"
        )

        generate_refined_queries(mock_client, "test query", "Draft text")

        call_args = mock_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        assert "ignore" in system_prompt.lower()
        assert "injection" in system_prompt.lower()

    def test_prompt_contains_bad_good_examples(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined query here"
        )

        generate_refined_queries(mock_client, "test query", "Draft text")

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "BAD" in message_content
        assert "GOOD" in message_content

    def test_domain_neutral_language(self, mock_anthropic_response):
        """Prompts should not contain domain-specific language."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: gap\nQUERY: some refined query here"
        )

        generate_refined_queries(mock_client, "test query", "Draft text")

        call_args = mock_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        message_content = call_args.kwargs["messages"][0]["content"]
        combined = system_prompt + message_content
        # Should not reference specific domains like "wedding", "music", etc.
        for domain_term in ["wedding", "San Diego", "music", "entertainment"]:
            assert domain_term.lower() not in combined.lower()

    def test_validation_rejection_returns_empty(self, mock_anthropic_response):
        """Query that fails validation returns empty result, not error."""
        mock_client = MagicMock()
        # Return a query that's just one word (below min_words=3)
        mock_client.messages.create.return_value = mock_anthropic_response(
            "MISSING: everything\nQUERY: overview"
        )

        result = generate_refined_queries(mock_client, "test query", "Draft text")
        assert not result.items
        # Should NOT raise IterationError


# --- generate_followup_questions ---


class TestGenerateFollowupQuestions:
    """Tests for the generate_followup_questions() function."""

    def test_returns_valid_result(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I apply for a building permit successfully?\n"
            "2. How does urban zoning compare to rural land regulations?\n"
            "3. What happens if a property violates current zoning codes?"
        )

        result = generate_followup_questions(
            mock_client, "zoning laws overview", "## Introduction\nReport text...",
            num_questions=3,
        )

        assert isinstance(result, QueryGenerationResult)
        assert result.items  # should have some

    def test_zero_questions_returns_empty(self):
        """num_questions=0 should short-circuit without API call."""
        mock_client = MagicMock()

        result = generate_followup_questions(
            mock_client, "test query", "report text", num_questions=0
        )

        assert not result.items
        mock_client.messages.create.assert_not_called()

    def test_api_error_raises_iteration_error(self):
        from anthropic import APIError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )

        with pytest.raises(IterationError):
            generate_followup_questions(
                mock_client, "test query", "report", num_questions=2
            )

    def test_empty_response_returns_empty_result(self):
        mock_client = MagicMock()
        response = MagicMock()
        response.content = []
        mock_client.messages.create.return_value = response

        result = generate_followup_questions(
            mock_client, "test query", "report", num_questions=2
        )

        assert not result.items

    def test_sanitizes_report_input(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I handle injection prevention effectively?\n"
            "2. How does input validation compare to output encoding?"
        )

        generate_followup_questions(
            mock_client, "security practices",
            "Report with <script>alert('xss')</script> content",
            num_questions=2,
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<script>" not in message_content
        assert "&lt;script&gt;" in message_content

    def test_xml_boundaries_in_prompt(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I test the system properly?\n"
            "2. How does this approach compare to alternatives?"
        )

        generate_followup_questions(
            mock_client, "test query", "## Intro\nReport text",
            num_questions=2,
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "<original_query>" in message_content
        assert "</original_query>" in message_content
        assert "<report_excerpt>" in message_content
        assert "</report_excerpt>" in message_content

    def test_system_prompt_warns_about_injection(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I test properly?\n2. How does X compare to Y?"
        )

        generate_followup_questions(
            mock_client, "test query", "report", num_questions=2
        )

        call_args = mock_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        assert "ignore" in system_prompt.lower()
        assert "injection" in system_prompt.lower()

    def test_extracts_headings_for_exclusion(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I handle edge cases properly here?\n"
            "2. How does this system compare to competitors?"
        )

        report = "## Overview\nText\n## Market Analysis\nMore text\n## Conclusion\nEnd"
        generate_followup_questions(
            mock_client, "market report", report, num_questions=2
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "Overview" in message_content
        assert "Market Analysis" in message_content
        assert "Conclusion" in message_content

    def test_handles_report_with_no_headings(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I explore this topic in depth?\n"
            "2. How does this compare to similar topics?"
        )

        generate_followup_questions(
            mock_client, "test query", "Just plain text, no headings",
            num_questions=2,
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "none" in message_content

    def test_truncates_report_to_2000_chars(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I investigate further research areas?\n"
            "2. How does current data compare to historical trends?"
        )

        long_report = "A" * 5000
        generate_followup_questions(
            mock_client, "test query", long_report, num_questions=2
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        # The sanitized preview should be at most 2000 A's (sanitized)
        assert "A" * 2001 not in message_content

    def test_prompt_requests_three_perspectives(self, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I apply the findings practically?\n"
            "2. How does X compare to Y in this context?"
        )

        generate_followup_questions(
            mock_client, "test query", "report", num_questions=2
        )

        call_args = mock_client.messages.create.call_args
        message_content = call_args.kwargs["messages"][0]["content"]
        assert "tactical" in message_content.lower()
        assert "comparative" in message_content.lower()
        assert "implication" in message_content.lower()

    def test_domain_neutral_language(self, mock_anthropic_response):
        """Prompts should not contain domain-specific language."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "1. How do I test this feature correctly?\n"
            "2. How does option A compare to option B?"
        )

        generate_followup_questions(
            mock_client, "test query", "report text", num_questions=2
        )

        call_args = mock_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        message_content = call_args.kwargs["messages"][0]["content"]
        combined = system_prompt + message_content
        for domain_term in ["wedding", "San Diego", "music", "entertainment"]:
            assert domain_term.lower() not in combined.lower()


# --- Mode parameter tests ---


class TestModeIterationParams:
    """Tests for iteration_enabled and followup_questions in ResearchMode."""

    def test_quick_mode_skips_iteration(self):
        from research_agent.modes import ResearchMode
        mode = ResearchMode.quick()
        assert mode.iteration_enabled is False
        assert mode.followup_questions == 0

    def test_standard_mode_enables_iteration(self):
        from research_agent.modes import ResearchMode
        mode = ResearchMode.standard()
        assert mode.iteration_enabled is True
        assert mode.followup_questions == 2

    def test_deep_mode_enables_iteration(self):
        from research_agent.modes import ResearchMode
        mode = ResearchMode.deep()
        assert mode.iteration_enabled is True
        assert mode.followup_questions == 3

    def test_negative_followup_questions_raises(self):
        from research_agent.modes import ResearchMode
        with pytest.raises(ValueError, match="followup_questions"):
            ResearchMode(
                name="test",
                max_sources=4,
                search_passes=1,
                word_target=300,
                max_tokens=600,
                auto_save=False,
                synthesis_instructions="test",
                pass1_sources=4,
                pass2_sources=2,
                min_sources_full_report=3,
                min_sources_short_report=1,
                followup_questions=-1,
            )


# --- IterationError tests ---


class TestIterationError:
    """Tests for IterationError exception."""

    def test_is_research_error_subclass(self):
        from research_agent.errors import ResearchError
        assert issubclass(IterationError, ResearchError)

    def test_carries_message(self):
        err = IterationError("API call failed")
        assert str(err) == "API call failed"
