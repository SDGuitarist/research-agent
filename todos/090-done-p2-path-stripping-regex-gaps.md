---
status: done
priority: p2
issue_id: "090"
tags: [code-review, security]
dependencies: []
unblocks: []
sub_priority: 1
---

# Path-Stripping Regex Misses Common OS Paths

## Problem Statement

The regex for stripping filesystem paths from `ResearchError` messages only matches `/Users/` and `/home/` prefixes. Paths from Linux servers (`/opt/`, `/var/`, `/srv/`, `/tmp/`), containers (`/app/`, `/workspace/`), and CI environments would pass through unredacted, leaking server filesystem structure to MCP clients.

## Findings

- **Source:** security-sentinel review
- **File:** `research_agent/mcp_server.py`, line 63
- **Evidence:** `re.sub(r'(/Users/|/home/)\S+', '<path>', str(e))`
- **Impact:** Information leakage aids exploitation of unauthenticated HTTP transport (089)

## Proposed Solutions

### Option A: Broader Unix path regex (Recommended)
```python
msg = re.sub(r'/(?:[\w.-]+/)+[\w.-]+', '<path>', str(e))
```
- **Pros:** Catches any multi-segment Unix absolute path
- **Cons:** Could over-match URLs or intentional path-like strings in error messages
- **Effort:** Small (1 line)
- **Risk:** Low — test with existing error messages

### Option B: Strip all absolute paths
```python
msg = re.sub(r'/\S+', '<path>', str(e))
```
- **Pros:** Maximum coverage
- **Cons:** Would strip URLs too (e.g., API endpoint paths in errors)
- **Effort:** Small
- **Risk:** Medium — may over-strip

## Acceptance Criteria

- [ ] Paths starting with `/opt/`, `/var/`, `/tmp/`, `/app/` are redacted
- [ ] Test with error messages containing non-standard paths
- [ ] URLs in error messages are not accidentally stripped

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-28 | Created from security-sentinel review | |

## Resources

- File: `research_agent/mcp_server.py:63`
