"""Tests for the MCP server: all 5 tools, transports, and error paths."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from research_agent.mcp_server import mcp, _validate_report_filename


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """In-memory MCP client — no subprocess, no network."""
    async with Client(mcp) as c:
        yield c


# Shared mock env (both API keys present)
ENV_BOTH = {"ANTHROPIC_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}


# ---------------------------------------------------------------------------
# run_research — happy path
# ---------------------------------------------------------------------------


class TestRunResearch:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_returns_report_with_metadata(self, mock_run, client):
        """Successful query returns metadata header + report body."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Test Report\n\nBody here.",
            query="test query",
            mode="quick",
            sources_used=4,
            status="full_report",
            critique=None,
        )

        result = await client.call_tool(
            "run_research", {"query": "test query", "mode": "quick"}
        )

        text = result.data
        assert "Mode: quick" in text
        assert "Sources: 4" in text
        assert "Status: full_report" in text
        assert "# Test Report" in text
        assert "not auto-saved" in text

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_auto_saves_standard_mode(self, mock_run, client, tmp_path):
        """Standard mode auto-saves and includes filename in metadata."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Saved Report",
            query="test query",
            mode="standard",
            sources_used=10,
            status="full_report",
            critique=None,
        )

        save_path = tmp_path / "test_query_2026-02-28.md"
        with patch("research_agent.report_store.get_auto_save_path", return_value=save_path), \
             patch("research_agent.safe_io.atomic_write") as mock_write:
            result = await client.call_tool(
                "run_research", {"query": "test query", "mode": "standard"}
            )

        mock_write.assert_called_once_with(save_path, "# Saved Report")
        text = result.data
        assert "Saved: test_query_2026-02-28.md" in text

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_includes_critique_pass(self, mock_run, client):
        """When critique is present, metadata shows pass/fail."""
        from research_agent.critique import CritiqueResult
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report",
            query="test",
            mode="quick",
            sources_used=4,
            status="full_report",
            critique=CritiqueResult(
                source_diversity=4, claim_support=4, coverage=4,
                geographic_balance=3, actionability=4,
                weaknesses="none", suggestions="none",
            ),
        )

        result = await client.call_tool(
            "run_research", {"query": "test", "mode": "quick"}
        )
        assert "Critique: pass" in result.data


# ---------------------------------------------------------------------------
# run_research — error paths
# ---------------------------------------------------------------------------


class TestRunResearchErrors:
    async def test_query_too_long(self, client):
        """Query over 2000 chars returns ToolError."""
        long_query = "x" * 2001
        with pytest.raises(ToolError, match="Query too long"):
            await client.call_tool("run_research", {"query": long_query})

    async def test_invalid_mode(self, client):
        """Invalid mode returns ToolError at boundary before API calls."""
        with pytest.raises(ToolError, match="Must be one of"):
            await client.call_tool(
                "run_research", {"query": "test", "mode": "bogus"}
            )

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_empty_query(self, mock_run, client):
        """Empty query returns ToolError."""
        from research_agent.errors import ResearchError

        mock_run.side_effect = ResearchError("Query cannot be empty")

        with pytest.raises(ToolError, match="Query cannot be empty"):
            await client.call_tool("run_research", {"query": ""})

    @patch.dict("os.environ", {}, clear=True)
    @patch("research_agent.run_research_async")
    async def test_missing_api_keys(self, mock_run, client):
        """Missing API keys returns ToolError."""
        from research_agent.errors import ResearchError

        mock_run.side_effect = ResearchError(
            "ANTHROPIC_API_KEY environment variable is required"
        )

        with pytest.raises(ToolError, match="ANTHROPIC_API_KEY"):
            await client.call_tool("run_research", {"query": "test"})

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_unexpected_exception_returns_clean_error(self, mock_run, client):
        """Unhandled exception returns generic ToolError — no stack trace."""
        mock_run.side_effect = RuntimeError("some internal failure")

        with pytest.raises(ToolError, match="Research failed unexpectedly"):
            await client.call_tool("run_research", {"query": "test"})

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_catch_all_does_not_leak_paths(self, mock_run, client):
        """Catch-all error message does not contain filesystem paths."""
        mock_run.side_effect = OSError(
            "/Users/alejandroguillen/Projects/research-agent/reports/file.md"
        )

        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("run_research", {"query": "test"})

        assert "/Users/" not in str(exc_info.value)
        assert "Research failed unexpectedly" in str(exc_info.value)

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_path_stripping_covers_common_unix_paths(self, mock_run, client):
        """Path stripping catches /opt/, /var/, /tmp/, /app/ paths too."""
        from research_agent.errors import ResearchError

        mock_run.side_effect = ResearchError(
            "Failed to read /opt/app/data/config.yaml"
        )

        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("run_research", {"query": "test"})

        assert "/opt/" not in str(exc_info.value)
        assert "<path>" in str(exc_info.value)


# ---------------------------------------------------------------------------
# list_saved_reports
# ---------------------------------------------------------------------------


class TestListSavedReports:
    @patch("research_agent.get_reports")
    async def test_with_reports(self, mock_reports, client):
        """Returns formatted list of reports."""
        from research_agent.results import ReportInfo

        mock_reports.return_value = [
            ReportInfo(filename="test_2026-02-28_120000.md",
                       date="2026-02-28", query_name="test"),
            ReportInfo(filename="query_2026-02-27_090000.md",
                       date="2026-02-27", query_name="query"),
        ]

        result = await client.call_tool("list_saved_reports", {})

        text = result.data
        assert "test_2026-02-28_120000.md" in text
        assert "query_2026-02-27_090000.md" in text
        assert "2026-02-28" in text

    @patch("research_agent.get_reports")
    async def test_empty_reports(self, mock_reports, client):
        """No reports returns helpful message."""
        mock_reports.return_value = []

        result = await client.call_tool("list_saved_reports", {})

        assert "No saved reports found" in result.data


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------


class TestGetReport:
    async def test_valid_filename(self, client, tmp_path):
        """Returns file content for a valid report."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        report_file = reports_dir / "test_report.md"
        report_file.write_text("# My Report\n\nContent here.")

        with patch("research_agent.report_store.REPORTS_DIR", reports_dir):
            result = await client.call_tool(
                "get_report", {"filename": "test_report.md"}
            )

        assert "# My Report" in result.data

    async def test_path_traversal_rejected(self, client):
        """Path traversal attempt returns ToolError."""
        with pytest.raises(ToolError, match="Invalid filename"):
            await client.call_tool(
                "get_report", {"filename": "../../.env"}
            )

    async def test_non_md_file_rejected(self, client):
        """Non-.md file returns ToolError."""
        with pytest.raises(ToolError, match="Only .md"):
            await client.call_tool(
                "get_report", {"filename": "secrets.txt"}
            )

    async def test_null_byte_rejected(self, client):
        """Null byte in filename returns ToolError."""
        with pytest.raises(ToolError, match="null byte"):
            await client.call_tool(
                "get_report", {"filename": "report\x00.md"}
            )

    async def test_nonexistent_file(self, client, tmp_path):
        """Nonexistent report returns ToolError."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        with patch("research_agent.report_store.REPORTS_DIR", reports_dir):
            with pytest.raises(ToolError, match="Report not found"):
                await client.call_tool(
                    "get_report", {"filename": "nonexistent.md"}
                )

    async def test_dotfile_rejected(self, client):
        """Dotfiles are rejected."""
        with pytest.raises(ToolError, match="Invalid filename"):
            await client.call_tool(
                "get_report", {"filename": ".hidden.md"}
            )

    async def test_backslash_rejected(self, client):
        """Backslash path traversal rejected."""
        with pytest.raises(ToolError, match="Invalid filename"):
            await client.call_tool(
                "get_report", {"filename": "..\\..\\etc\\passwd.md"}
            )

    async def test_special_chars_rejected(self, client):
        """Filenames with special characters rejected."""
        with pytest.raises(ToolError, match="Invalid filename"):
            await client.call_tool(
                "get_report", {"filename": "report name.md"}
            )


# ---------------------------------------------------------------------------
# list_research_modes
# ---------------------------------------------------------------------------


class TestListResearchModes:
    async def test_returns_all_modes(self, client):
        """Lists all three modes with details."""
        result = await client.call_tool("list_research_modes", {})

        text = result.data
        assert "quick" in text
        assert "standard" in text
        assert "deep" in text
        assert "sources" in text


# ---------------------------------------------------------------------------
# list_contexts
# ---------------------------------------------------------------------------


class TestListContexts:
    @patch("research_agent.list_available_contexts")
    async def test_with_contexts(self, mock_contexts, client):
        """Returns context names and previews."""
        mock_contexts.return_value = [
            ("pfe", "Pacific Flow Entertainment context for music industry research"),
        ]

        result = await client.call_tool("list_contexts", {})

        text = result.data
        assert "pfe" in text
        assert "Pacific Flow" in text

    @patch("research_agent.list_available_contexts")
    async def test_no_contexts(self, mock_contexts, client):
        """No contexts returns helpful message."""
        mock_contexts.return_value = []

        result = await client.call_tool("list_contexts", {})

        assert "No context files found" in result.data


# ---------------------------------------------------------------------------
# critique_report
# ---------------------------------------------------------------------------


class TestCritiqueReport:
    async def test_invalid_filename_rejected(self, client):
        """Invalid filename returns ToolError."""
        with pytest.raises(ToolError, match="Invalid filename"):
            await client.call_tool(
                "critique_report", {"filename": "../../.env"}
            )

    @patch("research_agent.critique_report_file")
    async def test_returns_scores(self, mock_critique, client, tmp_path):
        """Successful critique returns formatted scores."""
        from research_agent.critique import CritiqueResult

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        report_file = reports_dir / "test_report.md"
        report_file.write_text("# Test Report\n\nBody here.")

        mock_critique.return_value = CritiqueResult(
            source_diversity=4, claim_support=3, coverage=4,
            geographic_balance=2, actionability=4,
            weaknesses="Limited scope", suggestions="Broaden sources",
        )

        with patch("research_agent.report_store.REPORTS_DIR", reports_dir):
            result = await client.call_tool(
                "critique_report", {"filename": "test_report.md"}
            )

        text = result.data
        assert "PASS" in text
        assert "Source Diversity: 4" in text
        assert "Claim Support: 3" in text
        assert "Limited scope" in text


# ---------------------------------------------------------------------------
# run_research — skip_critique and max_sources params
# ---------------------------------------------------------------------------


class TestRunResearchParams:
    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_skip_critique_passed_through(self, mock_run, client):
        """skip_critique parameter is forwarded to run_research_async."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="quick",
            sources_used=4, status="full_report", critique=None,
        )

        await client.call_tool(
            "run_research", {"query": "test", "mode": "quick", "skip_critique": True}
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["skip_critique"] is True

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_max_sources_passed_through(self, mock_run, client):
        """max_sources parameter is forwarded to run_research_async."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="standard",
            sources_used=6, status="full_report", critique=None,
        )

        await client.call_tool(
            "run_research", {"query": "test", "mode": "standard", "max_sources": 6}
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["max_sources"] == 6


# ---------------------------------------------------------------------------
# _validate_report_filename — direct unit tests
# ---------------------------------------------------------------------------


class TestValidateReportFilename:
    def test_valid_filename(self, tmp_path):
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "valid_report.md").write_text("content")

        with patch("research_agent.report_store.REPORTS_DIR", reports_dir):
            path = _validate_report_filename("valid_report.md")
            assert path.name == "valid_report.md"

    def test_slash_rejected(self):
        with pytest.raises(ValueError, match="Invalid filename"):
            _validate_report_filename("path/to/file.md")

    def test_null_byte_rejected(self):
        with pytest.raises(ValueError, match="null byte"):
            _validate_report_filename("file\x00.md")

    def test_long_filename_rejected(self):
        with pytest.raises(ValueError, match="Filename too long"):
            _validate_report_filename("a" * 253 + ".md")

    def test_non_md_rejected(self):
        with pytest.raises(ValueError, match="Only .md"):
            _validate_report_filename("report.txt")

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="Invalid filename"):
            _validate_report_filename("report (1).md")

    def test_missing_file(self, tmp_path):
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        with patch("research_agent.report_store.REPORTS_DIR", reports_dir):
            with pytest.raises(FileNotFoundError, match="Report not found"):
                _validate_report_filename("missing.md")


# ---------------------------------------------------------------------------
# Transport validation
# ---------------------------------------------------------------------------


class TestTransportValidation:
    def test_invalid_transport_exits(self):
        """MCP_TRANSPORT=invalid produces an error exit."""
        result = subprocess.run(
            [sys.executable, "-m", "research_agent.mcp_server"],
            env={
                **{"PATH": "/usr/bin:/bin"},
                "MCP_TRANSPORT": "invalid",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "Unknown MCP_TRANSPORT" in result.stderr

    def test_non_localhost_http_refused(self):
        """HTTP transport on non-loopback address is refused."""
        result = subprocess.run(
            [sys.executable, "-m", "research_agent.mcp_server"],
            env={
                "PATH": "/usr/bin:/bin",
                "MCP_TRANSPORT": "http",
                "MCP_HOST": "0.0.0.0",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "Refusing to bind" in result.stderr


# ---------------------------------------------------------------------------
# Integration: stdio roundtrip
# ---------------------------------------------------------------------------


class TestStdioIntegration:
    def test_stdio_initialize_handshake(self):
        """Start MCP server via stdio, send initialize, get valid response."""
        import json

        # MCP JSON-RPC initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }

        request_bytes = json.dumps(init_request) + "\n"

        proc = subprocess.Popen(
            [sys.executable, "-m", "research_agent.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(Path.home()),
                "MCP_TRANSPORT": "stdio",
                "PYTHONPATH": str(Path(__file__).parent.parent),
            },
        )

        try:
            stdout, stderr = proc.communicate(input=request_bytes, timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            pytest.fail("MCP server timed out during stdio handshake")

        # The server should produce valid JSON-RPC on stdout
        # (may include multiple lines for the response)
        assert stdout.strip(), f"No stdout output. stderr: {stderr}"
        # Parse the first JSON line
        first_line = stdout.strip().split("\n")[0]
        response = json.loads(first_line)
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        assert "result" in response
        assert "serverInfo" in response["result"]
