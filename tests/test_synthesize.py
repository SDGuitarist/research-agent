"""Tests for research_agent.synthesize module."""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.sanitize import sanitize_content
from research_agent.synthesize import (
    _build_sources_context,
    _format_skeptic_findings,
    synthesize_report,
    synthesize_draft,
    synthesize_final,
)
from research_agent.skeptic import SkepticFinding
from research_agent.summarize import Summary
from research_agent.errors import SynthesisError
from research_agent.token_budget import truncate_to_budget


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
                max_tokens=8000,
            )

        call_args = mock_client.messages.stream.call_args
        assert call_args.kwargs["max_tokens"] == 8000


# --- Draft and final synthesis tests ---


def _make_streaming_client(response_text):
    """Create a mock client that streams response_text."""
    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter([response_text])
    mock_client.messages.stream.return_value = mock_stream
    return mock_client


SAMPLE_SUMMARIES = [
    Summary(
        url="https://example.com/1",
        title="Source One",
        summary="Summary of source one.",
    ),
    Summary(
        url="https://example.com/2",
        title="Source Two",
        summary="Summary of source two.",
    ),
]


class TestSynthesizeDraft:
    """Tests for synthesize_draft()."""

    def test_returns_draft_on_success(self):
        """Should return draft markdown from streaming response."""
        client = _make_streaming_client("## Executive Summary\nDraft content.")
        result = synthesize_draft(client, "test query", SAMPLE_SUMMARIES)
        assert "Executive Summary" in result
        assert "Draft content" in result

    def test_raises_on_empty_summaries(self):
        """Should raise SynthesisError when summaries list is empty."""
        client = MagicMock()
        with pytest.raises(SynthesisError, match="No summaries"):
            synthesize_draft(client, "test query", [])

    def test_raises_on_empty_response(self):
        """Should raise SynthesisError when response is empty."""
        client = _make_streaming_client("")
        with pytest.raises(SynthesisError, match="empty response"):
            synthesize_draft(client, "test query", SAMPLE_SUMMARIES)

    def test_no_business_context_in_prompt(self):
        """Draft should NOT include business_context block."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "test query", SAMPLE_SUMMARIES)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<business_context>" not in prompt

    def test_instructs_sections_1_through_8_only(self):
        """Draft instructions should specify sections 1-8 only."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "test query", SAMPLE_SUMMARIES)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "sections 1-8" in prompt.lower() or "sections (sections 1-8)" in prompt.lower()
        assert "Do NOT include Competitive Implications" in prompt

    def test_sanitizes_query(self):
        """Should sanitize the query in the prompt."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "<script>xss</script>", SAMPLE_SUMMARIES)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "&lt;script&gt;" in prompt


class TestFormatSkepticFindings:
    """Tests for _format_skeptic_findings()."""

    def test_formats_single_finding(self):
        """Should format a single finding with lens header."""
        findings = [
            SkepticFinding(
                lens="evidence_alignment",
                checklist="- [Concern] Claim X",
                critical_count=0,
                concern_count=1,
            )
        ]
        result = _format_skeptic_findings(findings)
        assert "### evidence_alignment" in result
        assert "Claim X" in result

    def test_formats_multiple_findings(self):
        """Should format multiple findings separated by blank lines."""
        findings = [
            SkepticFinding(lens="evidence_alignment", checklist="Finding 1",
                          critical_count=0, concern_count=0),
            SkepticFinding(lens="timing_stakes", checklist="Finding 2",
                          critical_count=0, concern_count=0),
        ]
        result = _format_skeptic_findings(findings)
        assert "### evidence_alignment" in result
        assert "### timing_stakes" in result

    def test_returns_empty_for_no_findings(self):
        """Should return empty string for empty list."""
        assert _format_skeptic_findings([]) == ""


class TestSynthesizeFinal:
    """Tests for synthesize_final()."""

    def test_returns_combined_report(self):
        """Should combine draft + final sections into full report."""
        client = _make_streaming_client("## Competitive Implications\nFinal content.")
        draft = "## Executive Summary\nDraft content."
        result = synthesize_final(
            client, "test query", draft, [], SAMPLE_SUMMARIES,
        )
        assert "Executive Summary" in result
        assert "Draft content" in result
        assert "Competitive Implications" in result
        assert "Final content" in result

    def test_includes_business_context_when_provided(self):
        """Should include business_context block in prompt."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
            business_context="Pacific Flow context",
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<business_context>" in prompt

    def test_includes_skeptic_findings_block(self):
        """Should include skeptic_findings block when findings provided."""
        findings = [
            SkepticFinding(
                lens="combined",
                checklist="- [Concern] Test finding",
                critical_count=0,
                concern_count=1,
            )
        ]
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", findings, SAMPLE_SUMMARIES,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<skeptic_findings>" in prompt
        assert "Test finding" in prompt

    def test_skips_section_11_when_no_findings(self):
        """Should instruct to skip Adversarial Analysis when findings is empty."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        # Should NOT list Adversarial Analysis as a section to write
        assert "11. **Adversarial Analysis**" not in prompt
        # Should instruct to skip it
        assert "Skip the Adversarial Analysis" in prompt
        # No skeptic_findings block
        assert "<skeptic_findings>" not in prompt

    def test_deep_mode_requests_three_subsections(self):
        """Deep mode should request three subsections in Section 11."""
        findings = [
            SkepticFinding(lens="evidence_alignment", checklist="E",
                          critical_count=0, concern_count=0),
        ]
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", findings, SAMPLE_SUMMARIES,
            is_deep=True,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "### Evidence Alignment Skeptic" in prompt
        assert "### Timing & Stakes Skeptic" in prompt
        assert "### Strategic Frame Skeptic" in prompt

    def test_standard_mode_single_assessment(self):
        """Standard mode should request single combined assessment."""
        findings = [
            SkepticFinding(lens="combined", checklist="C",
                          critical_count=0, concern_count=0),
        ]
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", findings, SAMPLE_SUMMARIES,
            is_deep=False,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "summarize the key challenges" in prompt
        # Should NOT have three subsection headers
        assert "### Evidence Alignment Skeptic" not in prompt

    def test_raises_on_empty_response(self):
        """Should raise SynthesisError on empty response."""
        client = _make_streaming_client("")
        with pytest.raises(SynthesisError, match="empty response"):
            synthesize_final(
                client, "query", "draft", [], SAMPLE_SUMMARIES,
            )


# --- Token budget enforcement tests ---


class TestTruncateToBudget:
    """Tests for truncate_to_budget() helper."""

    def _mock_count(self, text: str, model: str = "claude-sonnet-4-20250514") -> int:
        """Deterministic token counter: 1 token per 4 chars."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def test_truncate_to_budget_passthrough(self):
        """Text within budget returned unchanged."""
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = truncate_to_budget("short text", max_tokens=1000)
        assert result == "short text"

    def test_truncate_to_budget_truncates(self):
        """Oversized text truncated with [truncated] marker."""
        text = "a" * 400  # 100 tokens via mock
        with patch("research_agent.token_budget.count_tokens", side_effect=self._mock_count):
            result = truncate_to_budget(text, max_tokens=10)
        # max_chars = 10 * 4 = 40
        assert len(result.split("\n\n[Content truncated")[0]) == 40
        assert "[Content truncated to fit token budget]" in result

    def test_truncate_to_budget_empty(self):
        """Empty string returned as-is."""
        result = truncate_to_budget("", max_tokens=100)
        assert result == ""


class TestSynthesizeBudgetEnforcement:
    """Tests for token budget enforcement in synthesis functions."""

    def _mock_count(self, text: str, model: str = "claude-sonnet-4-20250514") -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def test_synthesize_report_calls_budget(self):
        """allocate_budget is called during synthesize_report()."""
        client = _make_streaming_client("Report content")
        with patch("research_agent.synthesize.allocate_budget") as mock_budget:
            from research_agent.token_budget import BudgetAllocation
            mock_budget.return_value = BudgetAllocation(
                allocations={"sources": 100}, pruned=[], total=100
            )
            with patch("builtins.print"):
                synthesize_report(
                    client=client,
                    query="test query",
                    summaries=SAMPLE_SUMMARIES,
                )
        mock_budget.assert_called_once()
        call_kwargs = mock_budget.call_args
        assert call_kwargs.kwargs["max_tokens"] == 100_000

    def test_synthesize_final_calls_budget(self):
        """allocate_budget is called during synthesize_final()."""
        client = _make_streaming_client("Final sections")
        with patch("research_agent.synthesize.allocate_budget") as mock_budget:
            from research_agent.token_budget import BudgetAllocation
            mock_budget.return_value = BudgetAllocation(
                allocations={"sources": 100}, pruned=[], total=100
            )
            synthesize_final(
                client, "query", "draft", [], SAMPLE_SUMMARIES,
            )
        mock_budget.assert_called_once()
        call_kwargs = mock_budget.call_args
        assert call_kwargs.kwargs["max_tokens"] == 100_000

    def test_budget_prunes_context_before_sources(self):
        """When over budget, business_context pruned before sources."""
        client = _make_streaming_client("Report content")
        with patch(
            "research_agent.synthesize.allocate_budget"
        ) as mock_budget, patch(
            "research_agent.synthesize.truncate_to_budget"
        ) as mock_truncate:
            from research_agent.token_budget import BudgetAllocation
            mock_budget.return_value = BudgetAllocation(
                allocations={"sources": 500, "business_context": 50},
                pruned=["business_context"],
                total=550,
            )
            mock_truncate.return_value = "truncated context"
            with patch("builtins.print"):
                synthesize_report(
                    client=client,
                    query="test query",
                    summaries=SAMPLE_SUMMARIES,
                    business_context="Very long business context " * 100,
                )
        # truncate_to_budget should be called for business_context, not sources
        mock_truncate.assert_called_once()
        call_args = mock_truncate.call_args
        assert call_args.args[1] == 50  # budget allocation for business_context
