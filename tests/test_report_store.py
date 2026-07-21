"""Tests for report_store functions not covered by test_main.py.

test_main.py already covers sanitize_filename (7 tests) and
get_auto_save_path (5 tests). This file tests the remaining functions:
_resolves_within_reports_root and the DB-backed report stores against
real Postgres via the `db` fixture.
"""

import re
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent.errors import StateError
from research_agent.report_store import (
    _resolves_within_reports_root,
    get_report,
    get_reports,
    save_report,
)


class TestResolvesWithinReportsRoot:
    """Tests for _resolves_within_reports_root()."""

    def test_path_inside_reports_returns_true(self, tmp_path):
        """A path inside reports/ should return True."""
        reports = tmp_path / "reports"
        reports.mkdir()
        target = reports / "test.md"
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert _resolves_within_reports_root(target) is True

    def test_traversal_returns_false(self, tmp_path):
        """../traversal outside reports/ should return False."""
        reports = tmp_path / "reports"
        reports.mkdir()
        target = reports / ".." / "etc" / "passwd"
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert _resolves_within_reports_root(target) is False

    def test_absolute_path_outside_returns_false(self, tmp_path):
        """An absolute path outside reports/ should return False."""
        reports = tmp_path / "reports"
        reports.mkdir()
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert _resolves_within_reports_root(Path("/tmp/evil.md")) is False

    def test_symlink_outside_returns_false(self, tmp_path):
        """A symlink pointing outside reports/ should return False."""
        reports = tmp_path / "reports"
        reports.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        secret = outside / "secret.md"
        secret.touch()
        link = reports / "link.md"
        link.symlink_to(secret)
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert _resolves_within_reports_root(link) is False

    def test_nonexistent_path_inside_returns_true(self, tmp_path):
        """A non-existent path inside reports/ should return True (strict=False)."""
        reports = tmp_path / "reports"
        reports.mkdir()
        target = reports / "does_not_exist.md"
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert _resolves_within_reports_root(target) is True


class TestSaveReport:
    """Tests for save_report() against real Postgres."""

    def test_persists_row_and_returns_key(self, db):
        key = save_report(
            db, query="python async best practices", mode="standard",
            content="# Report\n\nBody.", gate_decision="full_report",
            sources_used=5,
        )
        row = db.execute(
            "SELECT * FROM reports WHERE report_key = %s", (key,)
        ).fetchone()
        assert row["query"] == "python async best practices"
        assert row["mode"] == "standard"
        assert row["content"] == "# Report\n\nBody."
        assert row["gate_decision"] == "full_report"
        assert row["sources_used"] == 5
        assert row["job_id"] is None
        assert row["created_at"] is not None

    def test_key_format_is_slug_dash_uuid8(self, db):
        key = save_report(db, query="GraphQL vs REST?", mode="quick", content="x")
        assert re.fullmatch(r"graphql_vs_rest-[0-9a-f]{8}", key)
        # The MCP path-safety character rule carries over to keys.
        assert re.fullmatch(r"[a-zA-Z0-9_\-]+", key)

    def test_same_query_twice_gives_two_rows_distinct_keys(self, db):
        key1 = save_report(db, query="same query", mode="standard", content="a")
        key2 = save_report(db, query="same query", mode="standard", content="b")
        assert key1 != key2
        count = db.execute(
            "SELECT count(*) AS n FROM reports WHERE query = 'same query'"
        ).fetchone()["n"]
        assert count == 2

    @staticmethod
    def _uuids_sharing_prefix(count):
        """Distinct uuids whose first 8 hex chars (the key suffix) all match."""
        prefix = uuid.uuid4().hex[:8]
        return [uuid.UUID(prefix + f"{i:024x}") for i in range(count)]

    def test_key_collision_regenerates_and_retries(self, db):
        """A report_key UniqueViolation gets a fresh uuid and retries."""
        u1, u2 = self._uuids_sharing_prefix(2)
        other = uuid.uuid4()
        with patch("research_agent.report_store.uuid.uuid4",
                   side_effect=[u1, u2, other]):
            key1 = save_report(db, query="collide", mode="quick", content="a")
            key2 = save_report(db, query="collide", mode="quick", content="b")
        assert key1 == f"collide-{u1.hex[:8]}"
        assert key2 == f"collide-{other.hex[:8]}"

    def test_exhausted_collision_retries_raise_state_error(self, db):
        colliders = self._uuids_sharing_prefix(4)
        with patch("research_agent.report_store.uuid.uuid4",
                   side_effect=colliders):
            save_report(db, query="collide", mode="quick", content="a")
            with pytest.raises(StateError, match="collided"):
                save_report(db, query="collide", mode="quick", content="b")

    def test_job_id_conflict_is_not_retried(self, db):
        """UNIQUE(job_id) breach raises StateError instead of retrying."""
        job_id = db.execute(
            "INSERT INTO jobs (query, mode) VALUES ('q', 'quick') RETURNING id"
        ).fetchone()["id"]
        save_report(db, query="q", mode="quick", content="a", job_id=job_id)
        with pytest.raises(StateError, match="Failed to save report"):
            save_report(db, query="q", mode="quick", content="b", job_id=job_id)


class TestGetReportsDb:
    """Tests for the DB-backed get_reports()."""

    def test_empty_table_returns_empty(self, db):
        assert get_reports(db) == []

    def test_maps_columns_to_report_info(self, db):
        key = save_report(db, query="my query", mode="standard", content="x")
        result = get_reports(db)
        assert len(result) == 1
        assert result[0].filename == key
        assert result[0].query_name == "my query"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result[0].date)

    def test_sorted_newest_first(self, db):
        old_key = save_report(db, query="old", mode="quick", content="x")
        new_key = save_report(db, query="new", mode="quick", content="y")
        db.execute(
            "UPDATE reports SET created_at = created_at - interval '2 days' "
            "WHERE report_key = %s", (old_key,)
        )
        result = get_reports(db)
        assert [r.filename for r in result] == [new_key, old_key]


class TestGetReportDb:
    def test_returns_verbatim_content(self, db):
        key = save_report(
            db, query="stored report", mode="standard",
            content="# Report\n\n<script>kept verbatim</script>",
        )
        assert get_report(db, key) == "# Report\n\n<script>kept verbatim</script>"

    def test_unknown_key_returns_none(self, db):
        assert get_report(db, "missing-deadbeef") is None
