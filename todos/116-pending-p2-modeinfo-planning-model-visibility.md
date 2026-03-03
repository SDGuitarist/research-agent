---
status: done
priority: p2
issue_id: "116"
tags: [code-review, agent-native, parity]
dependencies: []
unblocks: ["118"]
sub_priority: 1
---

# 116: Add planning_model to ModeInfo for agent visibility

## Problem Statement

The `list_research_modes` MCP tool returns `ModeInfo` objects that include `name`, `max_sources`, `word_target`, `cost_estimate`, and `auto_save` — but not `model` or `planning_model`. An agent calling `list_research_modes` has no idea that tiered model routing exists or which model handles planning tasks. This is a context parity gap: a developer reading `modes.py` can see these values, but an agent querying the MCP tool cannot.

**Why it matters:** Agent-native parity principle — agents should have the same visibility into system configuration as developers.

## Findings

- **Source:** Agent-native reviewer (Warning 1)
- **Evidence:** `ModeInfo` at `research_agent/results.py:37` has 5 fields; `ResearchMode` has 17. The gap is widening with each cycle.
- **Known Pattern:** Cycle 19 solution `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md` established the parity discipline. This finding extends it.

## Proposed Solutions

### Option A: Add model + planning_model to ModeInfo (Recommended)
Add two string fields to `ModeInfo` and populate them in `list_modes()`:

```python
# results.py
@dataclass(frozen=True)
class ModeInfo:
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
    model: str = ""
    planning_model: str = ""
```

```python
# __init__.py list_modes()
ModeInfo(
    ...,
    model=m.model,
    planning_model=m.planning_model,
)
```

- **Pros:** Simple, direct, follows existing pattern
- **Cons:** Adds 2 more fields to manually sync
- **Effort:** Small (15 min)
- **Risk:** Very low

### Option B: Add a to_mode_info() method on ResearchMode
Generate `ModeInfo` from `ResearchMode` to prevent future drift.

- **Pros:** Prevents ModeInfo from falling further behind
- **Cons:** Larger refactor, changes the construction pattern
- **Effort:** Medium (30 min)
- **Risk:** Low

## Recommended Action

_To be filled during triage_

## Technical Details

**Affected files:**
- `research_agent/results.py` — add 2 fields to `ModeInfo`
- `research_agent/__init__.py` — update `list_modes()` mapping
- `tests/test_mcp.py` or equivalent — verify fields appear in output

## Acceptance Criteria

- [ ] `list_research_modes` MCP tool output includes `model` and `planning_model` for each mode
- [ ] Values match what's configured in `ResearchMode` factories
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-03-03 | Created from Cycle 21 review | ModeInfo has 5/17 fields — drift is a pattern |

## Resources

- Commit: 435dd2e
- Agent-native reviewer Warning 1
- Cycle 19 parity solution: `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md`
