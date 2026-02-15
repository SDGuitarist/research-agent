"""Staleness detection for research gaps."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

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
