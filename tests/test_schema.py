"""Tests for Gap data model and YAML parser."""

import dataclasses

import pytest

from research_agent.errors import SchemaError
from research_agent.schema import (
    Gap,
    GapStatus,
    SchemaResult,
    detect_cycles,
    load_schema,
    validate_gaps,
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


class TestValidateGaps:
    def test_validate_valid_gaps(self):
        gaps = (
            Gap(id="a", category="cat", priority=3),
            Gap(id="b", category="cat", priority=4, blocked_by=("a",)),
        )
        assert validate_gaps(gaps) == []

    def test_validate_duplicate_ids(self):
        gaps = (
            Gap(id="a", category="cat"),
            Gap(id="a", category="other"),
        )
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "Duplicate gap ID: 'a'" in errors[0]

    def test_validate_verified_needs_timestamp(self):
        gaps = (Gap(id="a", category="cat", status=GapStatus.VERIFIED),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "verified" in errors[0]
        assert "last_verified is None" in errors[0]

    def test_validate_unknown_has_no_timestamp(self):
        gaps = (
            Gap(
                id="a",
                category="cat",
                status=GapStatus.UNKNOWN,
                last_verified="2026-01-01",
            ),
        )
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "unknown" in errors[0]
        assert "last_verified is set" in errors[0]

    def test_validate_reference_integrity(self):
        gaps = (Gap(id="a", category="cat", blocked_by=("nonexistent",)),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_validate_self_reference_blocks(self):
        gaps = (Gap(id="a", category="cat", blocks=("a",)),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "references itself" in errors[0]
        assert "blocks" in errors[0]

    def test_validate_self_reference_blocked_by(self):
        gaps = (Gap(id="a", category="cat", blocked_by=("a",)),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "references itself" in errors[0]
        assert "blocked_by" in errors[0]

    def test_validate_priority_too_low(self):
        gaps = (Gap(id="a", category="cat", priority=0),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "priority" in errors[0]
        assert "0" in errors[0]

    def test_validate_priority_too_high(self):
        gaps = (Gap(id="a", category="cat", priority=6),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "priority" in errors[0]
        assert "6" in errors[0]

    def test_validate_ttl_days_invalid(self):
        gaps = (Gap(id="a", category="cat", ttl_days=0),)
        errors = validate_gaps(gaps)
        assert len(errors) == 1
        assert "ttl_days" in errors[0]

    def test_validate_reports_all_errors(self):
        gaps = (
            Gap(id="a", category="cat", priority=0, ttl_days=0),
            Gap(id="a", category="cat", status=GapStatus.VERIFIED),
        )
        errors = validate_gaps(gaps)
        assert len(errors) >= 3

    def test_validate_empty_gaps(self):
        assert validate_gaps(()) == []


class TestDetectCycles:
    def test_no_cycles_empty(self):
        assert detect_cycles(()) == []

    def test_no_cycles_linear(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b",)),
            Gap(id="b", category="cat", blocks=("c",)),
            Gap(id="c", category="cat", blocks=("d",)),
            Gap(id="d", category="cat"),
        )
        assert detect_cycles(gaps) == []

    def test_no_cycles_diamond(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b", "c")),
            Gap(id="b", category="cat", blocks=("d",)),
            Gap(id="c", category="cat", blocks=("d",)),
            Gap(id="d", category="cat"),
        )
        assert detect_cycles(gaps) == []

    def test_simple_cycle(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b",)),
            Gap(id="b", category="cat", blocks=("a",)),
        )
        cycles = detect_cycles(gaps)
        assert len(cycles) == 1
        assert "a" in cycles[0]
        assert "b" in cycles[0]

    def test_deep_cycle(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b",)),
            Gap(id="b", category="cat", blocks=("c",)),
            Gap(id="c", category="cat", blocks=("a",)),
        )
        cycles = detect_cycles(gaps)
        assert len(cycles) == 1
        assert cycles[0] == ("a", "b", "c", "a")

    def test_multiple_cycles(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b",)),
            Gap(id="b", category="cat", blocks=("a",)),
            Gap(id="c", category="cat", blocks=("d",)),
            Gap(id="d", category="cat", blocks=("c",)),
        )
        cycles = detect_cycles(gaps)
        assert len(cycles) == 2

    def test_no_dependencies(self):
        gaps = (
            Gap(id="a", category="cat"),
            Gap(id="b", category="cat"),
            Gap(id="c", category="cat"),
        )
        assert detect_cycles(gaps) == []

    def test_cycle_includes_path(self):
        gaps = (
            Gap(id="a", category="cat", blocks=("b",)),
            Gap(id="b", category="cat", blocks=("c",)),
            Gap(id="c", category="cat", blocks=("a",)),
        )
        cycles = detect_cycles(gaps)
        cycle = cycles[0]
        # Cycle should start and end with same node
        assert cycle[0] == cycle[-1]
        # All nodes in the cycle should be present
        assert set(cycle[:-1]) == {"a", "b", "c"}
