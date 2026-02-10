"""Tests for research_agent.synthesize module."""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.sanitize import sanitize_content
from research_agent.synthesize import (
    _deduplicate_summaries,
    _build_sources_context,
    _find_section,
    _splice_sections,
    validate_context_sections,
    regenerate_context_sections,
    synthesize_report,
)
from research_agent.summarize import Summary
from research_agent.errors import SynthesisError


class TestSanitizeContent:
    """Tests for sanitize_content() function."""

    def test_sanitize_content_escapes_angle_brackets(self):
        """Angle brackets should be escaped."""
        result = sanitize_content("<malicious>content</malicious>")
        assert result == "&lt;malicious&gt;content&lt;/malicious&gt;"

    def test_sanitize_content_handles_empty_string(self):
        """Empty string should return empty string."""
        result = sanitize_content("")
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

    def test_synthesize_report_includes_business_context_in_prompt(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Business context should appear in the prompt when provided."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                business_context="We are a guitar entertainment company.",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "<business_context>" in user_content
        assert "guitar entertainment company" in user_content

    def test_synthesize_report_omits_context_block_when_none(
        self, sample_summaries, mock_anthropic_stream
    ):
        """No business_context should produce no <business_context> block."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                business_context=None,
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "<business_context>" not in user_content
        assert "Competitive Implications" not in user_content

    def test_synthesize_report_sanitizes_business_context(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Business context with angle brackets should be escaped."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                business_context="<script>alert('xss')</script>",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "&lt;script&gt;" in user_content
        assert "<script>" not in user_content

    def test_synthesize_report_context_usage_instruction_present(
        self, sample_summaries, mock_anthropic_stream
    ):
        """When context is provided, usage instruction should be in prompt."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                business_context="Our company does X.",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "Competitive Implications" in user_content
        assert "Positioning Advice" in user_content
        assert "objective and context-free" in user_content

    def test_synthesize_report_passes_max_tokens_to_api(
        self, sample_summaries, mock_anthropic_stream
    ):
        """max_tokens parameter should be passed through to the API call."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                max_tokens=6000,
            )

        call_args = mock_client.messages.stream.call_args
        assert call_args.kwargs["max_tokens"] == 6000


# --- Business context validation tests ---

SAMPLE_REPORT = """# Research Report

## Executive Summary
This report covers competitor analysis.

## Company Overview
Acme Corp was founded in 2020.

## Service Portfolio
They offer DJ services and bands.

## Marketing Positioning
They position as premium entertainment.

## Messaging Theme Analysis
Authority and social proof patterns.

## Buyer Psychology
Fear of bad entertainment choices.

## Content & Marketing Tactics
Active on Instagram and Google Ads.

## Business Model Analysis
Revenue from booking commissions.

## Competitive Implications
Acme Corp threatens the local market. Pacific Flow Entertainment should
note their aggressive pricing strategy. Alex Guillen can differentiate
through cultural authenticity.

## Positioning Advice
Pacific Flow should emphasize consultation-first approach. Alex Guillen
Music can leverage the ceremony niche that Acme ignores.

## Limitations & Gaps
Limited financial data available.

## Sources
[Source 1] https://example.com
"""

SAMPLE_REPORT_NO_CONTEXT = """# Research Report

## Executive Summary
Overview of findings.

## Competitive Implications
Generic competition analysis without any business-specific references.
The market is growing and opportunities exist.

## Positioning Advice
Consider differentiating on quality and service. Invest in marketing
to reach more customers.

## Limitations & Gaps
Limited data.

## Sources
[Source 1] https://example.com
"""


class TestFindSection:
    """Tests for _find_section()."""

    def test_finds_section_by_title(self):
        section = _find_section(SAMPLE_REPORT, "Competitive Implications")
        assert "Pacific Flow Entertainment" in section
        assert "aggressive pricing" in section

    def test_finds_section_with_numbered_heading(self):
        report = "## 9. Competitive Implications\nContent here.\n\n## 10. Positioning Advice\n"
        section = _find_section(report, "Competitive Implications")
        assert "Content here" in section

    def test_returns_empty_for_missing_section(self):
        section = _find_section(SAMPLE_REPORT, "Nonexistent Section")
        assert section == ""

    def test_section_stops_at_next_heading(self):
        section = _find_section(SAMPLE_REPORT, "Competitive Implications")
        assert "Limitations" not in section
        assert "Positioning Advice" not in section

    def test_finds_positioning_advice_section(self):
        section = _find_section(SAMPLE_REPORT, "Positioning Advice")
        assert "consultation-first" in section
        assert "ceremony niche" in section


class TestValidateContextSections:
    """Tests for validate_context_sections()."""

    def test_returns_true_when_context_keywords_present(self):
        assert validate_context_sections(SAMPLE_REPORT, "some context") is True

    def test_returns_false_when_context_keywords_missing(self):
        assert validate_context_sections(SAMPLE_REPORT_NO_CONTEXT, "some context") is False

    def test_returns_true_when_no_business_context(self):
        assert validate_context_sections(SAMPLE_REPORT_NO_CONTEXT, None) is True

    def test_returns_true_when_sections_missing(self):
        report = "## Executive Summary\nJust a summary.\n"
        assert validate_context_sections(report, "some context") is True

    def test_detects_pacific_flow_keyword(self):
        report = "## Competitive Implications\nPacific Flow is well-positioned.\n## Sources\n"
        assert validate_context_sections(report, "ctx") is True

    def test_detects_alex_guillen_keyword(self):
        report = "## Positioning Advice\nAlex Guillen should focus on niche.\n## Sources\n"
        assert validate_context_sections(report, "ctx") is True

    def test_case_insensitive_keyword_match(self):
        report = "## Competitive Implications\npacific flow has advantages.\n## Sources\n"
        assert validate_context_sections(report, "ctx") is True


class TestSpliceSections:
    """Tests for _splice_sections()."""

    def test_splices_new_sections_into_report(self):
        new = "## Competitive Implications\nNew content.\n\n## Positioning Advice\nNew advice.\n"
        result = _splice_sections(SAMPLE_REPORT, new)
        assert "New content." in result
        assert "New advice." in result
        # Surrounding sections should be preserved
        assert "Executive Summary" in result
        assert "Limitations & Gaps" in result

    def test_returns_original_when_section_not_found(self):
        report = "## Executive Summary\nJust a summary.\n"
        result = _splice_sections(report, "## New Section\n")
        assert result == report

    def test_preserves_content_before_and_after(self):
        new = "## Competitive Implications\nUpdated.\n\n## Positioning Advice\nUpdated advice.\n"
        result = _splice_sections(SAMPLE_REPORT, new)
        assert "Business Model Analysis" in result
        assert "Limitations & Gaps" in result


class TestRegenerateContextSections:
    """Tests for regenerate_context_sections()."""

    def test_calls_api_and_splices_result(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=(
            "## Competitive Implications\nPacific Flow faces competition.\n\n"
            "## Positioning Advice\nAlex Guillen should leverage cultural niche.\n"
        ))]
        mock_client.messages.create.return_value = mock_response

        result = regenerate_context_sections(
            mock_client, SAMPLE_REPORT_NO_CONTEXT, "Pacific Flow context"
        )

        assert "Pacific Flow faces competition" in result
        mock_client.messages.create.assert_called_once()

    def test_returns_original_on_api_error(self):
        from anthropic import APIError
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="fail", request=MagicMock(), body=None
        )

        result = regenerate_context_sections(
            mock_client, SAMPLE_REPORT_NO_CONTEXT, "context"
        )

        assert result == SAMPLE_REPORT_NO_CONTEXT

    def test_returns_original_on_empty_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="")]
        mock_client.messages.create.return_value = mock_response

        result = regenerate_context_sections(
            mock_client, SAMPLE_REPORT_NO_CONTEXT, "context"
        )

        assert result == SAMPLE_REPORT_NO_CONTEXT

    def test_sanitizes_business_context(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="## Competitive Implications\nNew.\n\n## Positioning Advice\nNew.\n")]
        mock_client.messages.create.return_value = mock_response

        regenerate_context_sections(
            mock_client, SAMPLE_REPORT_NO_CONTEXT, "<script>xss</script>"
        )

        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "&lt;script&gt;" in prompt
        assert "<script>" not in prompt
