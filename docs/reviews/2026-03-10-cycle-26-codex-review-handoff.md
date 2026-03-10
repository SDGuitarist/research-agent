# Codex Code Review Handoff — Cycle 26: MCP Parity Lint Script + CI Workflow

## Your Job

Review the **code changes** merged in PR #6 for correctness, safety, and adherence to project conventions. This is a code review, not a plan review — the code is already on `main`.

## Read First

1. `CLAUDE.md` — repo conventions, architecture, test commands
2. `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md` — the plan these changes implement
3. `docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md` — plan review findings (3 items, all addressed before work)
4. `docs/reviews/CODEX-REVIEW-GATE.md` — review priorities for this repo

## What Changed

Three files, 45 lines added, 1 line modified. Merge commit `7dbde5a`.

| File | Change | Lines |
|------|--------|-------|
| `scripts/lint_mcp_parity.py` | New — standalone parity lint script | 27 |
| `.github/workflows/mcp-lint.yml` | New — CI workflow (push to main + PRs) | 17 |
| `pyproject.toml` | Modified — `fastmcp>=2.0,<3.0` → `fastmcp>=2.0,<4.0` | 1 |

Branch protection rule was also added: `mcp-lint` is now a required status check on `main`.

## What Must NOT Have Changed

- `research_agent/mcp_server.py` — no MCP server changes
- `tests/test_mcp_server.py` — existing parity test untouched
- Any file under `research_agent/` — purely additive tooling
- No new runtime dependencies added

## Risks to Scrutinize

### 1. Version cap bump (`pyproject.toml`)

The plan's scope fence said `pyproject.toml` must NOT be touched. It was modified because CI installed fastmcp 2.14.5 (where `list_tools()` is private `_list_tools`), while local dev runs 3.0.2. The cap was bumped to `<4.0` to align CI with the tested local version.

**Check:** Is `<4.0` the right upper bound? Could fastmcp 3.x introduce breaking changes elsewhere in the codebase beyond `list_tools()`? All 938 tests pass on 3.0.2 locally, but verify no subtle API differences exist.

### 2. Substring matching in lint script

`name not in instructions` is a substring match. A tool named `report` would pass if "report" appears anywhere in the instructions string. The existing pytest test uses the same logic, so this is consistent — but is it correct? Current 7 tool names are long and distinct, but this is a latent false-pass risk.

**Check:** Review the current tool names and instructions string. Could any tool name be a substring of a common English word that appears in the instructions for a different reason?

### 3. `asyncio.run()` in standalone script

The script calls `asyncio.run(mcp.list_tools())`. This works standalone and in CI, but would fail if imported from within an existing event loop (e.g., a test using `pytest-asyncio`).

**Check:** Is there any risk of someone importing `main()` from the script in a context with a running event loop? The `if __name__ == "__main__"` guard helps, but the function itself is importable.

### 4. CI workflow hardening

- No `apt-get` fallback for system packages — `pip install -e .` succeeded on first try, so this was unnecessary
- Python 3.12 pinned (project requires `>=3.10`) — acceptable for a lint check
- No caching of pip dependencies — each run installs from scratch (~30s total)

**Check:** Is the workflow missing any best practices (timeouts, permissions, concurrency limits)?

### 5. Plan deviation

The plan said 2 new files, 0 modifications. Actual: 2 new files, 1 modification (`pyproject.toml`). The deviation was justified (CI would fail without it), but verify no other unplanned changes slipped in.

## Verified Locally

- `python3 scripts/lint_mcp_parity.py` → exits 0, prints `OK: All 7 tools mentioned in instructions.`
- `python3 -m pytest tests/ -x -q` → 938 passed
- CI workflow ran green on PR #6 (run ID `22839714416`, 31s)
- Importing `research_agent.mcp_server` without API keys registers all 7 tools

## What to Produce

Write findings to `docs/reviews/2026-03-10-cycle-26-code-review-findings.md` with:

- Priority (P1/P2/P3) per CODEX-REVIEW-GATE priority order
- Whether each finding is a **blocker** (must fix) or **advisory** (acceptable risk)
- Specific file paths and line numbers where relevant
- If any risks above are confirmed, note the exact impact

## Three Questions from Work Phase

1. **Hardest implementation decision?** Whether to fix the fastmcp version cap in `pyproject.toml` (scope deviation) or hack around it with private API `_list_tools`. Chose the version fix because the cap was genuinely stale and `_list_tools` is fragile.
2. **What did you consider changing but left alone?** The existing pytest parity test at `test_mcp_server.py:462-470` — considered extracting shared logic between it and the script, but left it alone per the plan's scope fence. The duplication is ~5 lines.
3. **Least confident about going into review?** Whether the `<4.0` upper bound is too permissive — fastmcp 3.x is a major version jump and we only tested with 3.0.2. A future 3.x minor could theoretically break something the tests don't cover.
