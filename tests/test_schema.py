"""Tests for Gap data model."""

import dataclasses

import pytest

from research_agent.schema import Gap, GapStatus


class TestGapStatus:
    def test_gap_status_has_four_values(self):
        values = list(GapStatus)
        assert len(values) == 4
        assert GapStatus.UNKNOWN in values
        assert GapStatus.VERIFIED in values
        assert GapStatus.STALE in values
        assert GapStatus.BLOCKED in values


class TestGap:
    def test_gap_minimal_construction(self):
        gap = Gap(id="x", category="y")
        assert gap.id == "x"
        assert gap.category == "y"

    def test_gap_is_frozen(self):
        gap = Gap(id="x", category="y")
        with pytest.raises(dataclasses.FrozenInstanceError):
            gap.status = GapStatus.STALE  # type: ignore[misc]

    def test_gap_defaults(self):
        gap = Gap(id="x", category="y")
        assert gap.status is GapStatus.UNKNOWN
        assert gap.priority == 3
        assert gap.blocks == ()
        assert gap.blocked_by == ()
        assert gap.last_verified is None
        assert gap.last_checked is None
        assert gap.ttl_days is None
        assert gap.findings == ""
        assert gap.metadata == {}

    def test_gap_full_construction(self):
        gap = Gap(
            id="pricing",
            category="competitor-a",
            status=GapStatus.VERIFIED,
            priority=5,
            last_verified="2026-01-15",
            last_checked="2026-01-20",
            ttl_days=14,
            blocks=("market-position",),
            blocked_by=("team",),
            findings="Found pricing details",
            metadata={"source": "website"},
        )
        assert gap.id == "pricing"
        assert gap.category == "competitor-a"
        assert gap.status is GapStatus.VERIFIED
        assert gap.priority == 5
        assert gap.last_verified == "2026-01-15"
        assert gap.last_checked == "2026-01-20"
        assert gap.ttl_days == 14
        assert gap.blocks == ("market-position",)
        assert gap.blocked_by == ("team",)
        assert gap.findings == "Found pricing details"
        assert gap.metadata == {"source": "website"}

    def test_gap_blocks_is_tuple(self):
        gap = Gap(id="x", category="y", blocks=("a", "b"))
        assert isinstance(gap.blocks, tuple)

    def test_gap_equality(self):
        gap1 = Gap(id="x", category="y", priority=5)
        gap2 = Gap(id="x", category="y", priority=5)
        assert gap1 == gap2
