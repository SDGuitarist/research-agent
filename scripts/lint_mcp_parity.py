#!/usr/bin/env python3
"""Lint: verify every @mcp.tool is mentioned in the MCP instructions string."""

import asyncio
import re
import sys

from research_agent.mcp_server import mcp


def find_missing_tools(tool_names: list[str], instructions: str) -> list[str]:
    """Return tool names not mentioned as whole words in the instructions."""
    return [
        name for name in tool_names
        if not re.search(rf"\b{re.escape(name)}\b", instructions)
    ]


def main() -> int:
    instructions = mcp.instructions or ""
    tools = asyncio.run(mcp.list_tools())
    tool_names = sorted(t.name for t in tools)

    missing = find_missing_tools(tool_names, instructions)

    if missing:
        print(f"FAIL: MCP instructions missing tool names: {missing}")
        print("Update the 'instructions' string in mcp_server.py.")
        return 1

    print(f"OK: All {len(tool_names)} tools mentioned in instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
