"""Tests for the MCP server: all 8 tools, transports, and error paths."""

import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from research_agent.mcp_server import mcp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """In-memory MCP client — no subprocess, no network."""
    async with Client(mcp) as c:
        yield c


@pytest.fixture
def pooled_db(db):
    """Route MCP pooled borrows to the rollback-isolated Postgres fixture."""
    with patch(
        "research_agent.db.pooled_connection",
        side_effect=lambda: nullcontext(db),
    ):
        yield db


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
    async def test_auto_saves_standard_mode(self, mock_run, client, pooled_db):
        """Standard mode auto-saves to Postgres and returns its report key."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Saved Report",
            query="test query",
            mode="standard",
            sources_used=10,
            status="full_report",
            critique=None,
        )

        result = await client.call_tool(
            "run_research", {"query": "test query", "mode": "standard"}
        )

        row = pooled_db.execute(
            "SELECT report_key, content FROM reports"
        ).fetchone()
        assert row["content"] == "# Saved Report"
        text = result.data
        assert f"Saved: {row['report_key']}" in text

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

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_auto_save_state_error_becomes_tool_error(self, mock_run, client):
        from research_agent.errors import StateError
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="standard",
            sources_used=4, status="full_report",
        )
        with patch(
            "research_agent.mcp_server._save_report_db",
            side_effect=StateError("connection lost"),
        ):
            with pytest.raises(ToolError, match="Save report failed"):
                await client.call_tool(
                    "run_research", {"query": "test", "mode": "standard"}
                )


# ---------------------------------------------------------------------------
# list_saved_reports
# ---------------------------------------------------------------------------


class TestListSavedReports:
    async def test_with_reports(self, client, pooled_db):
        """Returns formatted report keys from Postgres."""
        from research_agent.report_store import save_report

        key1 = save_report(
            pooled_db, query="test", mode="standard", content="# One"
        )
        key2 = save_report(
            pooled_db, query="query", mode="standard", content="# Two"
        )

        result = await client.call_tool("list_saved_reports", {})

        text = result.data
        assert key1 in text
        assert key2 in text
        assert "test" in text

    async def test_empty_reports(self, client, pooled_db):
        """No reports returns helpful message."""
        result = await client.call_tool("list_saved_reports", {})

        assert "No saved reports found" in result.data

    async def test_config_error_becomes_tool_error(self, client):
        from research_agent.errors import ConfigError

        with patch(
            "research_agent.db.pooled_connection",
            side_effect=ConfigError("DATABASE_URL is required"),
        ):
            with pytest.raises(ToolError, match="DATABASE_URL"):
                await client.call_tool("list_saved_reports", {})


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------


class TestGetReport:
    async def test_valid_report_key(self, client, pooled_db):
        """Returns DB content for a valid report key."""
        from research_agent.report_store import save_report

        key = save_report(
            pooled_db, query="my report", mode="standard",
            content="# My Report\n\nContent here.",
        )
        result = await client.call_tool("get_report", {"report_key": key})

        assert "# My Report" in result.data

    async def test_path_traversal_rejected(self, client):
        """Path traversal attempt returns ToolError."""
        with pytest.raises(ToolError, match="Invalid report key"):
            await client.call_tool(
                "get_report", {"report_key": "../../.env"}
            )

    async def test_null_byte_rejected(self, client):
        """Null byte in report key returns ToolError."""
        with pytest.raises(ToolError, match="null byte"):
            await client.call_tool(
                "get_report", {"report_key": "report\x00key"}
            )

    async def test_nonexistent_report(self, client, pooled_db):
        """Unknown report key returns ToolError."""
        with pytest.raises(ToolError, match="Report not found"):
            await client.call_tool(
                "get_report", {"report_key": "nonexistent-deadbeef"}
            )

    async def test_backslash_rejected(self, client):
        """Backslash path traversal rejected."""
        with pytest.raises(ToolError, match="Invalid report key"):
            await client.call_tool(
                "get_report", {"report_key": "..\\..\\etc\\passwd"}
            )

    async def test_special_chars_rejected(self, client):
        """Report keys with special characters are rejected."""
        with pytest.raises(ToolError, match="Invalid report key"):
            await client.call_tool(
                "get_report", {"report_key": "report name"}
            )

    async def test_long_report_key_rejected(self, client):
        """Report key over 255 chars returns ToolError."""
        with pytest.raises(ToolError, match="Report key too long"):
            await client.call_tool(
                "get_report", {"report_key": "a" * 256}
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
        assert "min_domains=" in text

    async def test_novelty_queries_visible_in_output(self, client):
        """novelty_queries should appear in list_research_modes output."""
        result = await client.call_tool("list_research_modes", {})

        text = result.data
        assert "novelty=0" in text  # quick
        assert "novelty=1" in text  # standard
        assert "novelty=2" in text  # deep


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
    async def test_invalid_report_key_rejected(self, client):
        """Invalid report key returns ToolError."""
        with pytest.raises(ToolError, match="Invalid report key"):
            await client.call_tool(
                "critique_report", {"report_key": "../../.env"}
            )

    @patch("research_agent.critique.critique_report_text")
    async def test_returns_scores_and_saves_db_critique(
        self, mock_critique, client, pooled_db
    ):
        """Successful critique reads and writes through Postgres."""
        from research_agent.critique import CritiqueResult
        from research_agent.report_store import save_report

        mock_critique.return_value = CritiqueResult(
            source_diversity=4, claim_support=3, coverage=4,
            geographic_balance=2, actionability=4,
            weaknesses="Limited scope", suggestions="Broaden sources",
        )
        key = save_report(
            pooled_db, query="test report", mode="standard",
            content="# Test Report\n\nBody here.",
        )
        result = await client.call_tool(
            "critique_report", {"report_key": key}
        )

        text = result.data
        assert "PASS" in text
        assert "Source Diversity: 4" in text
        assert "Claim Support: 3" in text
        assert "Limited scope" in text
        assert mock_critique.call_args.args[1] == "# Test Report\n\nBody here."
        assert pooled_db.execute(
            "SELECT count(*) AS n FROM critiques"
        ).fetchone()["n"] == 1


# ---------------------------------------------------------------------------
# generate_followups
# ---------------------------------------------------------------------------


class TestGenerateFollowups:
    async def test_invalid_report_key_rejected(self, client):
        """Invalid report key returns ToolError."""
        with pytest.raises(ToolError, match="Invalid report key"):
            await client.call_tool(
                "generate_followups",
                {"query": "test query", "report_key": "../../.env"},
            )

    async def test_empty_query_rejected(self, client):
        """Empty query returns ToolError."""
        with pytest.raises(ToolError, match="non-empty string"):
            await client.call_tool(
                "generate_followups",
                {"query": "", "report_key": "test-deadbeef"},
            )

    @patch("research_agent.iterate.generate_followup_questions")
    async def test_returns_numbered_questions(self, mock_gen, client, pooled_db):
        """Successful generation reads the report from Postgres."""
        from research_agent.iterate import QueryGenerationResult
        from research_agent.report_store import save_report

        mock_gen.return_value = QueryGenerationResult(
            items=("What are the costs?", "How does it compare?"),
            rationale="Missing pricing and comparison data",
        )
        key = save_report(
            pooled_db, query="test query", mode="standard",
            content="# Test Report\n\nBody here.",
        )
        result = await client.call_tool(
            "generate_followups",
            {"query": "test query", "report_key": key},
        )

        text = result.data
        assert "1. What are the costs?" in text
        assert "2. How does it compare?" in text
        assert "Missing pricing" in text


# ---------------------------------------------------------------------------
# get_critique_history
# ---------------------------------------------------------------------------


class TestGetCritiqueHistory:
    @patch("research_agent.context.load_critique_history")
    async def test_returns_summary_when_history_available(
        self, mock_load, client, pooled_db
    ):
        """Should return critique summary text when enough passing critiques exist."""
        from research_agent.context_result import ContextResult
        mock_load.return_value = ContextResult.loaded(
            "Based on 5 recent self-critiques:\n"
            "Weakest dimensions: source_diversity (3.2).",
            source="reports/meta",
        )

        result = await client.call_tool("get_critique_history", {})
        text = result.data
        assert "Weakest dimensions" in text
        assert "source_diversity" in text

    @patch("research_agent.context.load_critique_history")
    async def test_no_history_message_mentions_passing_threshold(
        self, mock_load, client, pooled_db
    ):
        """Should return user-friendly message mentioning passing critiques when none available."""
        from research_agent.context_result import ContextResult
        mock_load.return_value = ContextResult.not_configured(source="reports/meta")

        result = await client.call_tool("get_critique_history", {})
        text = result.data
        assert "No critique history available" in text
        assert "3 passing" in text
        assert "overall_pass: true" in text

    @patch("research_agent.context.load_critique_history")
    async def test_three_failing_critiques_still_no_history(
        self, mock_load, client, pooled_db
    ):
        """3 failing critiques should not produce history — threshold is passing critiques."""
        from research_agent.context_result import ContextResult
        # load_critique_history filters to passing only, returns not_configured if < 3
        mock_load.return_value = ContextResult.not_configured(source="reports/meta")

        result = await client.call_tool("get_critique_history", {})
        assert "No critique history available" in result.data

    @patch("research_agent.context.load_critique_history")
    async def test_empty_context_result_returns_no_history(
        self, mock_load, client, pooled_db
    ):
        """ContextResult.empty() should fall through to no-history message."""
        from research_agent.context_result import ContextResult
        mock_load.return_value = ContextResult.empty(source="reports/meta")

        result = await client.call_tool("get_critique_history", {})
        assert "No critique history available" in result.data

    @patch("research_agent.context.load_critique_history")
    async def test_state_error_returns_tool_error(self, mock_load, client, pooled_db):
        """Expected DB failures are translated to ToolError."""
        from research_agent.errors import StateError

        mock_load.side_effect = StateError("connection lost")

        with pytest.raises(ToolError, match="Load critique history failed"):
            await client.call_tool("get_critique_history", {})


# ---------------------------------------------------------------------------
# run_research — skip_critique and max_sources params
# ---------------------------------------------------------------------------


class TestMcpInstructions:
    """Tests for MCP server instructions string."""

    def test_instructions_mention_generate_followups(self):
        """MCP instructions should mention generate_followups tool."""
        assert "generate_followups" in mcp.instructions

    async def test_all_tools_mentioned_in_instructions(self, client):
        """Every @mcp.tool function name must appear in the instructions string."""
        import re

        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        missing = {
            name for name in tool_names
            if not re.search(rf"\b{re.escape(name)}\b", mcp.instructions)
        }
        assert not missing, (
            f"MCP instructions missing tool names: {sorted(missing)}. "
            "Update the 'instructions' string in mcp_server.py."
        )


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
    async def test_max_sources_passed_through(self, mock_run, client, pooled_db):
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

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_context_null_string_normalized_to_none(self, mock_run, client):
        """LLM-sent "null" string is normalized to None (auto-detect)."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="quick",
            sources_used=4, status="full_report", critique=None,
        )

        await client.call_tool(
            "run_research", {"query": "test", "mode": "quick", "context": "null"}
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["context"] is None

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_context_none_string_preserves_skip(self, mock_run, client):
        """The string "none" still means skip context (not auto-detect)."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="quick",
            sources_used=4, status="full_report", critique=None,
        )

        await client.call_tool(
            "run_research", {"query": "test", "mode": "quick", "context": "none"}
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["context"] == "none"

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_skip_iteration_passed_through(self, mock_run, client):
        """skip_iteration parameter is forwarded to run_research_async."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="quick",
            sources_used=4, status="full_report", critique=None,
        )

        await client.call_tool(
            "run_research", {"query": "test", "mode": "quick", "skip_iteration": True}
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["skip_iteration"] is True

    @patch.dict("os.environ", ENV_BOTH, clear=True)
    @patch("research_agent.run_research_async")
    async def test_iteration_status_in_header(self, mock_run, client, pooled_db):
        """iteration_status='completed' appears in response header."""
        from research_agent.results import ResearchResult

        mock_run.return_value = ResearchResult(
            report="# Report", query="test", mode="standard",
            sources_used=10, status="full_report", critique=None,
            iteration_status="completed",
        )

        result = await client.call_tool(
            "run_research", {"query": "test", "mode": "standard"}
        )

        text = result.data
        assert "Iteration: completed" in text


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
            timeout=30,
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
            timeout=30,
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
