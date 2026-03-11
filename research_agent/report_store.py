"""Report storage utilities shared by CLI and MCP server."""

import re
from datetime import datetime
from pathlib import Path

from .results import ReportInfo

REPORTS_DIR = Path("reports")


def _literal_reports_root() -> Path:
    """Return an absolute reports/ path without resolving symlinks."""
    return REPORTS_DIR if REPORTS_DIR.is_absolute() else Path.cwd() / REPORTS_DIR


def _resolves_within_reports_root(path: Path | str) -> bool:
    """Check that a path resolves inside the literal reports/ root."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        return False
    return resolved.is_relative_to(_literal_reports_root())


def sanitize_filename(query: str, max_length: int = 50) -> str:
    """
    Sanitize a query string for use in a filename.

    - Lowercase
    - Replace spaces with underscores
    - Remove non-alphanumeric chars except underscores
    - Truncate to max_length
    """
    # Lowercase and replace spaces
    sanitized = query.lower().replace(" ", "_")
    # Keep only alphanumeric and underscores
    sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit("_", 1)[0]
    return sanitized or "research"


def get_auto_save_path(query: str) -> Path:
    """Generate auto-save path for standard and deep mode reports."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S%f")  # Microseconds prevent collisions
    safe_query = sanitize_filename(query)
    filename = f"{safe_query}_{timestamp}.md"
    path = REPORTS_DIR / filename
    if not _resolves_within_reports_root(path):
        raise OSError(
            "Refusing to use a reports/ path outside the literal repo-local reports/ directory"
        )
    return path


# Regex patterns for extracting date from report filenames
# Old format: 2026-02-03_183703056652_query_name.md (timestamp first)
_OLD_FORMAT = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{6,}_(.+)\.md$")
# New format: query_name_2026-02-03_183703056652.md (query first)
_NEW_FORMAT = re.compile(r"^(.+)_(\d{4}-\d{2}-\d{2})_\d{6,}\.md$")


def get_reports() -> list[ReportInfo]:
    """Return metadata for all saved reports, sorted newest-first.

    Returns:
        List of ReportInfo objects. Empty list if no reports directory
        or no report files exist.
    """
    if not REPORTS_DIR.is_dir():
        return []
    if not _resolves_within_reports_root(REPORTS_DIR):
        return []

    md_files = sorted(REPORTS_DIR.glob("*.md"))
    if not md_files:
        return []

    results: list[ReportInfo] = []
    for f in md_files:
        if not _resolves_within_reports_root(f):
            continue
        name = f.name
        old_match = _OLD_FORMAT.match(name)
        new_match = _NEW_FORMAT.match(name)

        if old_match:
            results.append(ReportInfo(filename=name, date=old_match.group(1), query_name=old_match.group(2)))
        elif new_match:
            results.append(ReportInfo(filename=name, date=new_match.group(2), query_name=new_match.group(1)))
        else:
            results.append(ReportInfo(filename=name, date="", query_name=name))

    # Sort by date newest-first (undated files sort to beginning)
    results.sort(key=lambda r: r.date, reverse=True)
    return results
