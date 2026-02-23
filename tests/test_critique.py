"""Tests for research_agent.critique module."""

import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from research_agent.critique import (
    CritiqueResult,
    evaluate_report,
    save_critique,
    _parse_critique_response,
)


# --- CritiqueResult gate logic ---

class TestCritiqueResultGate:
    def test_pass_all_scores_above_threshold(self):
        cr = CritiqueResult(3, 4, 3, 3, 4, "", "", "")
        assert cr.overall_pass is True

    def test_pass_exactly_3_0_mean(self):
        cr = CritiqueResult(3, 3, 3, 3, 3, "", "", "")
        assert cr.overall_pass is True

    def test_pass_one_dim_at_2(self):
        """A score of 2 is allowed — only below 2 fails."""
        cr = CritiqueResult(2, 4, 4, 4, 4, "", "", "")
        assert cr.overall_pass is True

    def test_fail_one_dim_at_1(self):
        """Score of 1 is below 2, so overall_pass is False."""
        cr = CritiqueResult(1, 4, 4, 4, 4, "", "", "")
        assert cr.overall_pass is False

    def test_fail_mean_below_3(self):
        cr = CritiqueResult(2, 2, 2, 2, 2, "", "", "")
        assert cr.overall_pass is False

    def test_mean_score_property(self):
        cr = CritiqueResult(1, 2, 3, 4, 5, "", "", "")
        assert cr.mean_score == 3.0


# --- _parse_critique_response ---

class TestParseCritiqueResponse:
    def test_valid_input(self):
        text = (
            "SOURCE_DIVERSITY: 4\n"
            "CLAIM_SUPPORT: 3\n"
            "COVERAGE: 5\n"
            "GEOGRAPHIC_BALANCE: 2\n"
            "ACTIONABILITY: 4\n"
            "WEAKNESSES: Only US sources found\n"
            "SUGGESTIONS: Try non-English search terms\n"
            "QUERY_DOMAIN: music licensing"
        )
        result = _parse_critique_response(text)
        assert result["source_diversity"] == 4
        assert result["claim_support"] == 3
        assert result["coverage"] == 5
        assert result["geographic_balance"] == 2
        assert result["actionability"] == 4
        assert result["weaknesses"] == "Only US sources found"
        assert result["suggestions"] == "Try non-English search terms"
        assert result["query_domain"] == "music licensing"

    def test_missing_fields_default_to_3(self):
        result = _parse_critique_response("nothing useful here")
        for dim in ("source_diversity", "claim_support", "coverage",
                     "geographic_balance", "actionability"):
            assert result[dim] == 3
        assert result["weaknesses"] == ""

    def test_scores_clamped_to_range(self):
        text = "SOURCE_DIVERSITY: 9\nCLAIM_SUPPORT: 0\nCOVERAGE: 3\nGEOGRAPHIC_BALANCE: 3\nACTIONABILITY: 3"
        result = _parse_critique_response(text)
        assert result["source_diversity"] == 5
        assert result["claim_support"] == 1

    def test_garbage_input(self):
        result = _parse_critique_response("🗑️ garbage 🗑️")
        assert result["source_diversity"] == 3
        assert result["weaknesses"] == ""


# --- evaluate_report ---

class TestEvaluateReport:
    def test_calls_api_and_sanitizes(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=(
                "SOURCE_DIVERSITY: 4\nCLAIM_SUPPORT: 3\nCOVERAGE: 4\n"
                "GEOGRAPHIC_BALANCE: 2\nACTIONABILITY: 3\n"
                "WEAKNESSES: <script>alert('xss')</script> weak sources\n"
                "SUGGESTIONS: Search more broadly\n"
                "QUERY_DOMAIN: AI music"
            ))]
        )

        result = evaluate_report(
            client=mock_client,
            query="AI music licensing",
            mode_name="standard",
            surviving_sources=6,
            dropped_sources=2,
            skeptic_findings=[],
            gate_decision="full_report",
        )

        assert result.source_diversity == 4
        assert result.geographic_balance == 2
        # Sanitized: < and > replaced
        assert "<script>" not in result.weaknesses
        assert "&lt;script&gt;" in result.weaknesses
        assert len(result.weaknesses) <= 200

    def test_truncates_long_text(self):
        long_text = "x" * 500
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=(
                "SOURCE_DIVERSITY: 3\nCLAIM_SUPPORT: 3\nCOVERAGE: 3\n"
                "GEOGRAPHIC_BALANCE: 3\nACTIONABILITY: 3\n"
                f"WEAKNESSES: {long_text}\n"
                "SUGGESTIONS: ok\nQUERY_DOMAIN: test"
            ))]
        )

        result = evaluate_report(
            mock_client, "q", "standard", 5, 1, None, "full_report",
        )
        assert len(result.weaknesses) <= 200

    def test_api_failure_returns_defaults(self):
        from anthropic import APIError
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = APIError(
            message="fail", request=MagicMock(), body=None,
        )

        result = evaluate_report(
            mock_client, "q", "standard", 5, 1, None, "full_report",
        )
        assert result.source_diversity == 3
        assert result.overall_pass is True  # defaults are all 3

    def test_empty_response_returns_defaults(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(content=[])

        result = evaluate_report(
            mock_client, "q", "standard", 5, 1, None, "full_report",
        )
        assert result.source_diversity == 3


# --- save_critique ---

class TestSaveCritique:
    def test_yaml_roundtrip(self, tmp_path):
        cr = CritiqueResult(4, 3, 5, 2, 4, "weak spot", "try harder", "music")
        path = save_critique(cr, tmp_path)

        assert path.exists()
        assert path.name.startswith("critique-music_")
        assert path.suffix == ".yaml"

        data = yaml.safe_load(path.read_text())
        assert data["source_diversity"] == 4
        assert data["coverage"] == 5
        assert data["weaknesses"] == "weak spot"
        assert data["overall_pass"] is True
        assert data["mean_score"] == 3.6

    def test_empty_domain_uses_unknown(self, tmp_path):
        cr = CritiqueResult(3, 3, 3, 3, 3, "", "", "")
        path = save_critique(cr, tmp_path)
        assert "unknown" in path.name

    def test_creates_meta_dir(self, tmp_path):
        nested = tmp_path / "reports" / "meta"
        cr = CritiqueResult(3, 3, 3, 3, 3, "", "", "test")
        path = save_critique(cr, nested)
        assert path.exists()
        assert nested.exists()


# --- Agent integration: _run_critique ---

class TestAgentCritiqueIntegration:
    def test_quick_mode_skips_critique(self):
        """Quick mode should not call evaluate_report."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.quick())
        with patch("research_agent.agent.evaluate_report") as mock_eval:
            agent._run_critique("q", 3, 1, None, "full_report")
            mock_eval.assert_not_called()

    def test_standard_mode_calls_critique(self):
        """Standard mode should call evaluate_report and save_critique."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.standard())
        fake_result = CritiqueResult(3, 3, 3, 3, 3, "", "", "test")
        with patch("research_agent.agent.evaluate_report", return_value=fake_result) as mock_eval, \
             patch("research_agent.agent.save_critique") as mock_save:
            agent._run_critique("q", 5, 2, [], "full_report")
            mock_eval.assert_called_once()
            mock_save.assert_called_once()
            assert agent._last_critique is fake_result

    def test_critique_error_caught_gracefully(self):
        """Pipeline should complete even if critique throws OSError."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.standard())
        with patch("research_agent.agent.evaluate_report", side_effect=OSError("disk full")):
            # Should not raise
            agent._run_critique("q", 5, 2, [], "full_report")
            assert agent._last_critique is None


class TestCritiqueContextThreading:
    """Tests that critique_context flows through the actual agent pipeline."""

    @pytest.mark.asyncio
    async def test_evaluate_and_synthesize_passes_critique_to_evaluate_sources(self):
        """_evaluate_and_synthesize should pass critique_context as critique_guidance to evaluate_sources."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode
        from research_agent.relevance import RelevanceEvaluation

        agent = ResearchAgent(mode=ResearchMode.standard())
        agent._start_time = 0.0
        agent._step_num = 0
        agent._step_total = 10

        fake_eval = RelevanceEvaluation(
            decision="insufficient_data",
            decision_rationale="no sources",
            surviving_sources=(),
            dropped_sources=(),
            total_scored=0,
            total_survived=0,
            refined_query="q",
        )

        with patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock, return_value=fake_eval) as mock_eval, \
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock, return_value="# No data"):
            await agent._evaluate_and_synthesize(
                query="test",
                summaries=[],
                refined_query="test",
                critique_context="Improve source diversity",
            )
            _, kwargs = mock_eval.call_args
            assert kwargs["critique_guidance"] == "Improve source diversity"

    @pytest.mark.asyncio
    async def test_evaluate_and_synthesize_passes_none_without_critique(self):
        """Without critique_context, evaluate_sources gets critique_guidance=None."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode
        from research_agent.relevance import RelevanceEvaluation

        agent = ResearchAgent(mode=ResearchMode.standard())
        agent._start_time = 0.0
        agent._step_num = 0
        agent._step_total = 10

        fake_eval = RelevanceEvaluation(
            decision="insufficient_data",
            decision_rationale="no sources",
            surviving_sources=(),
            dropped_sources=(),
            total_scored=0,
            total_survived=0,
            refined_query="q",
        )

        with patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock, return_value=fake_eval) as mock_eval, \
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock, return_value="# No data"):
            await agent._evaluate_and_synthesize(
                query="test",
                summaries=[],
                refined_query="test",
            )
            _, kwargs = mock_eval.call_args
            assert kwargs["critique_guidance"] is None

    @pytest.mark.asyncio
    async def test_synthesize_final_receives_critique_guidance(self):
        """In standard mode full_report path, synthesize_final should receive critique_guidance."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode
        from research_agent.relevance import RelevanceEvaluation
        from research_agent.context_result import ContextResult

        agent = ResearchAgent(mode=ResearchMode.standard())
        agent._start_time = 0.0
        agent._step_num = 0
        agent._step_total = 10

        fake_eval = RelevanceEvaluation(
            decision="full_report",
            decision_rationale="sufficient sources",
            surviving_sources=(MagicMock(summary="s1"),),
            dropped_sources=(),
            total_scored=1,
            total_survived=1,
            refined_query="refined",
        )
        fake_finding = MagicMock(critical_count=0, concern_count=0)

        with patch("research_agent.agent.evaluate_sources", new_callable=AsyncMock, return_value=fake_eval), \
             patch("research_agent.agent.synthesize_draft", return_value="draft"), \
             patch("research_agent.agent.load_synthesis_context", return_value=ContextResult.not_configured(source="")), \
             patch("research_agent.agent.run_skeptic_combined", new_callable=AsyncMock, return_value=fake_finding), \
             patch("research_agent.agent.synthesize_final", return_value="# Report") as mock_synth, \
             patch.object(agent, "_run_critique"):
            await agent._evaluate_and_synthesize(
                query="test",
                summaries=[],
                refined_query="test",
                critique_context="Focus on coverage",
            )
            _, kwargs = mock_synth.call_args
            assert kwargs["critique_guidance"] == "Focus on coverage"
