#!/usr/bin/env python3
"""Lint: verify every @mcp.tool is mentioned in the MCP instructions string."""

import asyncio
import sys

from research_agent.mcp_server import mcp


def main() -> int:
    instructions = mcp.instructions or ""
    tools = asyncio.run(mcp.list_tools())
    tool_names = sorted(t.name for t in tools)

    missing = [name for name in tool_names if name not in instructions]

    if missing:
        print(f"FAIL: MCP instructions missing tool names: {missing}")
        print("Update the 'instructions' string in mcp_server.py.")
        return 1

    print(f"OK: All {len(tool_names)} tools mentioned in instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
