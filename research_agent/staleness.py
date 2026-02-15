"""Staleness detection, batch limiting, and audit logging for research gaps."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import StateError
from .schema import Gap, GapStatus


def detect_stale(
    gaps: tuple[Gap, ...],
    default_ttl_days: int = 30,
    now: datetime | None = None,
) -> list[Gap]:
    """Identify gaps whose verified status has expired.

    Compares each VERIFIED gap's last_verified timestamp against its
    ttl_days (or default_ttl_days if the gap has no ttl_days set).

    Only checks gaps with status=VERIFIED. Gaps that are UNKNOWN,
    STALE, or BLOCKED are skipped — staleness is about freshness
    of verified intelligence, not about gaps that were never verified.

    Does NOT cascade through dependencies. If gap A blocks gap B
    and A goes stale, B's status is unchanged. This prevents the
    cascade bomb described in F4.1.

    Args:
        gaps: Gap objects to check.
        default_ttl_days: Fallback TTL for gaps without ttl_days.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        List of Gap objects with status flipped to STALE (new instances).
        Original Gap objects are unchanged.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stale: list[Gap] = []

    for gap in gaps:
        if gap.status is not GapStatus.VERIFIED:
            continue

        # Defensive: treat missing last_verified as stale
        if gap.last_verified is None:
            stale.append(replace(gap, status=GapStatus.STALE))
            continue

        verified_at = datetime.fromisoformat(gap.last_verified)
        ttl = gap.ttl_days if gap.ttl_days is not None else default_ttl_days
        if now - verified_at > timedelta(days=ttl):
            stale.append(replace(gap, status=GapStatus.STALE))

    return stale


def select_batch(
    gaps: tuple[Gap, ...] | list[Gap],
    max_per_run: int = 5,
) -> tuple[Gap, ...]:
    """Select the highest-priority gaps for a single research cycle.

    Sorts by priority (highest first), then by gap ID (alphabetical)
    for deterministic ordering. Returns at most max_per_run gaps.

    Args:
        gaps: Candidate gaps (typically stale + unknown gaps).
        max_per_run: Maximum gaps to return.

    Returns:
        Tuple of at most max_per_run Gap objects, sorted by priority.
    """
    sorted_gaps = sorted(gaps, key=lambda g: (-g.priority, g.id))
    return tuple(sorted_gaps[:max_per_run])


def log_flip(
    log_path: Path | str,
    gap_id: str,
    old_status: GapStatus,
    new_status: GapStatus,
    reason: str,
    now: datetime | None = None,
) -> None:
    """Append a status flip event to the audit log.

    Each entry is a single line of structured text:
    [ISO_TIMESTAMP] gap_id: old_status -> new_status (reason)

    The log file is append-only. If it doesn't exist, it is created.
    Parent directories are created if needed.

    Args:
        log_path: Path to the audit log file.
        gap_id: ID of the gap that changed.
        old_status: Previous status.
        new_status: New status.
        reason: Human-readable reason for the flip.
        now: Override timestamp for testing. Defaults to UTC now.

    Raises:
        StateError: If the write fails.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    timestamp = now.isoformat()
    line = f"[{timestamp}] {gap_id}: {old_status.value} -> {new_status.value} ({reason})\n"

    path = Path(log_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line)
    except OSError as exc:
        raise StateError(f"Failed to write audit log: {exc}") from exc
