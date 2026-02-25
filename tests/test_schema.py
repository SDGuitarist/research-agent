"""Tests for Gap data model and YAML parser."""

import dataclasses

import pytest

from research_agent.errors import SchemaError
from research_agent.schema import (
    Gap,
    GapStatus,
    SchemaResult,
    load_schema,
)


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

    def test_gap_blocks_is_tuple(self):
        gap = Gap(id="x", category="y", blocks=("a", "b"))
        assert isinstance(gap.blocks, tuple)

    def test_gap_equality(self):
        gap1 = Gap(id="x", category="y", priority=5)
        gap2 = Gap(id="x", category="y", priority=5)
        assert gap1 == gap2


class TestLoadSchema:
    def test_parse_valid_schema(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text(
            "gaps:\n"
            '  - id: "pricing"\n'
            '    category: "competitor-a"\n'
            '    status: "unknown"\n'
            "    priority: 4\n"
            "    ttl_days: 14\n"
            '    blocks: ["market-position"]\n'
            '  - id: "team"\n'
            '    category: "competitor-a"\n'
            '    status: "verified"\n'
            "    priority: 2\n"
            '    last_verified: "2026-01-15"\n'
            "    ttl_days: 90\n"
        )
        result = load_schema(schema_file)
        assert result.is_loaded
        assert len(result.gaps) == 2
        assert result.gaps[0].id == "pricing"
        assert result.gaps[0].priority == 4
        assert result.gaps[0].blocks == ("market-position",)
        assert result.gaps[1].id == "team"
        assert result.gaps[1].status is GapStatus.VERIFIED
        assert result.gaps[1].last_verified == "2026-01-15"

    def test_parse_missing_file(self, tmp_path):
        result = load_schema(tmp_path / "nonexistent.yaml")
        assert result.is_not_configured
        assert result.source == ""
        assert result.gaps == ()

    def test_parse_empty_file(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("")
        result = load_schema(schema_file)
        assert result.is_empty
        assert result.source == str(schema_file)
        assert result.gaps == ()

    def test_parse_empty_gaps_list(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("gaps: []\n")
        result = load_schema(schema_file)
        assert result.is_empty
        assert result.source == str(schema_file)

    def test_parse_malformed_yaml(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("gaps:\n  - id: [unterminated\n")
        with pytest.raises(SchemaError, match="Invalid YAML"):
            load_schema(schema_file)

    def test_parse_wrong_structure(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text('gaps: "not a list"\n')
        with pytest.raises(SchemaError, match="must be a list"):
            load_schema(schema_file)

    def test_parse_unknown_status(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text(
            "gaps:\n"
            '  - id: "x"\n'
            '    category: "y"\n'
            '    status: "foobar"\n'
        )
        with pytest.raises(SchemaError, match="unknown status 'foobar'"):
            load_schema(schema_file)

    def test_parse_missing_required_id(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("gaps:\n  - category: 'y'\n")
        with pytest.raises(SchemaError, match="missing required field 'id'"):
            load_schema(schema_file)

    def test_parse_missing_required_category(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("gaps:\n  - id: 'x'\n")
        with pytest.raises(SchemaError, match="missing required field 'category'"):
            load_schema(schema_file)

    def test_parse_bool_rejected_as_priority(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text(
            "gaps:\n"
            '  - id: "x"\n'
            '    category: "y"\n'
            "    priority: true\n"
        )
        with pytest.raises(SchemaError, match="non-integer priority"):
            load_schema(schema_file)

    def test_parse_defaults_applied(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text(
            "gaps:\n"
            '  - id: "minimal"\n'
            '    category: "test"\n'
        )
        result = load_schema(schema_file)
        gap = result.gaps[0]
        assert gap.status is GapStatus.UNKNOWN
        assert gap.priority == 3
        assert gap.blocks == ()
        assert gap.blocked_by == ()
        assert gap.last_verified is None
        assert gap.ttl_days is None
        assert gap.findings == ""

    def test_schema_result_bool_true_when_loaded(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text(
            "gaps:\n"
            '  - id: "x"\n'
            '    category: "y"\n'
        )
        result = load_schema(schema_file)
        assert bool(result) is True

    def test_schema_result_bool_false_when_empty(self, tmp_path):
        schema_file = tmp_path / "gaps.yaml"
        schema_file.write_text("gaps: []\n")
        result = load_schema(schema_file)
        assert bool(result) is False
