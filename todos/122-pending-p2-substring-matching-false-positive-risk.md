---
status: resolved
priority: p2
issue_id: "122"
tags: [code-review, architecture, correctness]
dependencies: []
unblocks: []
sub_priority: 4
---

# Substring Matching in Lint Script Can False-Positive on Short Tool Names

## Problem Statement

`scripts/lint_mcp_parity.py:15` uses `name not in instructions` — a Python substring check. A tool named `list` or `report` would pass because those substrings already appear in the instructions string. The same logic exists in `tests/test_mcp_server.py:466`.

**Found by:** Security Sentinel, Architecture Strategist, Agent-Native Reviewer
**Known Pattern:** `docs/solutions/security/domain-matching-substring-bypass.md` documents the same structural risk for domain matching

## Findings

- Current 7 tool names are long and distinctive — no false positive today
- Future tool names like `research`, `report`, or `list` would silently pass
- Both the lint script and the pytest test share this weakness
- The learnings researcher confirmed this matches the domain-matching substring bypass pattern from Cycle 24

## Proposed Solutions

### Option A: Word-boundary regex matching (Recommended)

```python
import re
missing = [name for name in tool_names if not re.search(rf'\b{re.escape(name)}\b', instructions)]
```

Apply to both `scripts/lint_mcp_parity.py` and `tests/test_mcp_server.py`.

- **Pros:** Prevents false positives, minimal code change
- **Cons:** `\b` treats `_` as a word character, so `run_research` matches as one token (correct behavior)
- **Effort:** Small
- **Risk:** Low

### Option B: Defer until tool surface grows

- **Pros:** No change needed now
- **Cons:** Latent risk remains; must remember to revisit
- **Effort:** None
- **Risk:** Low (current names are safe)

## Technical Details

- **Affected files:** `scripts/lint_mcp_parity.py`, `tests/test_mcp_server.py`

## Acceptance Criteria

- [ ] Lint script uses word-boundary or token-based matching
- [ ] Pytest parity test uses the same matching logic
- [ ] All 7 current tools still pass
- [ ] A hypothetical short name like `list` would be caught as missing
