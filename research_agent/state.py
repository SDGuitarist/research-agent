"""State persistence for targeted Postgres gap updates."""

from dataclasses import replace
from datetime import datetime, timezone

from psycopg import Error as PsycopgError

from .errors import StateError
from .schema import Gap, GapStatus


def save_schema(conn, gaps: tuple[Gap, ...]) -> int:
    """Upsert only the supplied gap rows using an injected connection.

    The caller owns the outer transaction. The nested transaction here is a
    savepoint when one already exists, which keeps rollback-per-test isolation.
    Returns the number of rows whose stored values actually changed.
    """
    changed = 0
    try:
        with conn.transaction():
            for gap in gaps:
                cursor = conn.execute(
                """INSERT INTO gaps (
                       id, category, status, priority, last_verified, last_checked,
                       ttl_days, blocks, blocked_by, findings
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       category = EXCLUDED.category,
                       status = EXCLUDED.status,
                       priority = EXCLUDED.priority,
                       last_verified = EXCLUDED.last_verified,
                       last_checked = EXCLUDED.last_checked,
                       ttl_days = EXCLUDED.ttl_days,
                       blocks = EXCLUDED.blocks,
                       blocked_by = EXCLUDED.blocked_by,
                       findings = EXCLUDED.findings,
                       updated_at = now()
                   WHERE (gaps.category, gaps.status, gaps.priority,
                          gaps.last_verified, gaps.last_checked, gaps.ttl_days,
                          gaps.blocks, gaps.blocked_by, gaps.findings)
                         IS DISTINCT FROM
                         (EXCLUDED.category, EXCLUDED.status, EXCLUDED.priority,
                          EXCLUDED.last_verified, EXCLUDED.last_checked,
                          EXCLUDED.ttl_days, EXCLUDED.blocks, EXCLUDED.blocked_by,
                          EXCLUDED.findings)""",
                    (
                        gap.id, gap.category, gap.status.value, gap.priority,
                        gap.last_verified, gap.last_checked, gap.ttl_days,
                        list(gap.blocks), list(gap.blocked_by), gap.findings,
                    ),
                )
                changed += cursor.rowcount
    except PsycopgError as exc:
        raise StateError(f"Failed to save gap state: {exc}") from exc
    return changed


def mark_checked(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with last_checked set to now.

    Updates last_checked only. Does NOT change status or last_verified.
    Use when a gap was researched but no new findings were found.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with updated last_checked.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return replace(gap, last_checked=now.isoformat())


def mark_verified(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with status=VERIFIED and timestamps set to now.

    Updates last_verified, last_checked, and status. Use when a gap
    was researched and new findings were confirmed.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with status=VERIFIED and fresh timestamps.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now.isoformat()
    return replace(gap, status=GapStatus.VERIFIED, last_verified=ts, last_checked=ts)
