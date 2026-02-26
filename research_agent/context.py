"""Business context loading."""

import logging
from collections import Counter
from pathlib import Path

import yaml

from .context_result import ContextResult
from .critique import DIMENSIONS
from .sanitize import sanitize_content

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path("research_context.md")

# Per-run cache: avoids re-reading the same context file multiple times.
# Call clear_context_cache() at the start of each research run.
_context_cache: dict[str, ContextResult] = {}


def clear_context_cache() -> None:
    """Clear the per-run context cache. Call at the start of each research run."""
    _context_cache.clear()


def load_full_context(context_path: Path | None = None) -> ContextResult:
    """Load the complete business context file.

    Caches the result per path to avoid redundant disk reads within a run.
    Call clear_context_cache() at the start of each run.

    Args:
        context_path: Path to context file (defaults to research_context.md)

    Returns:
        ContextResult with status indicating outcome.
    """
    path = context_path or DEFAULT_CONTEXT_PATH
    source = str(path)
    if source in _context_cache:
        return _context_cache[source]
    try:
        if not path.exists():
            result = ContextResult.not_configured(source=source)
            _context_cache[source] = result
            return result
        content = path.read_text().strip()
        if not content:
            result = ContextResult.empty(source=source)
            _context_cache[source] = result
            return result
        logger.info(f"Loaded research context from {path}")
        result = ContextResult.loaded(content, source=source)
        _context_cache[source] = result
        return result
    except OSError as e:
        logger.warning(f"Could not read context file {path}: {e}")
        return ContextResult.failed(str(e), source=source)


# --- Critique history loading (Tier 2 adaptive prompts) ---

# Minimum valid critiques needed before providing guidance
_MIN_CRITIQUES_FOR_GUIDANCE = 3


def _validate_critique_yaml(data: dict) -> bool:
    """Check that a parsed YAML dict has the expected critique schema.

    Validates: required keys present, scores are ints in 1-5, text under 200 chars.
    Returns False (skip silently) for any invalid data.
    """
    if not isinstance(data, dict):
        return False

    # Check all dimension scores exist and are in range
    for dim in DIMENSIONS:
        val = data.get(dim)
        if isinstance(val, bool) or not isinstance(val, int) or not (1 <= val <= 5):
            return False

    # Check text fields are strings and within length limit
    for field in ("weaknesses", "suggestions", "query_domain"):
        val = data.get(field)
        if val is not None and not isinstance(val, str):
            return False
        if isinstance(val, str) and len(val) > 200:
            return False

    # overall_pass must be bool
    if "overall_pass" not in data or not isinstance(data["overall_pass"], bool):
        return False

    return True


def _summarize_patterns(passing_critiques: list[dict]) -> str:
    """Aggregate passing critique scores into a concise guidance summary.

    Args:
        passing_critiques: Pre-filtered list of critiques where overall_pass is True.

    Returns a sanitized text suitable for injection into prompts,
    or empty string if fewer than _MIN_CRITIQUES_FOR_GUIDANCE.
    """
    if len(passing_critiques) < _MIN_CRITIQUES_FOR_GUIDANCE:
        return ""

    # Compute dimension averages
    dim_totals: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    for c in passing_critiques:
        for dim in DIMENSIONS:
            dim_totals[dim] += c[dim]

    n = len(passing_critiques)
    dim_avgs = {d: round(dim_totals[d] / n, 1) for d in DIMENSIONS}

    # Find weakest dimensions (below 3.5 average)
    weak_dims = sorted(
        [(d, avg) for d, avg in dim_avgs.items() if avg < 3.5],
        key=lambda x: x[1],
    )

    # Count most frequent weaknesses
    weakness_counter: Counter = Counter()
    for c in passing_critiques:
        w = c.get("weaknesses", "")
        if w:
            weakness_counter[w] += 1

    top_weaknesses = weakness_counter.most_common(2)

    # Build summary
    parts = [f"Based on {n} recent self-critiques:"]

    if weak_dims:
        dim_strs = [f"{d.replace('_', ' ')} ({avg})" for d, avg in weak_dims[:3]]
        parts.append(f"Weakest dimensions: {', '.join(dim_strs)}.")

    if top_weaknesses:
        freq_strs = [
            f'"{sanitize_content(w)}" ({count}/{n} runs)'
            for w, count in top_weaknesses
        ]
        parts.append(f"Recurring weaknesses: {'; '.join(freq_strs)}.")

    if not weak_dims and not top_weaknesses:
        parts.append("All dimensions averaging above 3.5. Maintain current quality.")

    summary = " ".join(parts)
    return sanitize_content(summary)


def load_critique_history(
    meta_dir: Path,
    limit: int = 10,
) -> ContextResult:
    """Load recent critique YAMLs and return summarized patterns.

    Args:
        meta_dir: Directory containing critique-*.yaml files.
        limit: Maximum number of critique files to read.

    Returns:
        ContextResult:
            - NOT_CONFIGURED if fewer than 3 valid passing critiques found.
            - LOADED with summary text if enough passing history exists.
    """
    source = str(meta_dir)

    if not meta_dir.exists():
        return ContextResult.not_configured(source=source)

    # Glob and sort by mtime (newest first)
    files = sorted(
        meta_dir.glob("critique-*.yaml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    if not files:
        return ContextResult.not_configured(source=source)

    valid_critiques: list[dict] = []
    for f in files:
        try:
            data = yaml.safe_load(f.read_text())
        except (yaml.YAMLError, OSError):
            logger.debug(f"Skipping corrupt critique file: {f}")
            continue

        if not _validate_critique_yaml(data):
            logger.debug(f"Skipping invalid critique file: {f}")
            continue

        valid_critiques.append(data)

    passing = [c for c in valid_critiques if c.get("overall_pass") is True]
    if len(passing) < _MIN_CRITIQUES_FOR_GUIDANCE:
        return ContextResult.not_configured(source=source)

    summary = _summarize_patterns(passing)
    if not summary:
        return ContextResult.not_configured(source=source)

    return ContextResult.loaded(summary, source=source)
