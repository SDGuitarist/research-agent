"""Business context loading and stage-appropriate slicing."""

import logging
from pathlib import Path

from .context_result import ContextResult

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path("research_context.md")

# Section headers included in each slice (matched against ## headings)
_SEARCH_SECTIONS = {
    "Two Brands, One Operator",
    "Target Market",
    "Search & Research Parameters",
    "Research Matching Criteria",
}

_SYNTHESIS_SECTIONS = {
    "Two Brands, One Operator",
    "How the Brands Work Together",
    "Target Market",
    "Key Differentiators",
    "Competitive Position",
}


def load_full_context(context_path: Path | None = None) -> ContextResult:
    """Load the complete business context file.

    Args:
        context_path: Path to context file (defaults to research_context.md)

    Returns:
        ContextResult with status indicating outcome.
    """
    path = context_path or DEFAULT_CONTEXT_PATH
    source = str(path)
    try:
        if not path.exists():
            return ContextResult.not_configured(source=source)
        content = path.read_text().strip()
        if not content:
            return ContextResult.empty(source=source)
        logger.info(f"Loaded research context from {path}")
        return ContextResult.loaded(content, source=source)
    except OSError as e:
        logger.warning(f"Could not read context file {path}: {e}")
        return ContextResult.failed(str(e), source=source)


def _extract_sections(full_context: str, section_names: set[str]) -> str:
    """Extract specific ## sections from the context file.

    Keeps the file header (everything before first ##) plus any ## section
    whose title matches one of the given names (case-insensitive substring).

    Args:
        full_context: Full text of the context file
        section_names: Set of section title substrings to include

    Returns:
        Filtered context with only matching sections
    """
    lines = full_context.split("\n")
    result_lines: list[str] = []
    include_current = True  # Include header before first ##

    for line in lines:
        if line.startswith("## "):
            section_title = line.removeprefix("## ").strip()
            include_current = any(
                name.lower() in section_title.lower()
                for name in section_names
            )
        if include_current:
            result_lines.append(line)

    return "\n".join(result_lines).strip()


def load_search_context(context_path: Path | None = None) -> ContextResult:
    """Load context slice for search/decomposition.

    Includes: brand names, geography, service types, search parameters.
    Excludes: pricing, voice guidelines, 'What We Are NOT', contact info.
    """
    full_result = load_full_context(context_path)
    if not full_result:
        return ContextResult.not_configured(source=full_result.source)
    sliced = _extract_sections(full_result.content, _SEARCH_SECTIONS)
    return ContextResult.loaded(sliced, source=full_result.source)


def load_synthesis_context(context_path: Path | None = None) -> ContextResult:
    """Load context slice for skeptic agents and final synthesis.

    Includes: competitive positioning, brand identity, differentiators.
    Excludes: pricing tables, 'What We Are NOT' (causes hedging),
              search parameters, contact info.
    """
    full_result = load_full_context(context_path)
    if not full_result:
        return ContextResult.not_configured(source=full_result.source)
    sliced = _extract_sections(full_result.content, _SYNTHESIS_SECTIONS)
    return ContextResult.loaded(sliced, source=full_result.source)
