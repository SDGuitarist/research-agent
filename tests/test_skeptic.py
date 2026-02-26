"""Tests for research_agent.skeptic module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from anthropic import RateLimitError, APIError, APITimeoutError

from research_agent.skeptic import (
    SkepticFinding,
    _count_severity,
    _build_context_block,
    _build_prior_block,
    _call_skeptic,
    run_skeptic_evidence,
    run_skeptic_timing,
    run_skeptic_frame,
    run_skeptic_combined,
    run_deep_skeptic_pass,
)
from research_agent.errors import SkepticError


class TestCountSeverity:
    """Tests for _count_severity()."""

    def test_counts_critical_findings(self):
        """Should count occurrences of 'Critical Finding'."""
        text = "[Critical Finding] One\n[Critical Finding] Two\n[Concern] Three"
        critical, concern = _count_severity(text)
        assert critical == 2
        assert concern == 1

    def test_counts_concerns(self):
        """Should count [Concern] tags."""
        text = "[Concern] A\n[Concern] B\n[Observation] C"
        critical, concern = _count_severity(text)
        assert critical == 0
        assert concern == 2

    def test_case_insensitive(self):
        """Should match case-insensitively."""
        text = "[CRITICAL FINDING] one\n[critical finding] two"
        critical, _ = _count_severity(text)
        assert critical == 2

    def test_zero_counts(self):
        """Should return zeros when no matches."""
        text = "[Observation] Nothing critical here."
        critical, concern = _count_severity(text)
        assert critical == 0
        assert concern == 0


class TestBuildContextBlock:
    """Tests for _build_context_block()."""

    def test_returns_empty_for_none(self):
        """Should return empty string when no context."""
        assert _build_context_block(None) == ""

    def test_returns_empty_for_empty_string(self):
        """Should return empty string for empty context."""
        assert _build_context_block("") == ""

    def test_wraps_in_xml(self):
        """Should wrap context in research_context XML tags."""
        result = _build_context_block("Test context")
        assert "<research_context>" in result
        assert "</research_context>" in result
        assert "Test context" in result

    def test_sanitizes_content(self):
        """Should sanitize angle brackets in context."""
        result = _build_context_block("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestBuildPriorBlock:
    """Tests for _build_prior_block()."""

    def test_returns_empty_for_none(self):
        """Should return empty string when no prior findings."""
        assert _build_prior_block(None) == ""

    def test_returns_empty_for_empty_list(self):
        """Should return empty string for empty list."""
        assert _build_prior_block([]) == ""

    def test_formats_findings(self):
        """Should format findings with lens headers."""
        findings = [
            SkepticFinding(
                lens="evidence_alignment",
                checklist="- [Concern] Claim X unsupported",
                critical_count=0,
                concern_count=1,
            )
        ]
        result = _build_prior_block(findings)
        assert "<prior_skeptic_findings>" in result
        assert "### evidence_alignment" in result
        assert "Claim X unsupported" in result


def _make_async_client(response_text):
    """Create a mock AsyncAnthropic client returning given text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_response.content = [mock_content]
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    return mock_client


def _make_async_client_multi(responses):
    """Create mock async client returning different responses per call."""
    mock_client = MagicMock()
    mock_responses = []
    for text in responses:
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = text
        mock_response.content = [mock_content]
        mock_responses.append(mock_response)
    mock_client.messages.create = AsyncMock(side_effect=mock_responses)
    return mock_client


class TestCallSkeptic:
    """Tests for _call_skeptic()."""

    @pytest.mark.asyncio
    async def test_returns_skeptic_finding(self):
        """Should return SkepticFinding with correct fields."""
        client = _make_async_client(
            "## Evidence Review\n- [Critical Finding] Claim unsupported\n"
            "- [Concern] Inference not flagged"
        )
        result = await _call_skeptic(client, "system", "prompt", "evidence_alignment")
        assert isinstance(result, SkepticFinding)
        assert result.lens == "evidence_alignment"
        assert result.critical_count == 1
        assert result.concern_count == 1

    @pytest.mark.asyncio
    async def test_raises_on_empty_content(self):
        """Should raise SkepticError when response has no content."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = []
        client.messages.create = AsyncMock(return_value=mock_response)
        with pytest.raises(SkepticError, match="empty response"):
            await _call_skeptic(client, "system", "prompt", "test_lens")

    @pytest.mark.asyncio
    async def test_raises_on_empty_text(self):
        """Should raise SkepticError when response text is empty."""
        client = _make_async_client("   ")
        with pytest.raises(SkepticError, match="empty response"):
            await _call_skeptic(client, "system", "prompt", "test_lens")

    @pytest.mark.asyncio
    async def test_raises_on_rate_limit(self):
        """Should raise SkepticError on rate limit."""
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        ))
        with pytest.raises(SkepticError, match="rate limited"):
            await _call_skeptic(client, "system", "prompt", "test_lens")

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        """Should raise SkepticError on timeout."""
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=APITimeoutError(
            request=MagicMock(),
        ))
        with pytest.raises(SkepticError, match="timed out"):
            await _call_skeptic(client, "system", "prompt", "test_lens")

    @pytest.mark.asyncio
    async def test_raises_on_api_error(self):
        """Should raise SkepticError on API error."""
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=APIError(
            message="server error",
            request=MagicMock(),
            body=None,
        ))
        with pytest.raises(SkepticError, match="API error"):
            await _call_skeptic(client, "system", "prompt", "test_lens")


class TestRunSkepticEvidence:
    """Tests for run_skeptic_evidence()."""

    @pytest.mark.asyncio
    async def test_returns_evidence_alignment_lens(self):
        """Should set lens to evidence_alignment."""
        client = _make_async_client("## Evidence Review\n- [Observation] Minor note")
        result = await run_skeptic_evidence(client, "Draft analysis text")
        assert result.lens == "evidence_alignment"

    @pytest.mark.asyncio
    async def test_sanitizes_draft(self):
        """Should sanitize draft content before building prompt."""
        client = _make_async_client("[Observation] ok")
        await run_skeptic_evidence(client, "<script>alert('xss')</script>")
        call_args = client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<script>" not in prompt
        assert "&lt;script&gt;" in prompt

    @pytest.mark.asyncio
    async def test_includes_context_when_provided(self):
        """Should include business context block when provided."""
        client = _make_async_client("[Observation] ok")
        await run_skeptic_evidence(client, "draft", synthesis_context="My business")
        call_args = client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "<research_context>" in prompt


class TestRunSkepticCombined:
    """Tests for run_skeptic_combined()."""

    @pytest.mark.asyncio
    async def test_returns_combined_lens(self):
        """Should set lens to combined."""
        client = _make_async_client("## Combined Review\n- [Observation] Note")
        result = await run_skeptic_combined(client, "Draft text")
        assert result.lens == "combined"

    @pytest.mark.asyncio
    async def test_uses_2000_max_tokens(self):
        """Combined mode should use 2000 max tokens."""
        client = _make_async_client("[Observation] ok")
        await run_skeptic_combined(client, "Draft text")
        call_args = client.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 2000


class TestRunDeepSkepticPass:
    """Tests for run_deep_skeptic_pass()."""

    @pytest.mark.asyncio
    async def test_returns_three_findings(self):
        """Should return exactly 3 SkepticFinding objects."""
        client = _make_async_client_multi([
            "- [Observation] Evidence note",
            "- [Concern] Timing risk",
            "- [Critical Finding] Frame issue",
        ])
        findings = await run_deep_skeptic_pass(client, "Draft text")
        assert len(findings) == 3

    @pytest.mark.asyncio
    async def test_correct_lens_order(self):
        """Should return findings in order: evidence, timing, frame."""
        client = _make_async_client_multi([
            "[Observation] Evidence",
            "[Observation] Timing",
            "[Observation] Frame",
        ])
        findings = await run_deep_skeptic_pass(client, "Draft text")
        assert findings[0].lens == "evidence_alignment"
        assert findings[1].lens == "timing_stakes"
        assert findings[2].lens == "strategic_frame"

    @pytest.mark.asyncio
    async def test_evidence_and_timing_have_no_prior_findings(self):
        """Evidence and timing run in parallel — neither has prior findings."""
        client = _make_async_client_multi([
            "[Observation] Evidence note",
            "[Observation] Timing note",
            "[Observation] Frame note",
        ])
        await run_deep_skeptic_pass(client, "Draft text")
        calls = client.messages.create.call_args_list

        # Evidence and timing run concurrently — order may vary,
        # but neither should have prior_skeptic_findings
        for call in calls[:2]:
            prompt = call.kwargs["messages"][0]["content"]
            assert "<prior_skeptic_findings>" not in prompt

    @pytest.mark.asyncio
    async def test_frame_receives_both_prior_findings(self):
        """Frame agent should receive both evidence and timing findings."""
        client = _make_async_client_multi([
            "[Observation] Evidence note",
            "[Observation] Timing note",
            "[Observation] Frame note",
        ])
        await run_deep_skeptic_pass(client, "Draft text")
        calls = client.messages.create.call_args_list

        # Third call (frame) should have both evidence and timing findings
        prompt_3 = calls[2].kwargs["messages"][0]["content"]
        assert "<prior_skeptic_findings>" in prompt_3
        assert "evidence_alignment" in prompt_3
        assert "timing_stakes" in prompt_3

    @pytest.mark.asyncio
    async def test_propagates_skeptic_error(self):
        """Should propagate SkepticError if any agent fails."""
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        ))
        with pytest.raises(SkepticError):
            await run_deep_skeptic_pass(client, "Draft text")
