"""Tests for research_agent.critique module."""

import yaml
import pytest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from research_agent.critique import (
    CritiqueResult,
    evaluate_report,
    save_critique,
    save_critique_file,
    _parse_critique_response,
)
from research_agent.errors import ConfigError, StateError

from psycopg_pool import PoolTimeout


# --- CritiqueResult gate logic ---

class TestCritiqueResultGate:
    def test_pass_all_scores_above_threshold(self):
        cr = CritiqueResult(
            source_diversity=3, claim_support=4, coverage=3,
            geographic_balance=3, actionability=4, weaknesses="", suggestions="",
        )
        assert cr.overall_pass is True

    def test_pass_exactly_3_0_mean(self):
        cr = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        assert cr.overall_pass is True

    def test_pass_one_dim_at_2(self):
        """A score of 2 is allowed — only below 2 fails."""
        cr = CritiqueResult(
            source_diversity=2, claim_support=4, coverage=4,
            geographic_balance=4, actionability=4, weaknesses="", suggestions="",
        )
        assert cr.overall_pass is True

    def test_fail_one_dim_at_1(self):
        """Score of 1 is below 2, so overall_pass is False."""
        cr = CritiqueResult(
            source_diversity=1, claim_support=4, coverage=4,
            geographic_balance=4, actionability=4, weaknesses="", suggestions="",
        )
        assert cr.overall_pass is False

    def test_fail_mean_below_3(self):
        cr = CritiqueResult(
            source_diversity=2, claim_support=2, coverage=2,
            geographic_balance=2, actionability=2, weaknesses="", suggestions="",
        )
        assert cr.overall_pass is False

    def test_mean_score_property(self):
        cr = CritiqueResult(
            source_diversity=1, claim_support=2, coverage=3,
            geographic_balance=4, actionability=5, weaknesses="", suggestions="",
        )
        assert cr.mean_score == 3.0


# --- Factory classmethods ---

class TestCritiqueResultFactory:
    def test_from_parsed_valid(self):
        parsed = {
            "source_diversity": 4, "claim_support": 3, "coverage": 5,
            "geographic_balance": 2, "actionability": 4,
        }
        cr = CritiqueResult.from_parsed(parsed, weaknesses="weak", suggestions="more")
        assert cr.source_diversity == 4
        assert cr.coverage == 5
        assert cr.weaknesses == "weak"
        assert cr.suggestions == "more"

    def test_from_parsed_missing_key_raises(self):
        parsed = {"source_diversity": 4, "claim_support": 3}  # missing 3 dims
        with pytest.raises(ValueError, match="missing dimension keys"):
            CritiqueResult.from_parsed(parsed, weaknesses="", suggestions="")

    def test_from_parsed_ignores_extra_keys(self):
        parsed = {
            "source_diversity": 4, "claim_support": 3, "coverage": 5,
            "geographic_balance": 2, "actionability": 4,
            "extra_field": 99,
        }
        cr = CritiqueResult.from_parsed(parsed, weaknesses="", suggestions="")
        assert cr.source_diversity == 4

    def test_fallback_returns_neutral_scores(self):
        cr = CritiqueResult.fallback()
        assert cr.source_diversity == 3
        assert cr.claim_support == 3
        assert cr.coverage == 3
        assert cr.geographic_balance == 3
        assert cr.actionability == 3
        assert cr.weaknesses == "Critique unavailable (API error)"
        assert cr.suggestions == ""
        assert cr.overall_pass is True


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
        )
        result = _parse_critique_response(text)
        assert result["source_diversity"] == 4
        assert result["claim_support"] == 3
        assert result["coverage"] == 5
        assert result["geographic_balance"] == 2
        assert result["actionability"] == 4
        assert result["weaknesses"] == "Only US sources found"
        assert result["suggestions"] == "Try non-English search terms"

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
                "SUGGESTIONS: Search more broadly"
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
        # Raw text stored — sanitization happens at consumption boundary
        # (_summarize_patterns in context.py), not at write time
        assert "<script>" in result.weaknesses
        assert len(result.weaknesses) <= 200

    def test_truncates_long_text(self):
        long_text = "x" * 500
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=(
                "SOURCE_DIVERSITY: 3\nCLAIM_SUPPORT: 3\nCOVERAGE: 3\n"
                "GEOGRAPHIC_BALANCE: 3\nACTIONABILITY: 3\n"
                f"WEAKNESSES: {long_text}\n"
                "SUGGESTIONS: ok"
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


# --- save_critique (DB) ---

class TestSaveCritiqueDb:
    def _cr(self, **overrides):
        base = dict(
            source_diversity=4, claim_support=3, coverage=5,
            geographic_balance=2, actionability=4,
            weaknesses="weak spot", suggestions="try harder",
        )
        base.update(overrides)
        return CritiqueResult(**base)

    def test_row_roundtrip(self, db):
        critique_id = save_critique(db, self._cr())
        row = db.execute(
            "SELECT * FROM critiques WHERE id = %s", (critique_id,)
        ).fetchone()
        assert row["source_diversity"] == 4
        assert row["coverage"] == 5
        assert row["weaknesses"] == "weak spot"
        assert row["suggestions"] == "try harder"
        assert row["overall_pass"] is True
        assert row["mean_score"] == pytest.approx(3.6)
        assert row["created_at"] is not None

    def test_free_text_sanitized_on_write(self, db):
        cr = self._cr(weaknesses="<script>bad</script> & more")
        critique_id = save_critique(db, cr)
        row = db.execute(
            "SELECT weaknesses FROM critiques WHERE id = %s", (critique_id,)
        ).fetchone()
        assert "<" not in row["weaknesses"]
        assert row["weaknesses"] == "&lt;script&gt;bad&lt;/script&gt; &amp; more"

    def test_failing_critique_stores_pass_false(self, db):
        cr = self._cr(source_diversity=1, claim_support=1, coverage=1,
                      geographic_balance=1, actionability=1)
        critique_id = save_critique(db, cr)
        row = db.execute(
            "SELECT overall_pass FROM critiques WHERE id = %s", (critique_id,)
        ).fetchone()
        assert row["overall_pass"] is False

    def test_ids_increment_across_saves(self, db):
        first = save_critique(db, self._cr())
        second = save_critique(db, self._cr())
        assert second > first


# --- save_critique_file (legacy disk archive, MCP-only until Session 4) ---

class TestSaveCritiqueFile:
    def test_yaml_roundtrip(self, tmp_path):
        cr = CritiqueResult(
            source_diversity=4, claim_support=3, coverage=5,
            geographic_balance=2, actionability=4,
            weaknesses="weak spot", suggestions="try harder",
        )
        path = save_critique_file(cr, tmp_path)

        assert path.exists()
        assert path.name.startswith("critique-")
        assert path.suffix == ".yaml"

        data = yaml.safe_load(path.read_text())
        assert data["source_diversity"] == 4
        assert data["coverage"] == 5
        assert data["weaknesses"] == "weak spot"
        assert data["overall_pass"] is True
        assert data["mean_score"] == 3.6

    def test_filename_is_timestamp_only(self, tmp_path):
        cr = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        path = save_critique_file(cr, tmp_path)
        # Format: critique-{timestamp}.yaml — no slug
        assert path.name.startswith("critique-")
        parts = path.stem.split("-", 1)
        assert parts[1].isdigit()

    def test_creates_meta_dir(self, tmp_path):
        nested = tmp_path / "reports" / "meta"
        cr = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        path = save_critique_file(cr, nested)
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
        fake_result = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        with patch("research_agent.agent.evaluate_report", return_value=fake_result) as mock_eval, \
             patch("research_agent.agent.save_critique") as mock_save, \
             patch("research_agent.db.open_pool") as mock_pool:
            mock_pool.return_value.connection.return_value = nullcontext(MagicMock())
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

    def test_db_save_failure_caught_gracefully(self):
        """A StateError from the critique DB save must not crash the pipeline."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.standard())
        fake_result = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        with patch("research_agent.agent.evaluate_report", return_value=fake_result), \
             patch("research_agent.db.open_pool",
                   side_effect=StateError("db down")):
            # Should not raise
            agent._run_critique("q", 5, 2, [], "full_report")
            assert agent._last_critique is None

    def test_saves_critique_to_db(self, db):
        """_run_critique persists a critiques row through the injected pool."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.standard())
        fake_result = CritiqueResult(
            source_diversity=4, claim_support=4, coverage=4,
            geographic_balance=4, actionability=4,
            weaknesses="w", suggestions="s",
        )
        with patch("research_agent.agent.evaluate_report", return_value=fake_result), \
             patch("research_agent.db.open_pool") as mock_pool:
            mock_pool.return_value.connection.return_value = nullcontext(db)
            agent._run_critique("q", 5, 2, [], "full_report")
        row = db.execute("SELECT * FROM critiques").fetchone()
        assert row["overall_pass"] is True
        assert row["weaknesses"] == "w"
        assert agent._last_critique is fake_result

    def test_run_critique_pool_timeout_degrades(self):
        """A PoolTimeout (previously not a ResearchError → leaked and crashed the
        pipeline) is now normalized to StateError and swallowed (Session 3 P1)."""
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode

        agent = ResearchAgent(mode=ResearchMode.standard())
        fake_result = CritiqueResult(
            source_diversity=3, claim_support=3, coverage=3,
            geographic_balance=3, actionability=3, weaknesses="", suggestions="",
        )
        with patch("research_agent.agent.evaluate_report", return_value=fake_result), \
             patch("research_agent.db.open_pool", side_effect=PoolTimeout("pool exhausted")):
            # Must not raise — research continues without a saved critique.
            agent._run_critique("q", 5, 2, [], "full_report")
        assert agent._last_critique is None


class TestLoadCritiqueHistoryDbDegradation:
    """_load_critique_history_db is an optional enhancement: every database
    failure class degrades to no history (warning-logged), never raises
    (Session 3 review P1)."""

    def _agent(self):
        from research_agent.agent import ResearchAgent
        from research_agent.modes import ResearchMode
        return ResearchAgent(mode=ResearchMode.standard())

    def test_missing_config_degrades_to_none(self):
        with patch("research_agent.db.open_pool",
                   side_effect=ConfigError("DATABASE_URL is not set")):
            assert self._agent()._load_critique_history_db() is None

    def test_pool_timeout_degrades_to_none(self):
        with patch("research_agent.db.open_pool", side_effect=PoolTimeout("exhausted")):
            assert self._agent()._load_critique_history_db() is None

    def test_sql_failure_degrades_to_none(self):
        import psycopg
        broken = MagicMock()
        broken.execute.side_effect = psycopg.errors.UndefinedTable("no such table")
        with patch("research_agent.db.open_pool") as mock_pool:
            mock_pool.return_value.connection.return_value = nullcontext(broken)
            assert self._agent()._load_critique_history_db() is None


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
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock, return_value="# No data"), \
             patch("research_agent.agent.identify_coverage_gaps", new_callable=AsyncMock):
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
             patch("research_agent.agent.generate_insufficient_data_response", new_callable=AsyncMock, return_value="# No data"), \
             patch("research_agent.agent.identify_coverage_gaps", new_callable=AsyncMock):
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
             patch("research_agent.agent.load_full_context", return_value=ContextResult.not_configured(source="")), \
             patch("research_agent.agent.run_skeptic_combined", new_callable=AsyncMock, return_value=fake_finding), \
             patch("research_agent.agent.synthesize_final", return_value="# Report") as mock_synth, \
             patch.object(agent, "_run_critique"), \
             patch.object(agent, "_run_iteration", new_callable=AsyncMock, return_value=("# Report", 0)):
            await agent._evaluate_and_synthesize(
                query="test",
                summaries=[],
                refined_query="test",
                critique_context="Focus on coverage",
            )
            _, kwargs = mock_synth.call_args
            assert kwargs["critique_guidance"] == "Focus on coverage"
