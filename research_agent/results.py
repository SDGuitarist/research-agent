"""Structured result types for the research agent public API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .critique import CritiqueResult


@dataclass(frozen=True)
class ResearchResult:
    """Result from a research query.

    Attributes:
        report: The markdown report.
        query: The original query string.
        mode: The research mode name (quick/standard/deep).
        sources_used: Number of sources that contributed to the report
            (survived the relevance gate).
        status: Gate decision — "full_report", "short_report",
                "insufficient_data", or "no_new_findings".
        critique: Self-critique result, or None if critique was skipped
            (quick mode) or failed.
    """
    report: str
    query: str
    mode: str
    sources_used: int
    status: str
    critique: CritiqueResult | None = field(default=None)
    iteration_status: str = field(default="skipped")
    iteration_sections: tuple[str, ...] = field(default=())
    source_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ModeInfo:
    """Information about an available research mode."""
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
    model: str = ""
    planning_model: str = ""
    relevance_model: str = ""


@dataclass(frozen=True)
class ReportInfo:
    """Metadata for a saved report file."""
    filename: str
    date: str
    query_name: str
