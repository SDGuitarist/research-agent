# Brainstorm: MCP Parity Lint Script (Cycle 26)

**Date:** 2026-03-08
**Status:** Complete
**Prior deferrals:** 4 (Cycles 19, 20, 22, 25)
**Promote-or-drop decision:** PROMOTE — with a concrete enforcement path this time

## Prior Phase Risk

> Cycle 25 Three Questions, "Least confident": Whether all `_parse_template` test imports should switch to the public wrapper, or just the ones that test "public behavior."

Not directly relevant to cycle 26 — that risk was resolved in cycle 25. The MCP lint script is a separate concern.

## Why We're Promoting (Not Dropping)

The cycle 25 plan-review blocker was precise: **"duplicates an existing check without a stated enforcement path."** The pytest test catches drift, but only when you run the full suite. The missing piece wasn't the script itself — it was *where and when it runs*.

This cycle promotes the lint script with a clear enforcement path: **a GitHub Actions CI check that runs on every PR.** This is the lightest-weight enforcement that actually prevents drift from reaching `main`.

Why not drop instead? The risk is real, not theoretical. The instructions string is read by LLM clients for tool discovery. A tool missing from instructions = invisible to agents. The pytest test is the backstop, but CI is the gate.

## What We're Building

A standalone lint script (`scripts/lint_mcp_parity.py`) plus a GitHub Actions workflow (`.github/workflows/mcp-lint.yml`) that runs it on every PR.

### The Script

~30 lines. Imports the `mcp` object, lists tools, checks each name appears in the instructions string. Exits 0/1. Same logic as the existing pytest test, but runnable standalone.

### The CI Workflow

~15 lines YAML. Triggers on `push` to `main` and `pull_request`. Installs the package, runs the script, fails the build if any tool is missing.

### What This Gives Us

| Layer | When | Speed | Already exists? |
|-------|------|-------|-----------------|
| CI check | Every PR | ~10s | No (new) |
| pytest test | `pytest tests/` | ~2s | Yes (keep) |
| Manual script | `python scripts/lint_mcp_parity.py` | <1s | No (new) |

Three layers, one source of truth (the `mcp` object). The pytest test stays as-is — removing it would weaken the safety net.

## Key Decisions

### 1. CI workflow, not pre-commit hook

**Why:** Pre-commit hooks require each developer to install them locally. This project has no `.pre-commit-config.yaml` and no hook infrastructure. Adding pre-commit just for one check is overhead. A GitHub Actions workflow runs automatically — zero developer setup.

**Rejected:** Pre-commit hook (requires infrastructure this project doesn't have), Makefile target only (no enforcement — same problem as cycle 25).

### 2. Separate workflow file, not a monolith

**Why:** `.github/workflows/mcp-lint.yml` is a single-purpose workflow. If CI grows later (tests, type checking, etc.), each concern gets its own workflow. Easier to reason about, easier to disable.

**Rejected:** Adding to an existing workflow (none exists), combining with test suite (lint should be fast and independent).

### 3. Script uses `asyncio.run()` to list tools

**Why:** FastMCP's `list_tools()` is async. The script wraps it in `asyncio.run()` — standard pattern for running async code from sync entry points. No event loop gymnastics.

### 4. Script checks tool names in instructions string, nothing else

**Why:** Same scope as the existing pytest test. The parity problem is: "are all tool names discoverable via the instructions string?" Not "are docstrings good?" or "are parameter schemas complete?" — those are separate concerns. YAGNI.

### 5. Keep the pytest test

**Why:** Belt and suspenders. The CI workflow catches drift in PRs. The pytest test catches it locally during development. They check the same thing via different paths. The maintenance cost of having both is near zero since the logic is identical.

## Scope Boundaries

**In scope:**
- `scripts/lint_mcp_parity.py` — standalone lint script (~30 lines)
- `.github/workflows/mcp-lint.yml` — CI workflow (~15 lines YAML)

**Out of scope:**
- Pre-commit hook configuration
- Removing the existing pytest parity test
- Changing the instructions string content
- Adding new MCP tools
- Parameter schema validation
- Docstring quality checks
- Any other CI workflows (tests, linting, type checking)

## Risk Assessment

**Very low.** The script is additive (new file). The CI workflow is additive (new file). Neither changes any existing code or behavior. If the script has a bug, the pytest test is still the backstop.

The only real risk: the CI workflow might need adjustment for Python version, package install method, or environment variables. The plan phase should specify the exact workflow YAML.

## Feed-Forward

- **Hardest decision:** Whether the enforcement path should be CI or pre-commit. CI wins because this project has no pre-commit infrastructure, and CI requires zero developer setup. If the project adds pre-commit later, the script is already there to wire in.
- **Rejected alternatives:** Dropping the lint script entirely (the risk is real — invisible tools hurt agent users), pre-commit hook (no infrastructure), Makefile-only (no enforcement), ruff custom rule (overkill for one check).
- **Least confident:** Whether the GitHub Actions workflow will work correctly on first try — Python version, dependency installation, and whether `fastmcp` tools registration happens at import time or requires explicit setup. The plan phase should verify by reading `mcp_server.py` initialization and FastMCP's tool registration mechanism.
