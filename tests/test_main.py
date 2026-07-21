"""Tests for CLI functions in research_agent.cli."""

import re
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_agent.cli import (
    list_reports,
    main,
    show_costs,
)
from research_agent.report_store import (
    REPORTS_DIR,
    _NEW_FORMAT,
    _OLD_FORMAT,
    get_auto_save_path,
    sanitize_filename,
    save_report,
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

    def test_rejects_symlinked_reports_root(self, tmp_path):
        external = tmp_path / "external"
        external.mkdir()
        reports_link = tmp_path / "reports"
        reports_link.symlink_to(external, target_is_directory=True)

        with patch("research_agent.report_store.REPORTS_DIR", reports_link):
            with pytest.raises(OSError, match="literal repo-local reports/ directory"):
                get_auto_save_path("anything")


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
    """Tests for list_reports() against the DB."""

    def _run(self, db):
        with patch("research_agent.cli.open_pool") as mock_pool:
            mock_pool.return_value.connection.return_value = nullcontext(db)
            list_reports()

    def test_empty_db(self, db, capsys):
        self._run(db)
        assert "No saved reports" in capsys.readouterr().out

    def test_lists_reports_from_db(self, db, capsys):
        save_report(db, query="graphql vs rest", mode="standard", content="# R")
        self._run(db)
        output = capsys.readouterr().out
        assert "Saved reports (1):" in output
        assert "graphql vs rest" in output
        assert re.search(r"graphql_vs_rest-[0-9a-f]{8}", output)

    def test_lists_two_rows_for_repeated_query(self, db, capsys):
        save_report(db, query="same query", mode="standard", content="a")
        save_report(db, query="same query", mode="standard", content="b")
        self._run(db)
        output = capsys.readouterr().out
        assert "Saved reports (2):" in output
        keys = re.findall(r"same_query-[0-9a-f]{8}", output)
        assert len(set(keys)) == 2


class TestCliAutoSave:
    """CLI research runs persist reports to Postgres, never files."""

    def _run_cli(self, db, tmp_path, monkeypatch, query="pacific flow competitors"):
        monkeypatch.chdir(tmp_path)  # stray file writes land in tmp, not the repo
        mock_agent = MagicMock()
        mock_agent.research.return_value = "# Report\n\nBody."
        mock_agent.last_critique = None
        mock_agent.iteration_status = "skipped"
        mock_agent.last_gate_decision = "full_report"
        mock_agent.last_source_count = 5
        with patch("research_agent.cli.ResearchAgent", return_value=mock_agent), \
             patch("research_agent.cli.open_pool") as mock_pool, \
             patch("sys.argv", ["main.py", "--standard", query]):
            mock_pool.return_value.connection.return_value = nullcontext(db)
            main()

    def test_standard_run_writes_one_db_row_and_no_file(
        self, db, tmp_path, monkeypatch, capsys
    ):
        self._run_cli(db, tmp_path, monkeypatch)
        rows = db.execute(
            "SELECT report_key, query, mode, content, gate_decision, sources_used "
            "FROM reports"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["query"] == "pacific flow competitors"
        assert rows[0]["mode"] == "standard"
        assert rows[0]["content"] == "# Report\n\nBody."
        assert rows[0]["gate_decision"] == "full_report"
        assert rows[0]["sources_used"] == 5
        assert not (tmp_path / "reports").exists()
        assert rows[0]["report_key"] in capsys.readouterr().out

    def test_same_query_twice_writes_two_rows_distinct_keys(
        self, db, tmp_path, monkeypatch
    ):
        self._run_cli(db, tmp_path, monkeypatch)
        self._run_cli(db, tmp_path, monkeypatch)
        rows = db.execute("SELECT report_key FROM reports").fetchall()
        assert len(rows) == 2
        assert rows[0]["report_key"] != rows[1]["report_key"]

    def test_explicit_output_flag_still_writes_a_file(
        self, db, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        out_file = tmp_path / "out.md"
        mock_agent = MagicMock()
        mock_agent.research.return_value = "# Report\n\nBody."
        mock_agent.last_critique = None
        mock_agent.iteration_status = "skipped"
        mock_agent.last_gate_decision = "full_report"
        mock_agent.last_source_count = 5
        with patch("research_agent.cli.ResearchAgent", return_value=mock_agent), \
             patch("research_agent.cli.open_pool") as mock_pool, \
             patch("sys.argv", ["main.py", "--quick", "q query words", "-o", str(out_file)]):
            mock_pool.return_value.connection.return_value = nullcontext(db)
            main()
        assert out_file.read_text() == "# Report\n\nBody."
        assert db.execute("SELECT count(*) AS n FROM reports").fetchone()["n"] == 0


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
        assert "~$0.45" in output
        assert "~$0.95" in output

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
        assert ResearchMode.standard().cost_estimate == "~$0.45"

    def test_deep_has_cost_estimate(self):
        assert ResearchMode.deep().cost_estimate == "~$0.95"


class TestCliMain:
    """Tests for CLI command handling."""

    def test_list_contexts_rejects_symlinked_contexts_root(self, tmp_path, capsys):
        external = tmp_path / "external"
        external.mkdir()
        (external / "outside.md").write_text("# Outside")
        contexts_link = tmp_path / "contexts"
        contexts_link.symlink_to(external, target_is_directory=True)

        with patch("research_agent.cli.CONTEXTS_DIR", contexts_link), \
             patch("research_agent.context.CONTEXTS_DIR", contexts_link), \
             patch("sys.argv", ["main.py", "--list-contexts"]):
            with pytest.raises(SystemExit) as exc:
                main()

        assert exc.value.code == 0
        assert "No context files found in contexts/." in capsys.readouterr().out
