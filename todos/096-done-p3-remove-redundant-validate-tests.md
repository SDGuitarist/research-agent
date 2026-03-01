---
status: done
priority: p3
issue_id: "096"
tags: [code-review, testing, simplification]
dependencies: []
unblocks: []
sub_priority: 1
---

# Remove Redundant TestValidateReportFilename Test Class

## Problem Statement

`TestValidateReportFilename` (7 unit tests, 43 lines) directly tests the private `_validate_report_filename` function. Five of these tests duplicate integration tests in `TestGetReport` that already cover the same validation paths through the full MCP tool. The integration tests are more valuable because they test the complete `ToolError` wrapping.

## Findings

- **Source:** code-simplicity-reviewer
- **File:** `tests/test_mcp_server.py`, lines 344-386
- **Overlap:** 5 of 7 unit tests duplicate `TestGetReport` integration tests

## Proposed Solutions

### Option A: Delete the class, add 1 test to TestGetReport (Recommended)
- Remove `TestValidateReportFilename` entirely (43 lines)
- Add `test_long_filename_rejected` to `TestGetReport` (the only unique case)
- **Effort:** Small
- **Risk:** None — integration tests already cover the paths

## Acceptance Criteria

- [ ] `TestValidateReportFilename` class removed
- [ ] Long filename test migrated to `TestGetReport`
- [ ] No coverage regression

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from code-simplicity-reviewer | 43 LOC removable |
