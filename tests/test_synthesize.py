"""Tests for research_agent.synthesize module."""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.context_result import ReportTemplate
from research_agent.synthesize import (
    _build_sources_context,
    _build_default_final_sections,
    _build_draft_sections,
    _build_final_sections,
    _DEFAULT_FINAL_START,
    _format_skeptic_findings,
    synthesize_report,
    synthesize_draft,
    synthesize_final,
)
from research_agent.skeptic import SkepticFinding
from research_agent.summarize import Summary
from research_agent.errors import SynthesisError
from research_agent.token_budget import truncate_to_budget


# Reusable test template
PFE_TEMPLATE = ReportTemplate(
    name="Pacific Flow Entertainment",
    draft_sections=(
        ("Executive Summary", "2-3 paragraph overview of key findings."),
        ("Company Overview", "Factual: founding, location, team size."),
        ("Service Portfolio", "Services offered, pricing if found."),
    ),
    final_sections=(
        ("Competitive Implications", "Threats, opportunities, gaps."),
        ("Positioning Advice", "3-5 actionable angles."),
    ),
    context_usage="Use context for Competitive Implications and Positioning Advice only.",
)


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

    def test_synthesize_report_includes_context_in_prompt(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Context should appear in the prompt when provided."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                context="We are a guitar entertainment company.",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "<research_context>" in user_content
        assert "guitar entertainment company" in user_content

    def test_synthesize_report_omits_context_block_when_none(
        self, sample_summaries, mock_anthropic_stream
    ):
        """No context should produce no <research_context> block."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                context=None,
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "<research_context>" not in user_content
        assert "Competitive Implications" not in user_content

    def test_synthesize_report_sanitizes_context(
        self, sample_summaries, mock_anthropic_stream
    ):
        """Context with angle brackets should be escaped."""
        mock_client = MagicMock()
        mock_stream = mock_anthropic_stream(["Report content"])
        mock_client.messages.stream.return_value = mock_stream

        with patch("builtins.print"):
            synthesize_report(
                client=mock_client,
                query="test query",
                summaries=sample_summaries,
                context="&lt;script&gt;alert('xss')&lt;/script&gt;",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        # Context is pre-sanitized at load time; synthesize passes it through
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
                context="Our company does X.",
            )

        call_args = mock_client.messages.stream.call_args
        user_content = call_args.kwargs["messages"][0]["content"]

        assert "analytical and recommendation sections" in user_content
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

    def test_no_context_in_prompt(self):
        """Draft should NOT include context block."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "test query", SAMPLE_SUMMARIES)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<research_context>" not in prompt

    def test_instructs_template_sections_when_template_provided(self):
        """Draft with template should use template's draft sections."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "test query", SAMPLE_SUMMARIES, template=PFE_TEMPLATE)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Executive Summary" in prompt
        assert "Company Overview" in prompt
        assert "Service Portfolio" in prompt
        assert "Do NOT include Competitive Implications" in prompt

    def test_instructs_generic_sections_without_template(self):
        """Draft without template should use generic technical template."""
        client = _make_streaming_client("Draft content")
        synthesize_draft(client, "test query", SAMPLE_SUMMARIES, template=None)
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Key Findings" in prompt
        assert "Technical Details" in prompt
        assert "Company Overview" not in prompt

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

    def test_includes_context_when_provided(self):
        """Should include context block in prompt."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
            context="Pacific Flow context",
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<research_context>" in prompt

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

    def test_skips_adversarial_analysis_when_no_findings(self):
        """Should instruct to skip Adversarial Analysis when findings is empty."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        # Section list before "Skip" should NOT mention Adversarial Analysis
        assert "**Adversarial Analysis**" not in prompt.split("Skip")[0]
        # Should instruct to skip it
        assert "Skip the Adversarial Analysis" in prompt
        # No skeptic_findings block
        assert "<skeptic_findings>" not in prompt

    def test_generic_skeptic_path_includes_adversarial_section(self):
        """Generic path with skeptic findings should list Adversarial Analysis."""
        findings = [
            SkepticFinding(lens="combined", checklist="C",
                          critical_count=0, concern_count=1),
        ]
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", findings, SAMPLE_SUMMARIES,
            template=None,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "5. **Adversarial Analysis**" in prompt
        assert "6. **Limitations & Gaps**" in prompt

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
        """When over budget, context pruned before sources."""
        client = _make_streaming_client("Report content")
        with patch(
            "research_agent.synthesize.allocate_budget"
        ) as mock_budget, patch(
            "research_agent.synthesize.truncate_to_budget"
        ) as mock_truncate:
            from research_agent.token_budget import BudgetAllocation
            mock_budget.return_value = BudgetAllocation(
                allocations={"sources": 500, "context": 50},
                pruned=["context"],
                total=550,
            )
            mock_truncate.return_value = "truncated context"
            with patch("builtins.print"):
                synthesize_report(
                    client=client,
                    query="test query",
                    summaries=SAMPLE_SUMMARIES,
                    context="Very long context " * 100,
                )
        # truncate_to_budget should be called for context, not sources
        mock_truncate.assert_called_once()
        call_args = mock_truncate.call_args
        assert call_args.args[1] == 50  # budget allocation for context


class TestCritiqueGuidanceParam:
    """Tests for critique_guidance parameter in synthesize_final."""

    def test_none_produces_no_guidance_block(self):
        """critique_guidance=None should not add critique guidance block."""
        client = _make_streaming_client("## Competitive Implications\nContent")
        with patch("builtins.print"):
            result = synthesize_final(
                client=client,
                query="test",
                draft="## Executive Summary\nDraft",
                skeptic_findings=[],
                summaries=SAMPLE_SUMMARIES,
                critique_guidance=None,
            )
        call_args = client.messages.stream.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "<critique_guidance>" not in prompt

    def test_provided_adds_guidance_block(self):
        """critique_guidance should inject critique_guidance block into prompt."""
        client = _make_streaming_client("## Competitive Implications\nContent")
        with patch("builtins.print"):
            result = synthesize_final(
                client=client,
                query="test",
                draft="## Executive Summary\nDraft",
                skeptic_findings=[],
                summaries=SAMPLE_SUMMARIES,
                critique_guidance="Improve source diversity scores",
            )
        call_args = client.messages.stream.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "<critique_guidance>" in prompt
        assert "Improve source diversity scores" in prompt


class TestBuildDraftSections:
    """Tests for _build_draft_sections() helper."""

    def test_formats_numbered_sections(self):
        """Should produce numbered section list from template."""
        result = _build_draft_sections(PFE_TEMPLATE)
        assert "1. **Executive Summary**" in result
        assert "2. **Company Overview**" in result
        assert "3. **Service Portfolio**" in result

    def test_excludes_final_sections(self):
        """Should mention final sections in the 'Do NOT include' line."""
        result = _build_draft_sections(PFE_TEMPLATE)
        assert "Competitive Implications" in result
        assert "Positioning Advice" in result

    def test_includes_balance_instruction(self):
        """Should include the balance instruction."""
        result = _build_draft_sections(PFE_TEMPLATE)
        assert "balanced coverage" in result


class TestBuildFinalSections:
    """Tests for _build_final_sections() helper."""

    def test_numbers_from_draft_count(self):
        """Section numbers should continue from draft count."""
        result = _build_final_sections(PFE_TEMPLATE, has_skeptic=False, draft_count=3)
        assert "4. **Competitive Implications**" in result
        assert "5. **Positioning Advice**" in result
        assert "6. **Limitations & Gaps**" in result

    def test_includes_adversarial_when_skeptic(self):
        """Should include Adversarial Analysis when skeptic findings present."""
        result = _build_final_sections(PFE_TEMPLATE, has_skeptic=True, draft_count=3)
        assert "Adversarial Analysis" in result

    def test_excludes_adversarial_when_no_skeptic(self):
        """Should NOT include Adversarial Analysis without skeptic findings."""
        result = _build_final_sections(PFE_TEMPLATE, has_skeptic=False, draft_count=3)
        assert "Adversarial Analysis" not in result

    def test_always_includes_sources(self):
        """Sources section should always be present."""
        result = _build_final_sections(PFE_TEMPLATE, has_skeptic=False, draft_count=3)
        assert "## Sources" in result


class TestBuildDefaultFinalSections:
    """Tests for _build_default_final_sections() helper."""

    def test_with_skeptic(self):
        """Should include Adversarial Analysis at position 5."""
        result = _build_default_final_sections(has_skeptic=True)
        assert "5. **Adversarial Analysis**" in result
        assert "6. **Limitations & Gaps**" in result
        assert "## Sources" in result

    def test_without_skeptic(self):
        """Should skip Adversarial Analysis, Limitations at position 5."""
        result = _build_default_final_sections(has_skeptic=False)
        assert "Adversarial Analysis" not in result
        assert "5. **Limitations & Gaps**" in result
        assert "## Sources" in result

    def test_default_final_start_matches_generic_draft_count(self):
        """_DEFAULT_FINAL_START must be 5 (4 generic draft sections + 1).

        If you add or remove a generic draft section in synthesize_draft's
        else-branch, update _DEFAULT_FINAL_START to match.
        """
        assert _DEFAULT_FINAL_START == 5


class TestTemplateDrivenFinal:
    """Tests for template-driven synthesize_final()."""

    def test_uses_template_sections(self):
        """Template sections should appear in the prompt."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
            template=PFE_TEMPLATE,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Competitive Implications" in prompt
        assert "Positioning Advice" in prompt
        assert "Limitations & Gaps" in prompt

    def test_template_context_usage_in_final(self):
        """Template context_usage should be used as context instruction."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
            context="Business info",
            template=PFE_TEMPLATE,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Competitive Implications and Positioning Advice only" in prompt

    def test_no_template_uses_generic_sections(self):
        """Without template, context should use generic section list (no PFE sections)."""
        client = _make_streaming_client("Final sections")
        synthesize_final(
            client, "query", "draft", [], SAMPLE_SUMMARIES,
            context="Business info",
            template=None,
        )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Limitations & Gaps" in prompt
        assert "Competitive Implications" not in prompt


class TestTemplateDrivenReport:
    """Tests for template-driven synthesize_report()."""

    def test_template_context_usage_in_report(self):
        """Template context_usage should override default context instruction."""
        client = _make_streaming_client("Report content")
        with patch("builtins.print"):
            synthesize_report(
                client=client,
                query="test query",
                summaries=SAMPLE_SUMMARIES,
                context="Business info",
                template=PFE_TEMPLATE,
            )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Competitive Implications and Positioning Advice only" in prompt

    def test_no_template_uses_default_context_instruction(self):
        """Without template, default context instruction should be used."""
        client = _make_streaming_client("Report content")
        with patch("builtins.print"):
            synthesize_report(
                client=client,
                query="test query",
                summaries=SAMPLE_SUMMARIES,
                context="Business info",
                template=None,
            )
        call_args = client.messages.stream.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "objective and context-free" in prompt
