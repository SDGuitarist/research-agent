"""Tests for report_store functions not covered by test_main.py.

test_main.py already covers sanitize_filename (7 tests) and
get_auto_save_path (5 tests). This file tests only the remaining
functions: _resolves_within_reports_root and get_reports.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from research_agent.report_store import (
    _resolves_within_reports_root,
    get_reports,
    REPORTS_DIR,
)
from research_agent.results import ReportInfo


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


class TestGetReports:
    """Tests for get_reports()."""

    def test_nonexistent_directory_returns_empty(self, tmp_path):
        """Non-existent reports directory should return empty list."""
        fake_dir = tmp_path / "reports"
        with patch("research_agent.report_store.REPORTS_DIR", fake_dir):
            assert get_reports() == []

    def test_empty_directory_returns_empty(self, tmp_path):
        """Empty reports directory should return empty list."""
        reports = tmp_path / "reports"
        reports.mkdir()
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            assert get_reports() == []

    def test_new_format_files_sorted_newest_first(self, tmp_path):
        """Files matching new format should be parsed and sorted newest-first."""
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "pizza_2026-01-01_120000000000.md").write_text("old")
        (reports / "tacos_2026-06-15_120000000000.md").write_text("new")
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            result = get_reports()
            assert len(result) == 2
            assert result[0].date == "2026-06-15"
            assert result[1].date == "2026-01-01"
            assert result[0].query_name == "tacos"

    def test_old_format_files_parsed(self, tmp_path):
        """Files matching old format (timestamp first) should be parsed."""
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-03-01_183703056652_my_query.md").write_text("content")
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            result = get_reports()
            assert len(result) == 1
            assert result[0].date == "2026-03-01"
            assert result[0].query_name == "my_query"

    def test_nonstandard_filenames_fallback(self, tmp_path):
        """Files not matching either format should use filename as query_name."""
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "random_notes.md").write_text("content")
        with patch("research_agent.report_store.REPORTS_DIR", reports), \
             patch("research_agent.report_store.Path.cwd", return_value=tmp_path):
            result = get_reports()
            assert len(result) == 1
            assert result[0].date == ""
            assert result[0].query_name == "random_notes.md"
