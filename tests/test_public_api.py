"""Tests for the public API: run_research, run_research_async, list_modes."""

import asyncio
import sys
import warnings
from unittest.mock import AsyncMock, patch

import pytest

import research_agent
from research_agent import (
    ResearchError,
    ResearchResult,
    ModeInfo,
    list_modes,
    run_research,
    run_research_async,
)


# --- __version__ and __all__ ---


class TestVersion:
    def test_version_is_set(self):
        assert research_agent.__version__ == "0.18.0"

    @pytest.mark.skipif(
        sys.version_info < (3, 11), reason="tomllib requires 3.11+"
    )
    def test_version_matches_pyproject(self):
        """Ensure __init__.__version__ matches pyproject.toml."""
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml not created yet (Session 4)")
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        assert research_agent.__version__ == data["project"]["version"]


class TestAll:
    def test_all_contains_expected_names(self):
        expected = {
            "ResearchAgent",
            "ResearchMode",
            "ResearchResult",
            "ResearchError",
            "ModeInfo",
            "list_available_contexts",
            "resolve_context_path",
            "run_research",
            "run_research_async",
            "list_modes",
        }
        assert set(research_agent.__all__) == expected


# --- list_modes ---


class TestListModes:
    def test_returns_three_modes(self):
        modes = list_modes()
        assert len(modes) == 3

    def test_returns_mode_info_instances(self):
        modes = list_modes()
        for m in modes:
            assert isinstance(m, ModeInfo)

    def test_mode_names(self):
        modes = list_modes()
        names = [m.name for m in modes]
        assert names == ["quick", "standard", "deep"]

    def test_all_fields_populated(self):
        for m in list_modes():
            assert m.name
            assert m.max_sources > 0
            assert m.word_target > 0
            assert m.cost_estimate  # non-empty string
            # auto_save is bool — just check it's set
            assert isinstance(m.auto_save, bool)


# --- run_research validation ---


ENV_BOTH = {"ANTHROPIC_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}


class TestRunResearchValidation:
    def test_empty_query_raises(self):
        with pytest.raises(ResearchError, match="Query cannot be empty"):
            run_research("")

    def test_whitespace_only_query_raises(self):
        with pytest.raises(ResearchError, match="Query cannot be empty"):
            run_research("   ")

    def test_invalid_mode_raises(self):
        with pytest.raises(ResearchError, match="Invalid mode"):
            run_research("test query", mode="invalid")

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}, clear=True)
    def test_missing_anthropic_key_raises(self):
        with pytest.raises(ResearchError, match="ANTHROPIC_API_KEY"):
            run_research("test query")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    def test_missing_tavily_key_raises(self):
        with pytest.raises(ResearchError, match="TAVILY_API_KEY"):
            run_research("test query")


# --- run_research_async validation ---


class TestRunResearchAsyncValidation:
    async def test_empty_query_raises(self):
        with pytest.raises(ResearchError, match="Query cannot be empty"):
            await run_research_async("")

    async def test_whitespace_only_query_raises(self):
        with pytest.raises(ResearchError, match="Query cannot be empty"):
            await run_research_async("   ")

    async def test_invalid_mode_raises(self):
        with pytest.raises(ResearchError, match="Invalid mode"):
            await run_research_async("test query", mode="invalid")

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}, clear=True)
    async def test_missing_anthropic_key_raises(self):
        with pytest.raises(ResearchError, match="ANTHROPIC_API_KEY"):
            await run_research_async("test query")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    async def test_missing_tavily_key_raises(self):
        with pytest.raises(ResearchError, match="TAVILY_API_KEY"):
            await run_research_async("test query")


# --- run_research happy path (mocked) ---


class TestRunResearchHappyPath:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    def test_returns_research_result(self, mock_agent_cls):
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 5
        agent_instance._last_gate_decision = "full_report"

        result = run_research("test query", mode="quick")

        assert isinstance(result, ResearchResult)
        assert result.report == "# Report"
        assert result.query == "test query"
        assert result.mode == "quick"
        assert result.sources_used == 5
        assert result.status == "full_report"

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    def test_default_mode_is_standard(self, mock_agent_cls):
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 8
        agent_instance._last_gate_decision = "full_report"

        result = run_research("test query")

        assert result.mode == "standard"

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    def test_short_report_status(self, mock_agent_cls):
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Short")
        agent_instance._last_source_count = 2
        agent_instance._last_gate_decision = "short_report"

        result = run_research("test query", mode="quick")

        assert result.status == "short_report"
        assert result.sources_used == 2


# --- run_research_async happy path (mocked) ---


class TestRunResearchAsyncHappyPath:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    async def test_returns_research_result(self, mock_agent_cls):
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 5
        agent_instance._last_gate_decision = "full_report"
        agent_instance.last_critique = None

        result = await run_research_async("test query", mode="quick")

        assert isinstance(result, ResearchResult)
        assert result.report == "# Report"
        assert result.query == "test query"
        assert result.mode == "quick"
        assert result.sources_used == 5
        assert result.status == "full_report"
        assert result.critique is None

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    async def test_includes_critique_in_result(self, mock_agent_cls):
        from research_agent.critique import CritiqueResult
        fake_critique = CritiqueResult(4, 3, 4, 3, 4, "weak", "try more", "test")

        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 5
        agent_instance._last_gate_decision = "full_report"
        agent_instance.last_critique = fake_critique

        result = await run_research_async("test query", mode="standard")

        assert result.critique is fake_critique
        assert result.critique.source_diversity == 4


# --- event loop collision ---


class TestEventLoopCollision:
    async def test_run_research_from_async_context_raises(self):
        """run_research() from inside async context gives clear error."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(ResearchError, match="async context"):
                run_research("test query")


# --- edge case: gate decision empty ---


class TestGateDecisionEdgeCase:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    def test_empty_gate_decision_becomes_error(self, mock_agent_cls):
        """If agent returns without setting gate decision, status is 'error'."""
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 0
        agent_instance._last_gate_decision = ""

        result = run_research("test query", mode="quick")

        assert result.status == "error"


# --- context parameter ---


class TestContextParameter:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    @patch("research_agent.resolve_context_path")
    def test_context_name_passed_to_agent(self, mock_resolve, mock_agent_cls):
        """context='pfe' resolves to a path and passes it to the agent."""
        from pathlib import Path

        mock_resolve.return_value = Path("contexts/pfe.md")
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 3
        agent_instance._last_gate_decision = "full_report"
        agent_instance.last_critique = None

        run_research("test", mode="quick", context="pfe")

        mock_resolve.assert_called_once_with("pfe")
        _, kwargs = mock_agent_cls.call_args
        assert kwargs["context_path"] == Path("contexts/pfe.md")
        assert kwargs["no_context"] is False

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    @patch("research_agent.resolve_context_path")
    def test_context_none_string_sets_no_context(self, mock_resolve, mock_agent_cls):
        """context='none' should set no_context=True."""
        mock_resolve.return_value = None  # resolve_context_path("none") returns None
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 3
        agent_instance._last_gate_decision = "full_report"
        agent_instance.last_critique = None

        run_research("test", mode="quick", context="none")

        _, kwargs = mock_agent_cls.call_args
        assert kwargs["context_path"] is None
        assert kwargs["no_context"] is True

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.ResearchAgent")
    def test_no_context_param_allows_auto_detect(self, mock_agent_cls):
        """When context is not passed, agent gets default (auto-detect)."""
        agent_instance = mock_agent_cls.return_value
        agent_instance.research_async = AsyncMock(return_value="# Report")
        agent_instance._last_source_count = 3
        agent_instance._last_gate_decision = "full_report"
        agent_instance.last_critique = None

        run_research("test", mode="quick")

        _, kwargs = mock_agent_cls.call_args
        assert kwargs.get("context_path") is None
        assert kwargs.get("no_context") is False
