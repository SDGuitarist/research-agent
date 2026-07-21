"""Tests for Postgres gap persistence and timestamp management."""

from datetime import datetime, timezone
from research_agent.schema import Gap, GapStatus, load_gaps
from research_agent.state import (
    mark_checked,
    mark_verified,
    save_schema,
)


class TestSaveSchema:
    def test_save_load_roundtrip(self, db):
        gaps = (
            Gap(id="pricing", category="market", priority=5),
            Gap(
                id="competitor",
                category="market",
                status=GapStatus.VERIFIED,
                last_verified="2026-01-01T00:00:00+00:00",
                blocks=("pricing",),
            ),
        )
        assert save_schema(db, gaps) == 2
        result = load_gaps(db)
        assert result.is_loaded
        assert len(result.gaps) == 2
        assert result.gaps == tuple(sorted(gaps, key=lambda gap: gap.id))

    def test_save_empty_gaps(self, db):
        assert save_schema(db, ()) == 0
        result = load_gaps(db)
        assert not result.is_loaded

    def test_save_roundtrip_with_all_fields(self, db):
        gaps = (
            Gap(
                id="full",
                category="market",
                status=GapStatus.STALE,
                priority=1,
                last_verified="2026-01-01T00:00:00+00:00",
                last_checked="2026-01-02T00:00:00+00:00",
                ttl_days=7,
                blocks=("other",),
                blocked_by=("other",),
                findings="Important data",
            ),
            Gap(id="other", category="tech", blocks=("full",), blocked_by=("full",)),
        )
        save_schema(db, gaps)
        result = load_gaps(db)
        assert result.gaps[0] == gaps[0]
        assert result.gaps[1] == gaps[1]

    def test_upsert_only_changes_supplied_gap(self, db):
        original = (
            Gap(id="a", category="market"),
            Gap(id="b", category="market", findings="keep me"),
        )
        save_schema(db, original)

        changed = save_schema(
            db, (Gap(id="a", category="market", findings="updated"),)
        )

        assert changed == 1
        assert load_gaps(db).gaps == (
            Gap(id="a", category="market", findings="updated"),
            original[1],
        )

    def test_identical_upsert_is_no_op(self, db):
        gap = Gap(id="pricing", category="market")
        save_schema(db, (gap,))

        assert save_schema(db, (gap,)) == 0


class TestMarkChecked:
    _NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_mark_checked_sets_timestamp(self):
        gap = Gap(id="pricing", category="market")
        result = mark_checked(gap, now=self._NOW)
        assert result.last_checked == self._NOW.isoformat()

    def test_mark_checked_preserves_status(self):
        gap = Gap(id="pricing", category="market", status=GapStatus.STALE)
        result = mark_checked(gap, now=self._NOW)
        assert result.status is GapStatus.STALE

    def test_mark_checked_preserves_last_verified(self):
        gap = Gap(
            id="pricing",
            category="market",
            status=GapStatus.VERIFIED,
            last_verified="2026-01-01T00:00:00+00:00",
        )
        result = mark_checked(gap, now=self._NOW)
        assert result.last_verified == "2026-01-01T00:00:00+00:00"

    def test_mark_checked_returns_new_gap(self):
        gap = Gap(id="pricing", category="market")
        result = mark_checked(gap, now=self._NOW)
        assert result is not gap
        assert gap.last_checked is None  # original unchanged


class TestMarkVerified:
    _NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_mark_verified_sets_status(self):
        gap = Gap(id="pricing", category="market")
        result = mark_verified(gap, now=self._NOW)
        assert result.status is GapStatus.VERIFIED

    def test_mark_verified_sets_both_timestamps(self):
        gap = Gap(id="pricing", category="market")
        result = mark_verified(gap, now=self._NOW)
        assert result.last_verified == self._NOW.isoformat()
        assert result.last_checked == self._NOW.isoformat()
        assert result.last_verified == result.last_checked

    def test_mark_verified_returns_new_gap(self):
        gap = Gap(id="pricing", category="market")
        result = mark_verified(gap, now=self._NOW)
        assert result is not gap
        assert gap.status is GapStatus.UNKNOWN  # original unchanged

    def test_timestamps_are_iso_utc(self):
        gap = Gap(id="pricing", category="market")
        result = mark_verified(gap, now=self._NOW)
        # ISO 8601 with UTC offset
        assert result.last_verified == "2026-02-15T12:00:00+00:00"
        assert "+00:00" in result.last_checked
