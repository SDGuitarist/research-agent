---
status: done
priority: p2
issue_id: "059"
tags: [code-review, quality]
dependencies: []
---

# P2: No integration tests for auto-detect in agent._research_async

## Problem Statement

The agent integration tests in `test_agent.py` mock `CONTEXTS_DIR.is_dir()` to return `False`, which disables the auto-detect code path entirely. Unit tests exist for `auto_detect_context()` in `test_context.py`, but there is no test that exercises the full integration: agent calls auto-detect → sets context_path → uses it in subsequent pipeline stages.

## Findings

- Flagged by: kieran-python-reviewer (MEDIUM)
- The auto-detect block at `agent.py:231-241` is untested in the agent context
- No test verifies `self.context_path` is set correctly after auto-detection
- No test verifies `self.no_context = True` when auto-detect returns None

## Proposed Solutions

### Option A: Add agent-level auto-detect tests (Recommended)
```python
async def test_auto_detect_sets_context_path_when_matched(self):
    """When auto-detect finds a match, agent.context_path should be set."""
    with patch("research_agent.agent.CONTEXTS_DIR") as mock_dir, \
         patch("research_agent.agent.auto_detect_context") as mock_detect:
        mock_dir.is_dir.return_value = True
        mock_detect.return_value = Path("contexts/pfe.md")
        # ... run agent, verify context_path was set ...

async def test_auto_detect_sets_no_context_when_none_matched(self):
    """When auto-detect returns None, agent.no_context should be True."""
    ...
```
- Pros: Closes the integration test gap
- Cons: Requires careful mocking of the full pipeline
- Effort: Medium (2-3 new test methods)
- Risk: Low

## Recommended Action

Option A.

## Technical Details

- **Affected files:** `tests/test_agent.py`

## Acceptance Criteria

- [ ] Test that auto-detect sets context_path when a match is found
- [ ] Test that auto-detect sets no_context=True when no match found
- [ ] Test that auto-detect is skipped when context_path is already set
- [ ] Test that auto-detect is skipped when no_context=True

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Unit tests exist but integration gap identified |
