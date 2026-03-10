# Codex Plan Review Handoff — Cycle 26: MCP Parity Lint Script + CI Workflow

## Your Job

Review the **plan** for correctness and completeness before work begins. This is a plan review, not a code review — no code has been written yet.

## Read First

1. `CLAUDE.md` — repo conventions, architecture, test commands
2. `docs/plans/2026-03-08-cycle-26-mcp-parity-lint-plan.md` — the plan to review
3. `docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md` — brainstorm context
4. `docs/reviews/CODEX-REVIEW-GATE.md` — review priorities for this repo

## Context: Why This Exists

This lint script has been deferred 4 times (cycles 19, 20, 22, 25). Cycle 25's plan review (by you) correctly blocked it because it "duplicates an existing check without a stated enforcement path." This cycle's answer: **GitHub Actions CI workflow** as the enforcement path.

## What the Plan Proposes

Two new files, zero modifications to existing code (~45 lines total):

### File 1: `scripts/lint_mcp_parity.py`

- Imports `mcp` object from `research_agent.mcp_server`
- Calls `asyncio.run(mcp.list_tools())` to get registered tool names
- Checks each tool name appears in `mcp.instructions` string
- Exits 0 (all tools mentioned) or 1 (missing tools)
- Same logic as existing pytest test at `tests/test_mcp_server.py:462-470`

### File 2: `.github/workflows/mcp-lint.yml`

- Triggers on `push` to `main` and `pull_request`
- `ubuntu-latest`, Python 3.12, `pip install -e .`, runs the script
- Single job, ~30s estimated

## Files That Will Be Created

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/lint_mcp_parity.py` | ~25 | Standalone lint script |
| `.github/workflows/mcp-lint.yml` | ~15 | CI enforcement |

## Files That Must NOT Change

- `research_agent/mcp_server.py` — no MCP server changes
- `tests/test_mcp_server.py` — existing parity test stays as-is
- `pyproject.toml` — no new dependencies
- Any file under `research_agent/` — this is purely additive tooling

## Risks to Scrutinize

1. **Does the CI workflow actually solve the cycle 25 blocker?** The previous review said "duplicates existing check without a stated enforcement path." The plan now adds a GitHub Actions workflow. Is this sufficient enforcement, or does it need to be a required status check (branch protection rule) to truly block merges?

2. **`pip install -e .` on `ubuntu-latest`** — The project depends on `lxml` (via `readability-lxml`) and `trafilatura`. Both need `libxml2-dev`/`libxslt-dev` to compile. Does `ubuntu-latest` have these pre-installed, or will the install step fail? The plan's fallback (`apt-get install`) is noted but not included in the YAML.

3. **`asyncio.run()` in the script** — Same concern as cycle 25 review: this works standalone but would fail if called from within an existing event loop. The plan says this is only for standalone use and CI. Is that clearly documented, or could someone try to import `main()` from a test?

4. **Two implementations of the same check** — The script and the pytest test check the same thing. If the check logic needs to change (e.g., checking descriptions instead of just names), both must be updated. Should the plan extract a shared helper, or is the duplication acceptable at ~5 lines of logic?

5. **Python version pinning** — The workflow pins Python 3.12. The project requires `>=3.10`. If a contributor's code works on 3.10 but the lint runs on 3.12, could import-time behavior differ? (Probably not for this simple case, but worth confirming.)

6. **No API keys needed** — The plan claims the script only imports the `mcp` object and never calls research functions. Verify: does importing `research_agent.mcp_server` trigger any side effects that require `ANTHROPIC_API_KEY` or `TAVILY_API_KEY`? (Looking at the file, imports are lazy inside tool functions, so this should be safe — but confirm.)

## Plan Quality Gate Check

Verify the plan answers these four questions adequately:

1. **What exactly is changing?** — 2 new files, exact content specified
2. **What must not change?** — Listed explicitly
3. **How will we know it worked?** — Script exits 0 locally + 938 tests pass
4. **Most likely way this plan is wrong?** — CI system deps for lxml. Is the mitigation sufficient (a comment in the plan) or should the YAML include the apt-get step proactively?

## What to Produce

Write findings to `docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md` with:

- Priority (P1/P2/P3) per CODEX-REVIEW-GATE priority order
- Whether each finding is a **blocker** (must fix before work) or **advisory** (note for work phase)
- Specific references to plan sections where relevant
- If any risks above are confirmed, note the exact impact

Focus on: Is the plan **correct enough** that a developer can execute it mechanically without making design decisions? Flag anything ambiguous, incorrect, or missing. This is the script's 5th attempt — be thorough.
