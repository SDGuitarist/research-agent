---
title: "MCP parity lint script with CI enforcement after 4 deferrals"
date: 2026-03-10
category: workflow
tags:
  - mcp
  - ci
  - lint
  - fastmcp
  - github-actions
  - deferred-debt
  - tool-discovery
cycle: 26
severity: medium
component:
  - scripts/lint_mcp_parity.py
  - .github/workflows/mcp-lint.yml
  - research_agent/mcp_server.py
  - tests/test_mcp_server.py
problem_type: "missing-automated-enforcement"
resolution_time: "~3 days (2026-03-08 brainstorm to 2026-03-10 final merge)"
---

# MCP Parity Lint — CI Enforcement

## Problem

The MCP server exposes tools via `@mcp.tool` decorators and has a hand-written `instructions` string that tells AI agents what tools are available. There was no automated enforcement that these stayed in sync — a developer could add a new tool and forget to mention it in the instructions. The tool becomes invisible to agents.

This gap was identified in Cycle 19 and deferred **four consecutive times** (cycles 19, 20, 22, 25) because it was always bundled with other work and dropped as the "least ready" item.

## Root Cause

1. **No CI enforcement path.** The existing pytest test covered tool-instruction parity but only ran locally — nothing blocked a merge with missing tool names.
2. **Substring matching.** Both the test and the eventual lint script used `name not in instructions` — a Python substring check. Tool names like `list` or `report` would false-positive because those substrings appear in the prose. Same structural pattern as the domain-matching substring bypass (Cycle 24).
3. **Deferred item decay.** Without a forcing function, the lint script lost priority each cycle. By deferral #4, it needed an explicit promote-or-drop decision to break the pattern.

## Solution

### 1. Standalone lint script (`scripts/lint_mcp_parity.py`)

```python
def find_missing_tools(tool_names: list[str], instructions: str) -> list[str]:
    """Return tool names not mentioned as whole words in the instructions."""
    return [
        name for name in tool_names
        if not re.search(rf"\b{re.escape(name)}\b", instructions)
    ]
```

Imports the live `mcp` FastMCP instance, calls `asyncio.run(mcp.list_tools())` to get all registered tools, checks each name with word-boundary regex. Exits 1 if any are missing.

### 2. CI workflow (`.github/workflows/mcp-lint.yml`)

Runs on every push to `main` and every PR. Security hardened:
- `permissions: contents: read` (least privilege)
- Actions pinned to full commit SHAs with version comments
- `cache: 'pip'` for 20-40s savings per run
- Python 3.12 pinned with comment explaining the choice

### 3. Generalized pytest test (`tests/test_mcp_server.py`)

Updated `test_all_tools_mentioned_in_instructions` to use the same word-boundary regex, replacing the substring check.

### 4. MCP instructions workflow guidance

Added: `"Typical workflow: list_research_modes -> run_research -> critique_report -> generate_followups."` — agents now know the recommended tool sequence, not just individual tool descriptions.

## Risk Resolution

**Flagged risk (brainstorm):** "Whether the GitHub Actions workflow will work correctly — Python version, dependency installation, and whether fastmcp tools register at import time."

**Plan verification:** Confirmed locally that `@mcp.tool` decorators register at import time — no server startup needed. `pip install -e .` chosen to match local dev workflow.

**What actually happened:** CI passed on first run (PR #7, 30 seconds). The `pip install -e .` step worked on `ubuntu-latest` without additional system packages. The unverified risk was a non-issue.

**Lesson:** Import-time registration is a FastMCP design guarantee. Document framework behavior assumptions in plans so they don't block future cycles.

## Verification

- 938 tests passing after all changes
- Lint script exits 0 with all 7 current tool names
- CI workflow passed on PR #6 (feature) and PR #7 (review fixes)
- FastMCP pinned to `>=3.0,<3.1` per review blocker (commit `5fa7ea0`)

## Prevention Strategies

**Substring matching is always wrong for identity checks.** Whether matching domains or tool names, use boundary-aware matching from day one. Rule: any PR using `in` or `endswith` for identity matching should be flagged in review.

**Every enforcement mechanism ships with its feature.** The lint script was the enforcement for MCP parity and it was split from the feature work 4 times. If you add a feature requiring ongoing consistency, the check that enforces it ships in the same PR.

**Promote-or-drop at deferral #2.** Any todo deferred twice gets a mandatory agenda item: promote to blocker or drop with a written rationale. No third deferral allowed.

## CI Hardening Checklist

For any new GitHub Actions workflow:

- [ ] `permissions:` block with least privilege
- [ ] Actions pinned to full SHA hashes, not mutable tags
- [ ] Dependency caching enabled
- [ ] `timeout-minutes` set on every job
- [ ] Python/runtime version matches project or is documented
- [ ] Boundary-aware matching for any string identity checks

## Cross-References

- `docs/solutions/security/domain-matching-substring-bypass.md` — same structural pattern, different context
- `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md` — Cycle 19 origin of MCP parity concept
- `docs/solutions/architecture/housekeeping-batch-and-structured-observability.md` — Cycle 22, noted "MCP instructions string is manually maintained"
- `docs/solutions/architecture/public-wrapper-for-cross-module-access.md` — Cycle 25, deferred-item-decay lesson triggered Cycle 26
- PR #6: `feat/26-mcp-parity-lint` (feature work)
- PR #7: `fix/26-review-todos` (review fixes)

## Three Questions

1. **Hardest pattern to extract from the fixes?** Whether the "promote-or-drop at deferral #2" rule is a real process improvement or just hindsight. The 4-deferral pattern is clear, but the rule assumes someone notices deferral count — which requires tracking in MEMORY.md or todo frontmatter. Chose to document it as a rule and rely on MEMORY.md tracking.
2. **What did you consider documenting but left out, and why?** The full CI hardening checklist could be its own standalone doc. Left it inline here because the project has one workflow — extracting a separate doc is premature until a second workflow is added.
3. **What might future sessions miss that this solution doesn't cover?** The deferred `--cost` and `--critique-history` MCP tools (todo #123). They're pre-existing gaps, not regressions, but they're now at deferral #1. If they hit deferral #2, the promote-or-drop rule applies.
