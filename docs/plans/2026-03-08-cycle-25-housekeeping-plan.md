---
cycle: 25
title: "Housekeeping — MCP Parity Lint + Public parse_context_file"
status: complete
feed_forward:
  risk: "Whether all _parse_template test imports should switch to the public wrapper, or just the ones testing public behavior"
  verify_first: true
---

# Plan: Housekeeping — MCP Parity Lint + Public parse_context_file (Cycle 25)

**Date:** 2026-03-08
**Brainstorm:** `docs/brainstorms/2026-03-08-cycle-25-housekeeping-brainstorm.md`

### Prior Phase Risk

> **Least confident about:** Whether all `_parse_template` test imports should switch to the public wrapper, or just the ones testing public behavior. Plan phase should audit each test.

**Resolution:** Audited all 26 call sites in `test_context.py`. Two test classes use `_parse_template`: `TestParseTemplate` (17 calls, lines 214–439) and `TestParseTemplateFrontmatterDetection` (5 calls, lines 966–1007). All tests exercise the same public contract (input string → output tuple). None test internal implementation details like caching or private state. **Decision: switch all to `parse_context_file`.** The private `_parse_template` import can be removed entirely from the test file.

## Plan Quality Gate

1. **What exactly is changing?** Two things: (a) new `scripts/lint_mcp_parity.py` file, (b) new `parse_context_file()` in `context.py` + import swaps in `cli.py` and `test_context.py`.
2. **What must not change?** Pipeline behavior, MCP server behavior, test outcomes, `_parse_template` internals.
3. **How will we know it worked?** All 938 tests pass. Lint script exits 0 on current codebase. `cli.py` no longer imports `_parse_template`.
4. **Most likely way this plan is wrong?** A test assertion references `_parse_template` by name in a string (e.g., docstring or error message) that we miss. Mitigated by grep audit above — no such references exist.

## Session 1: Both Items (Single Session)

Both items are small enough for one session (~60 lines total new/changed code).

### Step 1: Add `parse_context_file()` to `context.py`

**File:** `research_agent/context.py`

Add immediately after `_parse_template` (after the function ends, before the next function):

```python
def parse_context_file(
    raw: str,
) -> tuple[str, ReportTemplate | None, ContextProfile | None]:
    """Parse a context file's YAML frontmatter and body.

    Public wrapper around the internal template parser. Use this
    for any code outside context.py that needs to parse context files.

    Args:
        raw: Full file content (may or may not have YAML frontmatter).

    Returns:
        (body, template, profile) — body is the content after the closing
        ``---``, template is the parsed ReportTemplate or None if no valid
        template, profile is the parsed ContextProfile or None if no profile
        fields are present.

    Never raises — returns (raw, None, None) on any error.
    """
    return _parse_template(raw)
```

**What must not change:** `_parse_template` itself. `load_full_context()` at line 265 keeps calling `_parse_template` directly.

### Step 2: Export from `__init__.py`

**File:** `research_agent/__init__.py`

- Add `parse_context_file` to the import line (line 10): `from .context import list_available_contexts, load_critique_history, resolve_context_path, parse_context_file`
- Add `"parse_context_file"` to `__all__` list (alphabetical order, after `"list_modes"`)

### Step 3: Update `cli.py` import

**File:** `research_agent/cli.py`

- Line 18: change `_parse_template,` to `parse_context_file,`
- Line 224: change `_parse_template(raw)` to `parse_context_file(raw)`

### Step 4: Update `test_context.py` imports

**File:** `tests/test_context.py`

- Line 18: change `_parse_template,` to `parse_context_file,`
- All 22 call sites (lines 231–1004): replace `_parse_template(` with `parse_context_file(`
- Class docstring at line 215: change `_parse_template()` to `parse_context_file()`

### Step 5: Add `scripts/lint_mcp_parity.py`

**File:** `scripts/lint_mcp_parity.py` (new file)

```python
#!/usr/bin/env python3
"""Lint: verify all @mcp.tool functions are mentioned in the MCP instructions string.

Usage:
    python scripts/lint_mcp_parity.py

Exits 0 if all tools are mentioned, 1 if any are missing.
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research_agent.mcp_server import mcp  # noqa: E402


def main() -> int:
    instructions = mcp.instructions or ""
    tools = asyncio.run(mcp.list_tools())
    tool_names = {t.name for t in tools}

    missing = {name for name in tool_names if name not in instructions}

    if missing:
        print(f"FAIL: MCP instructions missing tool names: {sorted(missing)}")
        print("Update the 'instructions' string in mcp_server.py.")
        return 1

    print(f"OK: All {len(tool_names)} tools mentioned in instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Risk:** Minimal — uses the same public `mcp.list_tools()` API as the existing pytest test. `asyncio.run()` is fine for a one-shot script.

### Step 6: Test the lint script

Run `python scripts/lint_mcp_parity.py` — expect exit 0.

### Step 7: Run full test suite

`python3 -m pytest tests/ -v` — all 938 tests must pass.

### Commit Plan

Two commits:

1. `feat(25-1): add parse_context_file public wrapper and update imports`
   - `context.py`, `__init__.py`, `cli.py`, `test_context.py`

2. `feat(25-2): add MCP parity lint script`
   - `scripts/lint_mcp_parity.py`

## Feed-Forward

- **Hardest decision:** Whether to switch all 22 `_parse_template` test calls to the public wrapper or keep some on the private function. Audited every call — all test the same public contract (string in → tuple out), none test internal state. Switched all.
- **Rejected alternatives:** FastMCP internals access (`_tool_manager._tools` — doesn't exist), `inspect` module to find decorators (fragile), removing the existing pytest parity test (stays as authoritative async check).
- **Least confident:** Whether `parse_context_file` needs to be in `__all__` / `__init__.py`. It's used by CLI (internal) and tests, not by external consumers. Including it for completeness since other context functions (`list_available_contexts`, `resolve_context_path`) are already exported. If this is wrong, it's trivially reversible.
