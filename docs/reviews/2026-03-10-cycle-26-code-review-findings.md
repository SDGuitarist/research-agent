# Code Review Findings — Cycle 26 MCP Parity Lint Script + CI Workflow

### Prior Phase Risk

> **Least confident about going into review?** Whether the `<4.0` upper bound is too permissive — fastmcp 3.x is a major version jump and we only tested with 3.0.2.

This review confirms that risk. The merged lint script and workflow work on the locally installed `fastmcp 3.0.2`, but the `pyproject.toml` change broadens the runtime dependency contract for the whole package beyond what this cycle actually verified.

## Findings

### P2 Blocker — `pyproject.toml` widened FastMCP support to every 3.x release even though this cycle only validated 3.0.2

- Evidence: `pyproject.toml:22` now allows `fastmcp>=2.0,<4.0`, where the pre-merge parent had `fastmcp>=2.0,<3.0`. The new lint script calls `mcp.list_tools()` at `scripts/lint_mcp_parity.py:10-22`, and the existing parity test does the same at `tests/test_mcp_server.py:462-466`, so the repo is now relying on the FastMCP 3.x surface that was validated locally. This repo had already documented the wider `<4.0` range as risky and intentionally tightened it in `todos/099-done-p3-tighten-fastmcp-version.md:13-29` and `docs/fixes/cycle-19-mcp-server/batch3.md:23-25`.
- Exact impact: every fresh install and the new required `mcp-lint` check now float to whichever FastMCP 3.x release is newest, even though only 3.0.2 was exercised. A future 3.x release can start breaking CI, MCP startup, or the client/test surface on unrelated PRs even when this repo's code has not changed.
- Fix before next phase: narrow the dependency to the actually tested 3.x line instead of all `<4.0` releases, then widen only as part of a deliberate FastMCP upgrade cycle. If the team intentionally wants open-ended 3.x support, it needs broader compatibility proof than this lint script provides.

### P3 Advisory — The new required CI check only proves `list_tools()` parity, not the broader FastMCP range the package now claims to support

- Evidence: `.github/workflows/mcp-lint.yml:1-17` installs dependencies and runs only `python scripts/lint_mcp_parity.py`, and that script only imports the MCP server and calls `mcp.list_tools()` at `scripts/lint_mcp_parity.py:10-22`.
- Exact impact: if `pyproject.toml` keeps the wider FastMCP range, the required check can still go green while another FastMCP 3.x change breaks MCP client calls, `ToolError`, or transport behavior elsewhere in the repo.
- Fix: either narrow the dependency range (preferred), or add a compatibility check that exercises more of the MCP surface than `list_tools()` alone.

No additional material findings in `scripts/lint_mcp_parity.py` or `.github/workflows/mcp-lint.yml`.

## What I Did Not Review Or Could Not Verify

- I did not run a live GitHub Actions job from this environment or inspect the merged run logs directly.
- I did not test against any FastMCP version other than the locally installed `3.0.2`, so I cannot say which wider 3.x range is truly safe.
- I inspected the substring-matching and `asyncio.run()` concerns from the handoff and did not find a concrete current bug there. With today's 7 underscore-delimited tool names, the substring check is not producing a false pass, and the script is used as a standalone entrypoint rather than a shared async helper.

## Checks Run

- `git show --stat --summary 7dbde5a`
- `python3 scripts/lint_mcp_parity.py` -> `OK: All 7 tools mentioned in instructions.`
- `python3 -m pytest tests/ -v` -> 938 passed
- `python3 -c "import fastmcp; import asyncio; from research_agent.mcp_server import mcp; ..."` -> confirmed `fastmcp 3.0.2` and 7 registered tools

## Suggested Fix Order

1. Re-tighten the FastMCP constraint to the deliberately tested 3.x range so fresh installs and required CI do not float to arbitrary future releases.
2. Only if the team wants open-ended 3.x support, add broader MCP compatibility coverage before widening the range again.

## Claude Code Fix Prompt

```text
Read docs/reviews/2026-03-10-cycle-26-code-review-findings.md and docs/reviews/2026-03-10-cycle-26-codex-review-handoff.md.

Fix the FastMCP version-range blocker from cycle 26. Do not redesign the lint script or workflow unless the dependency fix proves insufficient.

Exact scope:
- pyproject.toml
- HANDOFF.md only if you need to record the follow-up work
- docs/reviews/2026-03-10-cycle-26-code-review-findings.md is reference only

Required change:
- Replace `fastmcp>=2.0,<4.0` with a deliberately tested 3.x constraint rather than an open-ended 3.x range.
- Keep `scripts/lint_mcp_parity.py` and `.github/workflows/mcp-lint.yml` unchanged unless you discover a concrete compatibility reason they must move with the dependency fix.

Acceptance criteria:
- Fresh installs no longer float to arbitrary future FastMCP 3.x releases.
- `python3 scripts/lint_mcp_parity.py` still exits 0.
- `python3 -m pytest tests/ -v` still passes.
- HANDOFF.md reflects the follow-up state if you change `pyproject.toml`.

Stop conditions:
- Stop after narrowing the dependency constraint and re-running the required checks.
- Do not modify `research_agent/` or `tests/` unless the dependency change reveals a real compatibility failure.
```

## Three Questions

1. **Hardest judgment call in this review?** Whether the widened FastMCP cap is a blocker even though the full suite still passes on 3.0.2. I treated it as a blocker because it changes clean-install behavior for the whole package, not just this one script.
2. **What did you consider flagging but chose not to, and why?** I considered flagging the substring-matching logic in the lint script and the `asyncio.run()` call, but with the current tool names and standalone invocation path they are not concrete bugs in this merge.
3. **What might this review have missed?** A future FastMCP 3.x release could break a code path that the current local test suite and parity script do not exercise, especially if the dependency range stays broad.
