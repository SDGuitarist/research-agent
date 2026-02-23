"""Tests for ResearchResult and ModeInfo frozen dataclasses."""

import pytest

from research_agent.critique import CritiqueResult
from research_agent.results import ModeInfo, ResearchResult


class TestResearchResult:
    def test_fields_accessible(self):
        result = ResearchResult(
            report="# Report",
            query="test query",
            mode="quick",
            sources_used=4,
            status="full_report",
        )
        assert result.report == "# Report"
        assert result.query == "test query"
        assert result.mode == "quick"
        assert result.sources_used == 4
        assert result.status == "full_report"
        assert result.critique is None

    def test_critique_field_populated(self):
        cr = CritiqueResult(4, 3, 5, 2, 4, "weak", "try harder", "music")
        result = ResearchResult(
            report="# Report",
            query="test",
            mode="standard",
            sources_used=5,
            status="full_report",
            critique=cr,
        )
        assert result.critique is cr
        assert result.critique.source_diversity == 4

    def test_frozen_immutability(self):
        result = ResearchResult(
            report="# Report",
            query="test query",
            mode="quick",
            sources_used=4,
            status="full_report",
        )
        with pytest.raises(AttributeError):
            result.report = "changed"
        with pytest.raises(AttributeError):
            result.sources_used = 10

    def test_repr(self):
        result = ResearchResult(
            report="# Report",
            query="test query",
            mode="quick",
            sources_used=4,
            status="full_report",
        )
        r = repr(result)
        assert "ResearchResult" in r
        assert "test query" in r
        assert "quick" in r

    def test_equality(self):
        kwargs = dict(
            report="# Report",
            query="test query",
            mode="quick",
            sources_used=4,
            status="full_report",
        )
        assert ResearchResult(**kwargs) == ResearchResult(**kwargs)

    def test_different_status_values(self):
        for status in ("full_report", "short_report", "insufficient_data", "no_new_findings"):
            result = ResearchResult(
                report="# Report",
                query="q",
                mode="standard",
                sources_used=0,
                status=status,
            )
            assert result.status == status


class TestModeInfo:
    def test_fields_accessible(self):
        info = ModeInfo(
            name="quick",
            max_sources=4,
            word_target=800,
            cost_estimate="$0.05",
            auto_save=False,
        )
        assert info.name == "quick"
        assert info.max_sources == 4
        assert info.word_target == 800
        assert info.cost_estimate == "$0.05"
        assert info.auto_save is False

    def test_frozen_immutability(self):
        info = ModeInfo(
            name="quick",
            max_sources=4,
            word_target=800,
            cost_estimate="$0.05",
            auto_save=False,
        )
        with pytest.raises(AttributeError):
            info.name = "deep"
        with pytest.raises(AttributeError):
            info.max_sources = 99

    def test_equality(self):
        kwargs = dict(
            name="standard",
            max_sources=10,
            word_target=2000,
            cost_estimate="$0.15",
            auto_save=True,
        )
        assert ModeInfo(**kwargs) == ModeInfo(**kwargs)
