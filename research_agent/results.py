"""Structured result types for the research agent public API."""

from dataclasses import dataclass


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
    """
    report: str
    query: str
    mode: str
    sources_used: int
    status: str


@dataclass(frozen=True)
class ModeInfo:
    """Information about an available research mode."""
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
