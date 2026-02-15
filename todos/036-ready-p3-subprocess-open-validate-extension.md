---
status: ready
priority: p3
issue_id: "036"
tags: [code-review, security]
dependencies: []
---

# subprocess.run("open") Without Extension Validation

## Problem Statement

`main.py:277` calls `subprocess.run(["open", path])` to open saved reports. The path should be validated to ensure it ends with `.md` to prevent opening unexpected file types.

## Findings

- **Source:** Security Sentinel agent
- **Location:** `main.py:277`

## Proposed Solutions

### Option A: Validate .md extension before open (Recommended)
```python
if not path.endswith(".md"):
    raise ValueError("Can only open .md files")
```
- **Effort:** Small (10 min)

## Acceptance Criteria

- [ ] Only `.md` files can be opened via subprocess
- [ ] Test: non-.md path is rejected
