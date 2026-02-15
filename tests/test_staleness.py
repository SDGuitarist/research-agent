"""Tests for staleness detection (Deliverable 3)."""

from datetime import datetime, timedelta, timezone

from research_agent.schema import Gap, GapStatus
from research_agent.staleness import detect_stale

# Fixed reference time for all tests
_NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _verified_gap(gap_id, days_ago, ttl_days=None, **kwargs):
    """Helper: create a VERIFIED gap verified `days_ago` days before _NOW."""
    verified_at = (_NOW - timedelta(days=days_ago)).isoformat()
    return Gap(
        id=gap_id,
        category="market",
        status=GapStatus.VERIFIED,
        last_verified=verified_at,
        ttl_days=ttl_days,
        **kwargs,
    )


class TestDetectStale:
    def test_detect_stale_by_ttl(self):
        gap = _verified_gap("old", days_ago=45)
        result = detect_stale((gap,), default_ttl_days=30, now=_NOW)
        assert len(result) == 1
        assert result[0].id == "old"
        assert result[0].status is GapStatus.STALE

    def test_detect_stale_fresh_gap(self):
        gap = _verified_gap("fresh", days_ago=10)
        result = detect_stale((gap,), default_ttl_days=30, now=_NOW)
        assert result == []

    def test_detect_stale_ignores_unknown(self):
        gap = Gap(id="new", category="market")  # status=UNKNOWN by default
        result = detect_stale((gap,), now=_NOW)
        assert result == []

    def test_detect_stale_ignores_already_stale(self):
        gap = Gap(
            id="already",
            category="market",
            status=GapStatus.STALE,
            last_verified="2025-01-01T00:00:00+00:00",
        )
        result = detect_stale((gap,), now=_NOW)
        assert result == []

    def test_detect_stale_ignores_blocked(self):
        gap = Gap(
            id="blocked",
            category="market",
            status=GapStatus.BLOCKED,
            last_verified="2025-01-01T00:00:00+00:00",
        )
        result = detect_stale((gap,), now=_NOW)
        assert result == []

    def test_no_cascade_through_dependencies(self):
        gap_a = _verified_gap("a", days_ago=45, blocks=("b",))
        gap_b = _verified_gap("b", days_ago=5, blocked_by=("a",))
        result = detect_stale((gap_a, gap_b), default_ttl_days=30, now=_NOW)
        assert len(result) == 1
        assert result[0].id == "a"
        # gap_b stays unchanged — no cascade
        assert gap_b.status is GapStatus.VERIFIED

    def test_uses_gap_ttl_over_default(self):
        gap = _verified_gap("custom", days_ago=20, ttl_days=14)
        result = detect_stale((gap,), default_ttl_days=30, now=_NOW)
        assert len(result) == 1
        assert result[0].id == "custom"

    def test_uses_default_ttl_when_none(self):
        gap = _verified_gap("nottl", days_ago=20, ttl_days=None)
        result = detect_stale((gap,), default_ttl_days=30, now=_NOW)
        # 20 days < 30 day default → not stale
        assert result == []

    def test_stale_gap_has_new_status(self):
        gap = _verified_gap("target", days_ago=45)
        result = detect_stale((gap,), default_ttl_days=30, now=_NOW)
        assert result[0].status is GapStatus.STALE
        assert gap.status is GapStatus.VERIFIED  # original unchanged

    def test_empty_gaps_returns_empty(self):
        result = detect_stale((), now=_NOW)
        assert result == []
