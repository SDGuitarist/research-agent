"""Tests for the one-time YAML-to-Postgres gap import."""

from datetime import datetime, timezone

import pytest

from research_agent.errors import SchemaError
from research_agent.schema import load_gaps, load_schema_file
from research_agent.staleness import detect_stale
from scripts.migrate_gaps import MigrationError, migrate_gaps


_VERIFIED_AT = "2026-01-15T08:30:00+00:00"


@pytest.fixture
def gap_yaml(tmp_path):
    path = tmp_path / "gaps.yaml"
    path.write_text(
        "gaps:\n"
        "  - id: pricing\n"
        "    category: market\n"
        "    status: verified\n"
        "    priority: 5\n"
        f'    last_verified: "{_VERIFIED_AT}"\n'
        f'    last_checked: "{_VERIFIED_AT}"\n'
        "    ttl_days: 14\n"
        "    blocks: [positioning]\n"
        "  - id: positioning\n"
        "    category: market\n"
        "    blocked_by: [pricing]\n"
    )
    return path


def test_import_is_idempotent_and_preserves_timestamps(db, gap_yaml):
    assert migrate_gaps(db, gap_yaml) == 2
    before = db.execute(
        "SELECT last_verified, last_checked, updated_at FROM gaps WHERE id = 'pricing'"
    ).fetchone()

    assert migrate_gaps(db, gap_yaml) == 0
    after = db.execute(
        "SELECT last_verified, last_checked, updated_at FROM gaps WHERE id = 'pricing'"
    ).fetchone()

    expected = datetime.fromisoformat(_VERIFIED_AT)
    assert before["last_verified"] == expected
    assert before["last_checked"] == expected
    assert after == before


def test_default_pfe_yaml_imports_and_reruns_as_no_op(db):
    first_changed = migrate_gaps(db)
    imported_count = db.execute("SELECT count(*) AS count FROM gaps").fetchone()["count"]

    assert first_changed == imported_count
    assert imported_count > 0
    assert migrate_gaps(db) == 0


def test_import_preserves_staleness_verdict_for_every_gap(db, gap_yaml):
    now = datetime(2026, 2, 15, tzinfo=timezone.utc)
    source_gaps = load_schema_file(gap_yaml).gaps
    before = {g.id for g in detect_stale(source_gaps, now=now)}
    assert before == {"pricing"}  # verified 2026-01-15, ttl 14d → stale at now

    migrate_gaps(db, gap_yaml, now=now)
    imported = load_gaps(db).gaps
    after = {g.id for g in detect_stale(imported, now=now)}

    assert after == before
    assert len(imported) == len(source_gaps)
    by_id = {gap.id: gap for gap in imported}
    assert by_id["pricing"].last_verified == _VERIFIED_AT
    assert by_id["pricing"].ttl_days == 14


def test_row_count_mismatch_raises_explicit_error_and_rolls_back(db, gap_yaml):
    db.execute("INSERT INTO gaps (id, category) VALUES ('extra', 'test')")

    with pytest.raises(MigrationError, match="row-count mismatch"):
        migrate_gaps(db, gap_yaml)

    assert db.execute(
        "SELECT count(*) AS count FROM gaps WHERE id IN ('pricing', 'positioning')"
    ).fetchone()["count"] == 0


def test_cycle_rejected_before_insert(db, tmp_path):
    path = tmp_path / "cycle.yaml"
    path.write_text(
        "gaps:\n"
        "  - id: a\n"
        "    category: test\n"
        "    blocks: [b]\n"
        "  - id: b\n"
        "    category: test\n"
        "    blocks: [a]\n"
    )

    with pytest.raises(SchemaError, match="dependency cycles"):
        migrate_gaps(db, path)

    assert db.execute("SELECT count(*) AS count FROM gaps").fetchone()["count"] == 0
