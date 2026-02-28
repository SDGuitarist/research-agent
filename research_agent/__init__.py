"""Research agent — search the web and generate structured reports."""

__version__ = "0.18.0"

import asyncio
import os

from .agent import ResearchAgent
from .report_store import get_reports
from .context import list_available_contexts, load_critique_history, resolve_context_path
from .context_result import ContextResult, ContextStatus, ReportTemplate
from .critique import CritiqueResult, critique_report_file
from .errors import ResearchError
from .modes import ResearchMode
from .results import ModeInfo, ReportInfo, ResearchResult

__all__ = [
    "ContextResult",
    "ContextStatus",
    "CritiqueResult",
    "ModeInfo",
    "ReportInfo",
    "ReportTemplate",
    "ResearchAgent",
    "ResearchError",
    "ResearchMode",
    "ResearchResult",
    "critique_report_file",
    "get_reports",
    "list_available_contexts",
    "list_modes",
    "load_critique_history",
    "resolve_context_path",
    "run_research",
    "run_research_async",
]


def run_research(
    query: str,
    mode: str = "standard",
    context: str | None = None,
    skip_critique: bool = False,
    max_sources: int | None = None,
) -> ResearchResult:
    """Run a research query and return a structured result.

    Args:
        query: The research question.
        mode: Research mode — "quick", "standard", or "deep".
        context: Context name (matches contexts/<name>.md), "none" to
            skip context, or None to auto-detect from the query.
        skip_critique: If True, skip self-critique after report generation.
        max_sources: Override the mode's default source count.

    Returns:
        ResearchResult with report, query, mode, sources_used, status.

    Raises:
        ResearchError: If query is empty, mode is invalid,
            API keys are missing, or research fails.
            Subclasses (SearchError, SynthesisError) propagate
            from the pipeline for specific failures.

    Note:
        The research agent prints progress to stdout during execution.
        This will be converted to logging in a future release.

        Set ANTHROPIC_API_KEY and TAVILY_API_KEY environment variables
        before calling. Reports auto-save to ./reports/ relative to CWD
        for standard and deep modes.
    """
    try:
        return asyncio.run(run_research_async(
            query, mode=mode, context=context,
            skip_critique=skip_critique, max_sources=max_sources,
        ))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            raise ResearchError(
                "run_research() cannot be called from async context. "
                "Use 'await run_research_async()' instead."
            ) from e
        raise


async def run_research_async(
    query: str,
    mode: str = "standard",
    context: str | None = None,
    skip_critique: bool = False,
    max_sources: int | None = None,
) -> ResearchResult:
    """Async version of run_research for use in async contexts.

    Same interface as run_research(). Use this when calling from
    an async context (MCP servers, FastAPI, Jupyter, etc.)
    where asyncio.run() would fail.
    """
    if not query or not query.strip():
        raise ResearchError("Query cannot be empty")

    try:
        research_mode = ResearchMode.from_name(mode)
    except ValueError:
        raise ResearchError(
            f"Invalid mode: {mode!r}. Must be one of: deep, quick, standard"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ResearchError(
            "ANTHROPIC_API_KEY environment variable is required"
        )

    if not os.environ.get("TAVILY_API_KEY"):
        raise ResearchError(
            "TAVILY_API_KEY environment variable is required"
        )

    # Resolve context parameter to agent constructor args
    context_path = None
    no_context = False
    if context is not None:
        try:
            context_path = resolve_context_path(context)
        except (FileNotFoundError, ValueError) as e:
            raise ResearchError(str(e)) from e
        if context_path is None:
            no_context = True  # context="none"

    agent = ResearchAgent(
        mode=research_mode, context_path=context_path, no_context=no_context,
        skip_critique=skip_critique, max_sources=max_sources,
    )
    report = await agent.research_async(query)

    return ResearchResult(
        report=report,
        query=query,
        mode=research_mode.name,
        sources_used=agent.last_source_count,
        status=agent.last_gate_decision or "error",
        critique=agent.last_critique,
    )


def list_modes() -> list[ModeInfo]:
    """List available research modes with their configuration.

    Returns:
        List of ModeInfo objects with name, max_sources, word_target,
        cost_estimate, and auto_save fields.
    """
    modes = [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]
    return [
        ModeInfo(
            name=m.name,
            max_sources=m.max_sources,
            word_target=m.word_target,
            cost_estimate=m.cost_estimate,
            auto_save=m.auto_save,
        )
        for m in modes
    ]
