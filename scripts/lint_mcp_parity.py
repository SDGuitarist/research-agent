#!/usr/bin/env python3
"""Lint MCP discoverability and cross-consumer Postgres storage parity."""

import asyncio
import ast
import re
import sys
from pathlib import Path

from research_agent.mcp_server import mcp


ROOT = Path(__file__).resolve().parents[1]
CONSUMER_STORAGE_OPS = {
    "cli": {
        "path": ROOT / "research_agent/cli.py",
        "required": {"get_reports", "save_report", "save_critique", "load_critique_history"},
    },
    "mcp": {
        "path": ROOT / "research_agent/mcp_server.py",
        "required": {
            "get_reports", "get_report", "save_report",
            "save_critique", "load_critique_history",
        },
    },
    # Session 5 activates this check automatically when web.py lands.
    "web": {
        "path": ROOT / "research_agent/web.py",
        "required": {"get_reports", "get_report"},
    },
    # Session 6 worker persists finished reports through the shared store.
    "worker": {
        "path": ROOT / "research_agent/worker.py",
        "required": {"save_report"},
    },
}
STORAGE_MODULES = {
    "research_agent.report_store",
    "research_agent.critique",
    "research_agent.context",
}
REMOVED_FILE_SHIMS = {
    "get_archived_reports",
    "save_critique_file",
    "load_critique_history_files",
}


def find_missing_tools(tool_names: list[str], instructions: str) -> list[str]:
    """Return tool names not mentioned as whole words in the instructions."""
    return [
        name for name in tool_names
        if not re.search(rf"\b{re.escape(name)}\b", instructions)
    ]


def imported_storage_ops(path: Path) -> set[str]:
    """Return canonical storage symbols imported and called by an entry point."""
    tree = ast.parse(path.read_text(), filename=str(path))
    aliases = {
        alias.asname or alias.name: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module in STORAGE_MODULES
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    return {canonical for local, canonical in aliases.items() if local in called_names}


def find_storage_parity_errors() -> list[str]:
    """Check active CLI/MCP/web consumers use their shared Postgres stores."""
    errors = []
    for consumer, config in CONSUMER_STORAGE_OPS.items():
        path = config["path"]
        if not path.exists():
            continue
        imported = imported_storage_ops(path)
        missing = config["required"] - imported
        if missing:
            errors.append(f"{consumer} missing DB storage ops: {sorted(missing)}")
        stale = REMOVED_FILE_SHIMS & imported
        if stale:
            errors.append(f"{consumer} still imports file shims: {sorted(stale)}")
    return errors


def main() -> int:
    instructions = mcp.instructions or ""
    tools = asyncio.run(mcp.list_tools())
    tool_names = sorted(t.name for t in tools)

    missing = find_missing_tools(tool_names, instructions)

    if missing:
        print(f"FAIL: MCP instructions missing tool names: {missing}")
        print("Update the 'instructions' string in mcp_server.py.")
        return 1

    storage_errors = find_storage_parity_errors()
    if storage_errors:
        for error in storage_errors:
            print(f"FAIL: {error}")
        return 1

    print(f"OK: All {len(tool_names)} tools mentioned in instructions.")
    active = [
        name for name, config in CONSUMER_STORAGE_OPS.items()
        if config["path"].exists()
    ]
    print(f"OK: Postgres storage parity checked for {', '.join(active)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
