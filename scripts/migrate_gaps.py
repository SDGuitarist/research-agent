#!/usr/bin/env python3
"""One-time, idempotent import of the PFE gap YAML into Postgres."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from research_agent.db import close_pool, open_pool
from research_agent.errors import SchemaError
from research_agent.schema import detect_cycles, load_gaps, load_schema_file
from research_agent.staleness import detect_stale
from research_agent.state import save_schema

DEFAULT_GAPS_PATH = Path(__file__).resolve().parents[1] / "gaps" / "pfe.yaml"


def _staleness_verdict(gap, now: datetime) -> bool:
    return bool(detect_stale((gap,), now=now))


def migrate_gaps(conn, path: Path | str = DEFAULT_GAPS_PATH) -> int:
    """Validate and upsert a gap YAML, then assert migration equivalence."""
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

    checked_at = datetime.now(timezone.utc)
    sample = source.gaps[0]
    before_verdict = _staleness_verdict(sample, checked_at)

    with conn.transaction():
        changed = save_schema(conn, source.gaps)
        imported = load_gaps(conn)
        row_count = conn.execute("SELECT count(*) AS count FROM gaps").fetchone()["count"]

        assert row_count == len(source.gaps), (
            f"Gap import row-count mismatch: YAML={len(source.gaps)}, DB={row_count}"
        )

        imported_by_id = {gap.id: gap for gap in imported.gaps}
        assert imported_by_id == {gap.id: gap for gap in source.gaps}, (
            "Gap import state differs from the validated YAML"
        )
        after_verdict = _staleness_verdict(imported_by_id[sample.id], checked_at)
        assert after_verdict == before_verdict, (
            f"Staleness verdict changed during import for gap {sample.id!r}"
        )

    return changed


def main() -> None:
    pool = open_pool()
    try:
        with pool.connection() as conn:
            changed = migrate_gaps(conn)
        print(f"Imported {len(load_schema_file(DEFAULT_GAPS_PATH).gaps)} gaps; {changed} changed.")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
