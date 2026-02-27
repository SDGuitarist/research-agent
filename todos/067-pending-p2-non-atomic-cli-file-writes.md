---
status: done
priority: p2
issue_id: "067"
tags: [code-review, data-integrity]
dependencies: []
---

# P2: Non-atomic file writes in CLI output path

## Problem Statement

The CLI saves reports with `Path.write_text()` at `cli.py:350`, which is not atomic. If the process crashes mid-write, the report file is partially written. The codebase already has `safe_io.atomic_write()` for this purpose.

## Findings

- Flagged by: data-integrity-guardian (P2)
- Background agents writing via `-o` are particularly vulnerable
- A partial file passes the queue skill's existence check → marked Completed with corrupted report

## Fix

```python
from research_agent.safe_io import atomic_write
atomic_write(output_path, report)
```

## Acceptance Criteria

- [ ] CLI uses `atomic_write` for report output
- [ ] Interrupted write leaves no partial file on disk

## Technical Details

- **Affected files:** `research_agent/cli.py`
- **Effort:** Small (2 lines)
