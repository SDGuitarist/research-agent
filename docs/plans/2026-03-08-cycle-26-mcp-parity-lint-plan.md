---
cycle: 26
title: "MCP Parity Lint Script + CI Workflow"
status: active
feed_forward:
  risk: "Whether the GitHub Actions workflow will work correctly — Python version, dependency installation, and whether fastmcp tools register at import time"
  verify_first: true
---

# Plan: MCP Parity Lint Script + CI Workflow (Cycle 26)

**Date:** 2026-03-08
**Brainstorm:** `docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md`

### Prior Phase Risk

> **Least confident about:** Whether the GitHub Actions workflow will work correctly on first try — Python version, dependency installation, and whether `fastmcp` tools registration happens at import time or requires explicit setup.

**Resolution (partial):** Verified locally that `asyncio.run(mcp.list_tools())` returns all 7 tools after a bare import of `research_agent.mcp_server` — no server startup needed, `@mcp.tool` decorators register at import time. However, whether `pip install -e .` succeeds on a clean `ubuntu-latest` runner without additional system packages remains **unverified** (see Risk #4 below).

## Plan Quality Gate

1. **What exactly is changing?** Two new files: `scripts/lint_mcp_parity.py` (standalone lint script) and `.github/workflows/mcp-lint.yml` (CI workflow). No existing files are modified. After the workflow is live, a manual repo-settings step makes it a required status check.
2. **What must not change?** MCP server behavior, existing test outcomes, the instructions string content, the existing pytest parity test.
3. **How will we know it worked?** (a) `python scripts/lint_mcp_parity.py` exits 0 locally, (b) all 938 existing tests still pass, (c) the workflow runs green on the first push, (d) the branch protection rule lists `mcp-lint` as required.
4. **Most likely way this plan is wrong?** The CI runner may lack system packages needed to build `lxml` or `trafilatura` wheels. This is **unverified** — `ubuntu-latest` likely has the needed deps, but if `pip install -e .` fails in CI, the fix is adding `apt-get install -y libxml2-dev libxslt-dev` before the pip install step. This is a rollout risk, not a solved risk.

## Prerequisites

**CI install** (GitHub Actions — installs runtime deps only):
```bash
pip install -e .
```

**Local verification** (developer machine — installs runtime + test deps):
```bash
pip install -e ".[test]"
```

Note: `CLAUDE.md` documents `pip install -e ".[test]"` as the local setup command. The `README.md` still references `pip install -r requirements.txt` (outdated). Test deps (`pytest`, `pytest-asyncio`) live in the `[project.optional-dependencies] test` extra in `pyproject.toml:25-29`.

## Session 1: Both Files (Single Session)

Both files are small enough for one session (~45 lines total).

### Step 1: Create `scripts/lint_mcp_parity.py`

**Exact content:**

```python
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
```

**Design notes:**
- No `sys.path` manipulation — the package is installed via `pip install -e .` (same as all other scripts in this project)
- Uses sorted list (not set) so missing tool names print in deterministic order
- Returns int exit code, does not call `sys.exit()` inside `main()` (testable)
- Same logic as the pytest test at `tests/test_mcp_server.py:462-470`, adapted for standalone use

**Verify:** Ensure `pip install -e ".[test]"` has been run locally, then: `python scripts/lint_mcp_parity.py` → should print `OK: All 7 tools mentioned in instructions.` and exit 0.

### Step 2: Create `.github/workflows/mcp-lint.yml`

**Exact content:**

```yaml
name: MCP Parity Lint

on:
  push:
    branches: [main]
  pull_request:

jobs:
  mcp-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .
      - run: python scripts/lint_mcp_parity.py
```

**Design notes:**
- Python 3.12: stable, well-supported, within `>=3.10` constraint
- `pip install -e .` installs `fastmcp` and all deps — same install method as local dev
- No API keys needed — the script only imports the `mcp` object, never calls research functions
- Triggers on push to main + all PRs — standard pattern
- Single job, ~30s total (checkout + python setup + pip install + lint)

**Verify:** YAML syntax is valid. Workflow triggers are correct.

### Step 3: Rollout — Make `MCP Parity Lint` a required status check

After the workflow file is pushed and runs green at least once:

1. Go to **GitHub → repo Settings → Branches → Branch protection rules** for `main`
2. Under **Require status checks to pass before merging**, add `mcp-lint` (the job name from the workflow)
3. Save the rule

This is a **manual step** — it cannot be done via a committed file. Until this step is complete, the workflow only provides CI visibility (advisory), not merge-blocking enforcement.

**Note:** If the repo does not yet have branch protection on `main`, create a new rule for `main` first.

### Step 4: Make lint script executable

```bash
chmod +x scripts/lint_mcp_parity.py
```

### Step 5: Run existing tests

```bash
python3 -m pytest tests/ -x -q
```

All 938 tests must pass (requires `pip install -e ".[test]"` — see Prerequisites). No existing tests should be affected since we're only adding new files.

## Scope Fence

**Files created:** 2
- `scripts/lint_mcp_parity.py`
- `.github/workflows/mcp-lint.yml`

**Files modified:** 0

**Files that must NOT be touched:**
- `research_agent/mcp_server.py` — no changes to the server
- `tests/test_mcp_server.py` — existing parity test stays as-is
- `pyproject.toml` — no new dependencies

## Feed-Forward

- **Hardest decision:** Whether to pin Python 3.12 in CI or use a matrix. Chose single version — this is a lint check, not a compatibility test. Matrix adds complexity for zero benefit here.
- **Rejected alternatives:** (1) Using `pip install .` (non-editable) in CI — works but `pip install -e .` matches local dev workflow. (2) Adding a test for the lint script itself — YAGNI, the script is 20 lines and the pytest parity test already validates the same logic. (3) Claiming the workflow alone "prevents drift" — narrowed to CI visibility until the branch-protection step is completed.
- **Least confident:** Two unverified items: (a) Whether `pip install -e .` on `ubuntu-latest` will succeed without additional system packages — if it fails, add `apt-get install -y libxml2-dev libxslt-dev` before pip install. (b) Whether the repo already has branch protection rules on `main` that might conflict with the new required check.
