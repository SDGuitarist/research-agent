"""MCP server for the research agent."""

import logging
import os
import re
import sys
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 2000

mcp = FastMCP(
    "Research Agent",
    instructions=(
        "Research agent that searches the web and generates structured markdown reports. "
        "Reports and contexts are relative to the working directory. "
        "Set 'cwd' in your MCP client config to the research-agent project root."
    ),
)


@mcp.tool
async def run_research(
    query: str,
    mode: str = "standard",
    context: str | None = None,
) -> str:
    """Run a research query and get a structured markdown report.

    Expected duration: quick ~10-20s, standard ~30-60s, deep ~90-180s.

    Args:
        query: The research question to investigate.
        mode: Research depth — "quick" (4 sources, ~$0.12),
              "standard" (10 sources, ~$0.35), or "deep" (12 sources, 2-pass, ~$0.85).
        context: Three-way behavior:
                 - Omit (default None): auto-detect context from contexts/ dir
                   (costs 1 extra API call to scan available files).
                 - "none" (string): skip context loading entirely — no extra API call.
                 - "<name>" (e.g., "pfe"): load a specific context file from contexts/<name>.yaml.
                 Use list_contexts to see available names.
    """
    from fastmcp.exceptions import ToolError

    from research_agent import ResearchError, run_research_async
    from research_agent.errors import StateError
    from research_agent.report_store import REPORTS_DIR, get_auto_save_path
    from research_agent.safe_io import atomic_write

    if len(query) > MAX_QUERY_LENGTH:
        raise ToolError(
            f"Query too long ({len(query)} chars, max {MAX_QUERY_LENGTH}). "
            "Shorten your query and try again."
        )

    try:
        result = await run_research_async(query, mode=mode, context=context)
    except ResearchError as e:
        # Strip absolute filesystem paths to avoid leaking server directory structure
        msg = re.sub(r'(/Users/|/home/)\S+', '<path>', str(e))
        raise ToolError(msg)
    except Exception:
        logger.exception("Unexpected error in run_research")
        # Server boundary catch-all. Don't expose raw exception message
        # (may contain filesystem paths from third-party libs).
        # See CLAUDE.md: "Never bare except Exception" — this is the one
        # justified exception: an MCP server boundary where unhandled errors
        # would crash the entire server process.
        raise ToolError(
            "Research failed unexpectedly. Try again, or use a different mode/query. "
            "If the error persists, check that API keys are configured."
        )

    # Auto-save for standard/deep modes (intentionally omits research log —
    # that's a CLI convenience feature, not an MCP concern)
    saved_to = None
    if result.mode in ("standard", "deep"):
        try:
            save_path = get_auto_save_path(query)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(save_path, result.report)
            saved_to = save_path.name
        except (OSError, StateError) as e:
            logger.warning("Auto-save failed: %s", e)

    # Format metadata header
    save_info = saved_to or "(not auto-saved, use mode=standard to save)"
    critique_info = ""
    if result.critique is not None:
        critique_info = f" | Critique: {'pass' if result.critique.overall_pass else 'FAIL'}"
    header = (
        f"Mode: {result.mode} | Sources: {result.sources_used} | "
        f"Status: {result.status} | Saved: {save_info}{critique_info}"
    )
    return f"{header}\n\n{result.report}"


@mcp.tool
def list_saved_reports() -> str:
    """List all saved research reports with dates and query names.

    Returns a formatted list of reports available for retrieval via get_report.
    """
    from research_agent import get_reports

    reports = get_reports()
    if not reports:
        return "No saved reports found. Run research in standard or deep mode to auto-save."
    lines = []
    for r in reports:
        date_str = r.date or "unknown date"
        lines.append(f"- {r.filename} ({date_str}: {r.query_name})")
    return "\n".join(lines)


@mcp.tool
def get_report(filename: str) -> str:
    """Retrieve a saved research report by filename.

    Args:
        filename: Report filename (e.g., "query_name_2026-02-28_143052.md").
                  Use list_saved_reports to see available files.
    """
    from fastmcp.exceptions import ToolError

    try:
        path = _validate_report_filename(filename)
    except (ValueError, FileNotFoundError) as e:
        raise ToolError(str(e))
    return path.read_text()


@mcp.tool
def list_research_modes() -> str:
    """Show available research modes and their configurations."""
    from research_agent import list_modes

    modes = list_modes()
    lines = []
    for m in modes:
        save_str = "auto-saves" if m.auto_save else "no auto-save"
        lines.append(
            f"- {m.name}: {m.max_sources} sources, ~{m.word_target} words, "
            f"{m.cost_estimate}, {save_str}"
        )
    return "\n".join(lines)


@mcp.tool
def list_contexts() -> str:
    """List available research context files and their descriptions.

    Use context names as the 'context' parameter in run_research.
    """
    from research_agent import list_available_contexts

    contexts = list_available_contexts()
    if not contexts:
        return "No context files found in contexts/ directory."
    lines = []
    for name, preview in contexts:
        lines.append(f"- {name}: {preview[:100]}")
    return "\n".join(lines)


def _validate_report_filename(filename: str) -> Path:
    """Validate and resolve a report filename, preventing path traversal."""
    from research_agent.report_store import REPORTS_DIR

    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise ValueError(f"Invalid filename: {filename!r}")
    if "\x00" in filename:
        raise ValueError("Invalid filename: contains null byte")
    if len(filename) > 255:
        raise ValueError(f"Filename too long: {len(filename)} characters")
    if not filename.endswith(".md"):
        raise ValueError("Only .md report files can be retrieved")
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValueError(f"Invalid filename characters: {filename!r}")
    path = (REPORTS_DIR / filename).resolve()
    if not path.is_relative_to(REPORTS_DIR.resolve()):
        raise ValueError("Filename resolves outside reports/ directory")
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {filename}")
    return path


def main():
    """Entry point for the research-agent-mcp console script."""
    from dotenv import load_dotenv

    load_dotenv()

    log_level = os.environ.get("MCP_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, log_level, logging.WARNING),
        format="%(levelname)s: %(name)s: %(message)s",
    )

    # CWD sanity check
    if not Path("research_agent").is_dir() and not Path("pyproject.toml").exists():
        logger.warning(
            "CWD does not appear to be the research-agent project root. "
            "Set 'cwd' in your MCP client config."
        )

    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("MCP_PORT", "8000"))
        except ValueError:
            sys.exit(f"MCP_PORT must be an integer, got: {os.environ['MCP_PORT']!r}")

        if host not in ("127.0.0.1", "localhost"):
            logger.warning(
                "MCP server binding to %s:%d — accessible on the network. "
                "No authentication is configured.", host, port,
            )

        # host/port go in FastMCP settings, not run(). run() only accepts transport.
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="http")
    else:
        sys.exit(f"Unknown MCP_TRANSPORT: {transport!r}. Use 'stdio' or 'http'.")


if __name__ == "__main__":
    main()
