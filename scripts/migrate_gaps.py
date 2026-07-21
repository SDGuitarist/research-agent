#!/usr/bin/env python3
"""One-time, idempotent import of the PFE gap YAML into Postgres."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from research_agent.db import close_pool, open_pool
from research_agent.errors import SchemaError
from research_agent.schema import Gap, detect_cycles, load_gaps, load_schema_file
from research_agent.staleness import detect_stale
from research_agent.state import save_schema

DEFAULT_GAPS_PATH = Path(__file__).resolve().parents[1] / "gaps" / "pfe.yaml"


class MigrationError(Exception):
    """A post-import self-check failed and the import was rolled back.

    Raised instead of bare ``assert`` so the checks stay active under
    ``python -O`` (which strips assertions).
    """


def _stale_ids(gaps: tuple[Gap, ...], now: datetime) -> frozenset[str]:
    """Return the set of gap ids that detect_stale flags at ``now``."""
    return frozenset(gap.id for gap in detect_stale(gaps, now=now))


def migrate_gaps(
    conn, path: Path | str = DEFAULT_GAPS_PATH, now: datetime | None = None
) -> int:
    """Validate and upsert a gap YAML, then verify migration equivalence.

    Returns the number of rows whose stored values actually changed (0 on an
    idempotent re-run). Raises SchemaError for a bad source (missing/empty,
    duplicate ids, dependency cycles) before any write. Raises MigrationError —
    rolling the whole import back — if the post-import state does not match the
    validated YAML: row count, per-gap equality, and the staleness verdict of
    EVERY imported gap must be identical before and after.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    source = load_schema_file(path)
    if not source.is_loaded:
        raise SchemaError(f"Gap import source is missing or empty: {path}")

    gap_ids = [gap.id for gap in source.gaps]
    if len(set(gap_ids)) != len(gap_ids):
        raise SchemaError("Gap import source contains duplicate gap IDs")

    cycles = detect_cycles(source.gaps)
    if cycles:
        rendered = ", ".join(" -> ".join(cycle) for cycle in cycles)
        raise SchemaError(f"Gap import source contains dependency cycles: {rendered}")

    pre_stale = _stale_ids(source.gaps, now)

    with conn.transaction():
        changed = save_schema(conn, source.gaps)
        imported = load_gaps(conn)

        if len(imported.gaps) != len(source.gaps):
            raise MigrationError(
                f"Gap import row-count mismatch: "
                f"YAML={len(source.gaps)}, DB={len(imported.gaps)}"
            )
        if {g.id: g for g in imported.gaps} != {g.id: g for g in source.gaps}:
            raise MigrationError("Gap import state differs from the validated YAML")
        post_stale = _stale_ids(imported.gaps, now)
        if post_stale != pre_stale:
            raise MigrationError(
                "Staleness verdicts changed during import: "
                f"before={sorted(pre_stale)}, after={sorted(post_stale)}"
            )

    return changed


def main() -> None:
    pool = open_pool()
    try:
        with pool.connection() as conn:
            changed = migrate_gaps(conn)
        total = len(load_schema_file(DEFAULT_GAPS_PATH).gaps)
        print(f"Imported {total} gaps; {changed} changed.")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
