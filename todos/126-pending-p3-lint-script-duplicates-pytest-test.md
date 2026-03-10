---
status: resolved
priority: p3
issue_id: "126"
tags: [code-review, architecture, simplicity]
dependencies: ["122"]
unblocks: []
sub_priority: 2
---

# Lint Script Duplicates Existing Pytest Parity Test

## Problem Statement

`scripts/lint_mcp_parity.py:10-23` and `tests/test_mcp_server.py:462-470` implement the same logic (~5 lines). Two places to maintain means two places that can drift apart.

**Found by:** Code Simplicity Reviewer, Performance Oracle, Architecture Strategist

## Findings

- The duplication is intentional per the plan — the lint script serves a different purpose (standalone CI enforcement) from the pytest test (developer-facing suite)
- There is no CI workflow running pytest, so the lint script is the only CI enforcement
- Simplicity reviewer suggested replacing the lint script with `pytest tests/test_mcp_server.py::TestMcpInstructions -v` in CI
- Architecture strategist recommended extracting a shared helper only if the matching logic grows (e.g., when fixing #122)

## Proposed Solutions

### Option A: Accept duplication for now (Recommended)

The duplication is 5 lines. Extract a shared helper when fixing #122 (substring matching), which will naturally touch both implementations.

- **Effort:** None
- **Risk:** Low

### Option B: Replace lint script with pytest invocation in CI

Change CI to: `pip install -e ".[test]"` + `pytest tests/test_mcp_server.py::TestMcpInstructions -v`

- **Pros:** Removes 27-line script entirely
- **Cons:** CI now installs test deps; couples CI enforcement to test suite structure
- **Effort:** Small

## Technical Details

- **Affected files:** `scripts/lint_mcp_parity.py`, `tests/test_mcp_server.py`, `.github/workflows/mcp-lint.yml`
- **Depends on:** #122 (if matching logic changes, extract shared helper then)

## Acceptance Criteria

- [ ] Decision made: keep duplication or extract shared logic
