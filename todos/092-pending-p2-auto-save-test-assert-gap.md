---
status: pending
priority: p2
issue_id: "092"
tags: [code-review, testing]
dependencies: []
unblocks: []
sub_priority: 3
---

# Auto-Save Test Doesn't Assert atomic_write Was Called

## Problem Statement

The `test_auto_saves_standard_mode` test patches `atomic_write` but never asserts it was called with the correct arguments. This was the feed-forward risk from Session 3: "Whether test coverage is sufficient for the auto-save path." The test only verifies the metadata string contains the filename, not that the write actually happened.

## Findings

- **Source:** kieran-python-reviewer, feed-forward risk from work phase
- **File:** `tests/test_mcp_server.py`, line 65-86
- **Evidence:** `patch("research_agent.safe_io.atomic_write")` with no `assert_called_once_with`

## Proposed Solutions

### Option A: Add mock assertion (Recommended)
```python
with patch("research_agent.report_store.get_auto_save_path", return_value=save_path) as mock_path, \
     patch("research_agent.safe_io.atomic_write") as mock_write:
    result = await client.call_tool(...)

mock_write.assert_called_once_with(save_path, "# Saved Report")
```
- **Effort:** Small (2 lines changed)
- **Risk:** None

## Acceptance Criteria

- [ ] Test asserts `atomic_write` was called with correct path and content
- [ ] Feed-forward risk from Session 3 is resolved

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from review — closes feed-forward gap | |
