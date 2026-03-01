---
status: done
priority: p2
issue_id: "094"
tags: [code-review, agent-native]
dependencies: []
unblocks: ["095"]
sub_priority: 5
---

# Missing critique_report MCP Tool

## Problem Statement

The CLI supports `--critique REPORT` to evaluate report quality (scores, weaknesses, suggestions), but there is no MCP equivalent. An agent cannot complete the research feedback loop: run research → review report → critique it → re-run if quality is low. The public API already exports `critique_report_file` in `__all__`.

## Findings

- **Source:** agent-native-reviewer
- **CLI location:** `research_agent/cli.py:211-228`
- **Public API:** `research_agent.critique_report_file` (already exported)
- **Impact:** Agent-native parity gap — critique workflow unreachable via MCP

## Proposed Solutions

### Option A: Add critique_report tool (Recommended)
```python
@mcp.tool
def critique_report(filename: str) -> str:
    """Evaluate quality of a saved report. Returns scores, weaknesses, suggestions."""
    from fastmcp.exceptions import ToolError
    from research_agent import critique_report_file

    try:
        path = _validate_report_filename(filename)
    except (ValueError, FileNotFoundError) as e:
        raise ToolError(str(e))

    result = critique_report_file(path, model="claude-sonnet-4-20250514")
    return f"Scores: {result.mean_score:.1f}/5\n{result.weaknesses}\n{result.suggestions}"
```
- **Effort:** Medium (new tool + tests)
- **Risk:** Low — wraps existing public API

### Option B: Defer to a future cycle
- Document the gap and add to backlog
- **Effort:** None
- **Risk:** Agents cannot use critique workflow

## Acceptance Criteria

- [ ] `critique_report` tool callable via MCP
- [ ] Returns scores, weaknesses, and suggestions
- [ ] Path validation matches `get_report` security checks
- [ ] Tests cover happy path and error paths

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from agent-native-reviewer | Largest agent-parity gap |
