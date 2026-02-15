"""Tests for state persistence — state writer (Deliverable 1)."""

from unittest.mock import patch

import pytest

from research_agent.errors import SchemaError, StateError
from research_agent.schema import Gap, GapStatus, load_schema, validate_gaps
from research_agent.state import _gap_to_dict, save_schema, update_gap


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
        assert "metadata" not in result

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
                metadata={"source": "web"},
            ),
            Gap(id="other", category="tech", blocks=("full",), blocked_by=("full",)),
        )
        save_schema(path, gaps)
        result = load_schema(path)
        assert result.gaps[0] == gaps[0]
        assert result.gaps[1] == gaps[1]


class TestUpdateGap:
    def _write_schema(self, path, gaps):
        """Helper: write gaps to disk for update_gap tests."""
        save_schema(path, gaps)

    def test_update_gap_changes_field(self, tmp_path):
        path = tmp_path / "schema.yaml"
        gaps = (
            Gap(id="pricing", category="market"),
            Gap(id="competitor", category="market"),
        )
        self._write_schema(path, gaps)
        updated = update_gap(path, "pricing", priority=5)
        assert updated.priority == 5
        assert updated.id == "pricing"

    def test_update_gap_unknown_id_raises(self, tmp_path):
        path = tmp_path / "schema.yaml"
        self._write_schema(path, (Gap(id="pricing", category="market"),))
        with pytest.raises(StateError, match="nonexistent"):
            update_gap(path, "nonexistent", priority=1)

    def test_update_gap_invalid_state_raises(self, tmp_path):
        path = tmp_path / "schema.yaml"
        self._write_schema(path, (Gap(id="pricing", category="market"),))
        with pytest.raises(SchemaError):
            update_gap(path, "pricing", status=GapStatus.VERIFIED)
            # verified without last_verified → validation fails

    def test_update_gap_preserves_others(self, tmp_path):
        path = tmp_path / "schema.yaml"
        original_competitor = Gap(id="competitor", category="tech", priority=2)
        gaps = (
            Gap(id="pricing", category="market"),
            original_competitor,
        )
        self._write_schema(path, gaps)
        update_gap(path, "pricing", priority=5)
        result = load_schema(path)
        assert result.gaps[1] == original_competitor

    def test_update_gap_persists_to_disk(self, tmp_path):
        path = tmp_path / "schema.yaml"
        self._write_schema(path, (Gap(id="pricing", category="market"),))
        update_gap(path, "pricing", priority=5)
        result = load_schema(path)
        assert result.gaps[0].priority == 5
