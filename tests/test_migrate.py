"""Tests for the migration runner's file discovery / ordering (no DB needed)."""

from research_agent.migrate import migration_files, pending_migrations


def test_migration_files_sorted_by_prefix(tmp_path):
    for name in ("003_c.sql", "001_a.sql", "002_b.sql", "notes.txt", "01_bad.sql"):
        (tmp_path / name).write_text("SELECT 1;")
    files = migration_files(tmp_path)
    # Only NNN_*.sql, in numeric (== lexical, zero-padded) order.
    assert [f.name for f in files] == ["001_a.sql", "002_b.sql", "003_c.sql"]


def test_pending_excludes_applied(tmp_path):
    for name in ("001_a.sql", "002_b.sql"):
        (tmp_path / name).write_text("SELECT 1;")
    files = migration_files(tmp_path)
    pending = pending_migrations(files, applied={"001_a.sql"})
    assert [f.name for f in pending] == ["002_b.sql"]


def test_pending_empty_when_all_applied(tmp_path):
    (tmp_path / "001_a.sql").write_text("SELECT 1;")
    files = migration_files(tmp_path)
    assert pending_migrations(files, applied={"001_a.sql"}) == []
