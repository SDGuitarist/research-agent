"""Tests for main.py CLI functions."""

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from main import (
    get_auto_save_path,
    list_reports,
    sanitize_filename,
    show_costs,
    REPORTS_DIR,
    _OLD_FORMAT,
    _NEW_FORMAT,
)
from research_agent.modes import ResearchMode


class TestSanitizeFilename:
    """Tests for sanitize_filename()."""

    def test_lowercases_and_replaces_spaces(self):
        assert sanitize_filename("Hello World") == "hello_world"

    def test_removes_special_characters(self):
        assert sanitize_filename("what's up?") == "whats_up"

    def test_collapses_multiple_underscores(self):
        assert sanitize_filename("a   b   c") == "a_b_c"

    def test_strips_leading_trailing_underscores(self):
        assert sanitize_filename("  hello  ") == "hello"

    def test_truncates_at_word_boundary(self):
        long_query = "a" * 30 + "_" + "b" * 30
        result = sanitize_filename(long_query, max_length=50)
        assert len(result) <= 50
        assert not result.endswith("_")

    def test_returns_research_for_empty_input(self):
        assert sanitize_filename("???") == "research"

    def test_returns_research_for_empty_string(self):
        assert sanitize_filename("") == "research"


class TestGetAutoSavePath:
    """Tests for get_auto_save_path()."""

    def test_returns_path_in_reports_directory(self):
        path = get_auto_save_path("test query")
        assert path.parent == REPORTS_DIR

    def test_filename_is_query_first(self):
        path = get_auto_save_path("GraphQL vs REST")
        name = path.name
        # Query slug should come before the timestamp
        assert name.startswith("graphql_vs_rest_")
        assert name.endswith(".md")

    def test_filename_contains_timestamp_with_microseconds(self):
        path = get_auto_save_path("test")
        name = path.stem  # without .md
        # Should contain a date pattern after the query
        assert re.search(r"\d{4}-\d{2}-\d{2}_\d{6,}", name)

    def test_filename_ends_with_md(self):
        path = get_auto_save_path("anything")
        assert path.suffix == ".md"


class TestFilenameRegexPatterns:
    """Tests for the filename regex patterns used by --list."""

    def test_old_format_matches_timestamp_first(self):
        match = _OLD_FORMAT.match("2026-02-03_183703056652_graphql_vs_rest.md")
        assert match is not None
        assert match.group(1) == "2026-02-03"
        assert match.group(2) == "graphql_vs_rest"

    def test_new_format_matches_query_first(self):
        match = _NEW_FORMAT.match("graphql_vs_rest_2026-02-03_183703056652.md")
        assert match is not None
        assert match.group(1) == "graphql_vs_rest"
        assert match.group(2) == "2026-02-03"

    def test_old_format_no_match_on_non_standard(self):
        assert _OLD_FORMAT.match("codebase_review.md") is None

    def test_new_format_no_match_on_non_standard(self):
        assert _NEW_FORMAT.match("codebase_review.md") is None


class TestListReports:
    """Tests for list_reports()."""

    def test_missing_directory(self, tmp_path, capsys):
        with patch("main.REPORTS_DIR", tmp_path / "nonexistent"):
            list_reports()
        assert "No reports directory found" in capsys.readouterr().out

    def test_empty_directory(self, tmp_path, capsys):
        reports = tmp_path / "reports"
        reports.mkdir()
        with patch("main.REPORTS_DIR", reports):
            list_reports()
        assert "No saved reports" in capsys.readouterr().out

    def test_lists_old_format_reports(self, tmp_path, capsys):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-02-03_183703_graphql_vs_rest.md").write_text("test")
        with patch("main.REPORTS_DIR", reports):
            list_reports()
        output = capsys.readouterr().out
        assert "Saved reports (1):" in output
        assert "2026-02-03" in output
        assert "graphql_vs_rest" in output

    def test_lists_new_format_reports(self, tmp_path, capsys):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "graphql_vs_rest_2026-02-03_183703056652.md").write_text("test")
        with patch("main.REPORTS_DIR", reports):
            list_reports()
        output = capsys.readouterr().out
        assert "Saved reports (1):" in output
        assert "2026-02-03" in output
        assert "graphql_vs_rest" in output

    def test_non_standard_files_listed_separately(self, tmp_path, capsys):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "codebase_review.md").write_text("test")
        (reports / "2026-02-03_183703_query.md").write_text("test")
        with patch("main.REPORTS_DIR", reports):
            list_reports()
        output = capsys.readouterr().out
        assert "Saved reports (2):" in output
        assert "non-standard names" in output
        assert "codebase_review.md" in output

    def test_ignores_non_md_files(self, tmp_path, capsys):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / ".DS_Store").write_text("junk")
        with patch("main.REPORTS_DIR", reports):
            list_reports()
        assert "No saved reports" in capsys.readouterr().out


class TestShowCosts:
    """Tests for show_costs()."""

    def test_prints_all_three_modes(self, capsys):
        show_costs()
        output = capsys.readouterr().out
        assert "quick" in output
        assert "standard" in output
        assert "deep" in output

    def test_marks_standard_as_default(self, capsys):
        show_costs()
        output = capsys.readouterr().out
        assert "[default]" in output

    def test_includes_cost_estimates(self, capsys):
        show_costs()
        output = capsys.readouterr().out
        assert "~$0.12" in output
        assert "~$0.20" in output
        assert "~$0.50" in output

    def test_includes_source_counts(self, capsys):
        show_costs()
        output = capsys.readouterr().out
        # Each mode's max_sources should appear
        quick = ResearchMode.quick()
        standard = ResearchMode.standard()
        deep = ResearchMode.deep()
        assert str(quick.max_sources) in output
        assert str(standard.max_sources) in output
        assert str(deep.max_sources) in output


class TestResearchModeCostEstimate:
    """Tests for cost_estimate field on ResearchMode."""

    def test_quick_has_cost_estimate(self):
        assert ResearchMode.quick().cost_estimate == "~$0.12"

    def test_standard_has_cost_estimate(self):
        assert ResearchMode.standard().cost_estimate == "~$0.20"

    def test_deep_has_cost_estimate(self):
        assert ResearchMode.deep().cost_estimate == "~$0.50"
