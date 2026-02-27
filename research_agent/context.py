"""Context loading and auto-detection."""

import logging
from collections import Counter
from pathlib import Path

import yaml
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError, APITimeoutError

from .context_result import ContextResult
from .critique import DIMENSIONS
from .errors import ANTHROPIC_TIMEOUT
from .modes import DEFAULT_MODEL
from .sanitize import sanitize_content

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path("research_context.md")
CONTEXTS_DIR = Path("contexts")

def new_context_cache() -> dict[str, ContextResult]:
    """Create a fresh per-run context cache.

    Pass the returned dict to load_full_context() as the cache parameter.
    Each ResearchAgent run should create its own cache.
    """
    return {}


def resolve_context_path(name: str) -> Path | None:
    """Resolve a --context flag value to a file path.

    Args:
        name: Context name from CLI. "none" means no context.
              Otherwise looks for contexts/<name>.md.

    Returns:
        Path to the context file, or None if "none" was specified.

    Raises:
        FileNotFoundError: If the named context file doesn't exist.
    """
    if name.lower() == "none":
        return None

    # Defense layer 1: reject names that look like paths
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(
            f"Invalid context name: {name!r} (must be a simple name, not a path)"
        )

    # Defense layer 2: verify resolved path stays inside contexts/
    path = (CONTEXTS_DIR / f"{name}.md").resolve()
    contexts_resolved = CONTEXTS_DIR.resolve()
    if not path.is_relative_to(contexts_resolved):
        raise ValueError(
            f"Context name {name!r} resolves outside contexts/ directory"
        )

    if not path.exists():
        available = sorted(p.stem for p in CONTEXTS_DIR.glob("*.md")) if CONTEXTS_DIR.is_dir() else []
        hint = f" Available: {', '.join(available)}" if available else ""
        raise FileNotFoundError(f"Context file not found: {path}{hint}")
    return path


def load_full_context(
    context_path: Path | None = None,
    cache: dict[str, ContextResult] | None = None,
) -> ContextResult:
    """Load the complete research context file.

    Args:
        context_path: Path to context file (defaults to research_context.md)
        cache: Optional per-run cache dict (from new_context_cache()).
            If provided, avoids redundant disk reads within a run.

    Returns:
        ContextResult with status indicating outcome.
    """
    path = context_path or DEFAULT_CONTEXT_PATH
    source = str(path)
    if cache is not None and source in cache:
        return cache[source]
    try:
        if not path.exists():
            result = ContextResult.not_configured(source=source)
            if cache is not None:
                cache[source] = result
            return result
        content = path.read_text().strip()
        if not content:
            result = ContextResult.empty(source=source)
            if cache is not None:
                cache[source] = result
            return result
        content = sanitize_content(content)
        logger.info("Loaded research context from %s", path)
        result = ContextResult.loaded(content, source=source)
        if cache is not None:
            cache[source] = result
        return result
    except OSError as e:
        logger.warning("Could not read context file %s: %s", path, e)
        return ContextResult.failed(str(e), source=source)


# --- Auto-detection: pick context file based on query ---

# Maximum lines to read from each context file for the preview
_PREVIEW_LINES = 5


def list_available_contexts() -> list[tuple[str, str]]:
    """List context files in contexts/ with a short preview of each.

    Returns:
        List of (name, preview) tuples. Empty list if contexts/ doesn't exist
        or has no .md files.
    """
    if not CONTEXTS_DIR.is_dir():
        return []

    results = []
    for path in sorted(CONTEXTS_DIR.glob("*.md")):
        try:
            lines = []
            with path.open() as f:
                for i, line in enumerate(f):
                    if i >= _PREVIEW_LINES:
                        break
                    lines.append(line.rstrip())
            preview = "\n".join(lines)
        except OSError:
            preview = "(could not read)"
        results.append((path.stem, preview))
    return results


def auto_detect_context(
    client: Anthropic,
    query: str,
    model: str = DEFAULT_MODEL,
) -> Path | None:
    """Ask the LLM which context file (if any) is relevant to the query.

    Only called when no --context flag is given and contexts/ directory exists
    with at least one .md file.

    Args:
        client: Anthropic client (sync).
        query: The user's research query.
        model: Claude model to use.

    Returns:
        Path to the selected context file, or None if no context matches.
        Returns None on any error (LLM failure, bad response, etc.).
    """
    available = list_available_contexts()
    if not available:
        return None

    # Build a numbered list of context files with sanitized previews
    safe_query = sanitize_content(query)
    options = []
    for i, (name, preview) in enumerate(available, 1):
        safe_preview = sanitize_content(preview)
        options.append(f"{i}. {name}\n{safe_preview}")
    options_text = "\n\n".join(options)

    prompt = (
        f"Given this research query:\n\n"
        f"  <query>{safe_query}</query>\n\n"
        f"Which of these context files (if any) is relevant? "
        f"A context file is relevant if the query is about topics covered by that context.\n\n"
        f"{options_text}\n\n"
        f"Reply with ONLY the context name (e.g. \"{available[0][0]}\") or \"none\" "
        f"if no context is relevant. Do not explain."
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=50,
            timeout=ANTHROPIC_TIMEOUT,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.content[0].text.strip().lower()
    except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
        logger.warning("Auto-detect context failed: %s", e)
        return None

    # Match answer to a known context name
    valid_names = {name.lower(): name for name, _ in available}
    if answer in ("none", "\"none\""):
        logger.info("Auto-detect: no context matches query")
        return None

    # Strip quotes if the LLM wrapped the name
    cleaned = answer.strip("\"'")
    if cleaned in valid_names:
        original_name = valid_names[cleaned]
        path = CONTEXTS_DIR / f"{original_name}.md"
        logger.info("Auto-detect: selected context '%s'", original_name)
        return path

    # Fallback: check if any valid context name appears as a word in the response
    answer_words = answer.split()
    for valid_lower, original_name in valid_names.items():
        if valid_lower in answer_words:
            path = CONTEXTS_DIR / f"{original_name}.md"
            logger.info(
                "Auto-detect: extracted context '%s' from verbose response",
                original_name,
            )
            return path

    logger.warning("Auto-detect returned unrecognized answer: %r", answer)
    return None


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
