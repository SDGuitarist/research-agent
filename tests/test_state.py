"""Tests for state persistence — state writer + timestamp management."""

from datetime import datetime, timezone
from unittest.mock import patch

from research_agent.schema import Gap, GapStatus, load_schema
from research_agent.state import (
    _gap_to_dict,
    mark_checked,
    mark_verified,
    save_schema,
)


class TestGapToDict:
    def test_gap_to_dict_converts_enum(self):
        gap = Gap(
            id="pricing",
            category="market",
            status=GapStatus.VERIFIED,
            last_verified="2026-01-01T00:00:00+00:00",
        )
        result = _gap_to_dict(gap)
        assert result["status"] == "verified"

    def test_gap_to_dict_omits_defaults(self):
        gap = Gap(id="pricing", category="market")
        result = _gap_to_dict(gap)
        assert "findings" not in result
        assert "blocks" not in result
        assert "blocked_by" not in result
        assert "status" not in result  # unknown is default
        assert "priority" not in result  # 3 is default
        assert "last_verified" not in result
        assert "last_checked" not in result
        assert "ttl_days" not in result

    def test_gap_to_dict_converts_tuples(self):
        gap = Gap(
            id="pricing",
            category="market",
            blocks=("competitor", "revenue"),
        )
        result = _gap_to_dict(gap)
        assert result["blocks"] == ["competitor", "revenue"]
        assert isinstance(result["blocks"], list)

    def test_gap_to_dict_includes_required_fields(self):
        gap = Gap(id="pricing", category="market")
        result = _gap_to_dict(gap)
        assert result["id"] == "pricing"
        assert result["category"] == "market"

    def test_gap_to_dict_includes_non_default_fields(self):
        gap = Gap(
            id="pricing",
            category="market",
            priority=5,
            ttl_days=14,
            findings="Some findings",
        )
        result = _gap_to_dict(gap)
        assert result["priority"] == 5
        assert result["ttl_days"] == 14
        assert result["findings"] == "Some findings"


class TestSaveSchema:
    def test_save_load_roundtrip(self, tmp_path):
        path = tmp_path / "schema.yaml"
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
        save_schema(path, gaps)
        result = load_schema(path)
        assert result.is_loaded
        assert len(result.gaps) == 2
        assert result.gaps[0] == gaps[0]
        assert result.gaps[1] == gaps[1]

    def test_save_uses_atomic_write(self, tmp_path):
        path = tmp_path / "schema.yaml"
        gaps = (Gap(id="pricing", category="market"),)
        with patch("research_agent.state.atomic_write") as mock_write:
            save_schema(path, gaps)
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            assert call_args[0][0] == path

    def test_save_empty_gaps(self, tmp_path):
        path = tmp_path / "schema.yaml"
        save_schema(path, ())
        result = load_schema(path)
        assert not result.is_loaded

    def test_save_roundtrip_with_all_fields(self, tmp_path):
        path = tmp_path / "schema.yaml"
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
        save_schema(path, gaps)
        result = load_schema(path)
        assert result.gaps[0] == gaps[0]
        assert result.gaps[1] == gaps[1]


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
