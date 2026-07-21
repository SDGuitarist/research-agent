"""Report storage utilities shared by CLI and MCP server."""

import re
import uuid
from datetime import datetime
from pathlib import Path

from psycopg import Error as PsycopgError
from psycopg.errors import UniqueViolation

from .errors import StateError
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


# Retry budget for the astronomically-rare report_key hex-suffix collision.
_MAX_KEY_ATTEMPTS = 3


def save_report(
    conn,
    *,
    query: str,
    mode: str,
    content: str,
    gate_decision: str | None = None,
    sources_used: int | None = None,
    job_id: uuid.UUID | None = None,
) -> str:
    """Insert a report row using an injected connection; return its report_key.

    The caller owns the outer transaction — the nested transaction here is a
    savepoint when one already exists; never conn.commit() inside.

    report_key = f"{slug}-{uuid8}" is generated once at insert time and stored
    in a UNIQUE column; consumers must never re-derive it. An 8-hex collision
    surfaces as UniqueViolation on report_key — regenerate the suffix and
    retry. A job_id conflict is a real invariant breach (one report per job)
    and is not retried.

    Raises:
        StateError: On any database failure other than a retryable
            report_key collision.
    """
    for _ in range(_MAX_KEY_ATTEMPTS):
        report_id = uuid.uuid4()
        report_key = f"{sanitize_filename(query)}-{report_id.hex[:8]}"
        try:
            with conn.transaction():
                conn.execute(
                    """INSERT INTO reports
                           (id, job_id, report_key, query, mode, content,
                            gate_decision, sources_used)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (report_id, job_id, report_key, query, mode, content,
                     gate_decision, sources_used),
                )
            return report_key
        except UniqueViolation as exc:
            if "report_key" not in (exc.diag.constraint_name or ""):
                raise StateError(f"Failed to save report: {exc}") from exc
            continue
        except PsycopgError as exc:
            raise StateError(f"Failed to save report: {exc}") from exc
    raise StateError(
        f"Failed to save report: report_key collided {_MAX_KEY_ATTEMPTS} times"
    )


def get_reports(conn) -> list[ReportInfo]:
    """Return metadata for all saved reports, sorted newest-first.

    Reads the reports table with an injected connection. ``filename``
    carries the report_key (the canonical lookup handle) and
    ``query_name`` the original query text.

    Raises:
        StateError: On database failure.
    """
    try:
        rows = conn.execute(
            """SELECT report_key, query, created_at
               FROM reports ORDER BY created_at DESC, id DESC"""
        ).fetchall()
    except PsycopgError as exc:
        raise StateError(f"Failed to list reports: {exc}") from exc
    return [
        ReportInfo(
            filename=row["report_key"],
            date=row["created_at"].strftime("%Y-%m-%d"),
            query_name=row["query"],
        )
        for row in rows
    ]


def get_report(conn, report_key: str) -> str | None:
    """Return a report's verbatim content by canonical key, or ``None``.

    The injected connection and its transaction belong to the caller.

    Raises:
        StateError: On database failure.
    """
    try:
        row = conn.execute(
            "SELECT content FROM reports WHERE report_key = %s",
            (report_key,),
        ).fetchone()
    except PsycopgError as exc:
        raise StateError(f"Failed to retrieve report: {exc}") from exc
    return None if row is None else row["content"]
