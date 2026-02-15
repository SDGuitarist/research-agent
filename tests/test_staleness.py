"""Tests for staleness detection, batch limiting, and audit logging."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from research_agent.errors import StateError
from research_agent.schema import Gap, GapStatus
from research_agent.staleness import detect_stale, log_flip, select_batch

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


class TestSelectBatch:
    def test_batch_selects_highest_priority(self):
        gaps = tuple(
            Gap(id=f"g{i}", category="market", priority=i) for i in range(1, 11)
        )
        result = select_batch(gaps, max_per_run=3)
        assert len(result) == 3
        assert result[0].priority == 10
        assert result[1].priority == 9
        assert result[2].priority == 8

    def test_batch_respects_limit(self):
        gaps = tuple(
            Gap(id=f"g{i}", category="market", priority=5) for i in range(10)
        )
        result = select_batch(gaps, max_per_run=3)
        assert len(result) == 3

    def test_batch_breaks_ties_by_id(self):
        gaps = (
            Gap(id="charlie", category="market", priority=5),
            Gap(id="alpha", category="market", priority=5),
            Gap(id="bravo", category="market", priority=5),
        )
        result = select_batch(gaps, max_per_run=3)
        assert result[0].id == "alpha"
        assert result[1].id == "bravo"
        assert result[2].id == "charlie"

    def test_batch_fewer_than_limit(self):
        gaps = (
            Gap(id="a", category="market", priority=5),
            Gap(id="b", category="market", priority=3),
        )
        result = select_batch(gaps, max_per_run=5)
        assert len(result) == 2

    def test_batch_empty_input(self):
        result = select_batch((), max_per_run=5)
        assert result == ()

    def test_batch_returns_tuple(self):
        gaps = [Gap(id="a", category="market")]
        result = select_batch(gaps, max_per_run=5)
        assert isinstance(result, tuple)


class TestLogFlip:
    def test_log_flip_creates_file(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_flip(log_file, "pricing", GapStatus.VERIFIED, GapStatus.STALE, "TTL expired", now=_NOW)
        assert log_file.exists()
        assert "pricing" in log_file.read_text()

    def test_log_flip_appends(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_flip(log_file, "first", GapStatus.VERIFIED, GapStatus.STALE, "reason1", now=_NOW)
        log_flip(log_file, "second", GapStatus.UNKNOWN, GapStatus.VERIFIED, "reason2", now=_NOW)
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]

    def test_log_flip_format(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_flip(log_file, "pricing", GapStatus.VERIFIED, GapStatus.STALE, "TTL expired: 45 > 30", now=_NOW)
        line = log_file.read_text().strip()
        expected = f"[{_NOW.isoformat()}] pricing: verified -> stale (TTL expired: 45 > 30)"
        assert line == expected

    def test_log_flip_creates_parent_dirs(self, tmp_path):
        log_file = tmp_path / "nested" / "deep" / "audit.log"
        log_flip(log_file, "gap1", GapStatus.VERIFIED, GapStatus.STALE, "expired", now=_NOW)
        assert log_file.exists()

    def test_log_flip_uses_utc(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_flip(log_file, "gap1", GapStatus.VERIFIED, GapStatus.STALE, "expired")
        line = log_file.read_text()
        # UTC timestamps contain +00:00
        assert "+00:00" in line

    def test_log_flip_custom_timestamp(self, tmp_path):
        log_file = tmp_path / "audit.log"
        custom = datetime(2025, 6, 15, 8, 30, 0, tzinfo=timezone.utc)
        log_flip(log_file, "gap1", GapStatus.VERIFIED, GapStatus.STALE, "expired", now=custom)
        line = log_file.read_text()
        assert custom.isoformat() in line

    def test_log_flip_records_reason(self, tmp_path):
        log_file = tmp_path / "audit.log"
        reason = "TTL expired: 45 days > 30 day limit"
        log_flip(log_file, "gap1", GapStatus.VERIFIED, GapStatus.STALE, reason, now=_NOW)
        assert reason in log_file.read_text()

    def test_log_flip_write_error_raises(self, tmp_path):
        bad_path = tmp_path / "audit.log"
        with patch("pathlib.Path.open", side_effect=OSError("disk full")):
            with pytest.raises(StateError, match="Failed to write audit log"):
                log_flip(bad_path, "gap1", GapStatus.VERIFIED, GapStatus.STALE, "reason", now=_NOW)
