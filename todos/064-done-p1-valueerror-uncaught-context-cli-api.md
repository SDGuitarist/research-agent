---
status: done
priority: p1
issue_id: "064"
tags: [code-review, error-handling]
dependencies: []
---

# P1: ValueError from resolve_context_path uncaught in CLI and public API

## Problem Statement

`resolve_context_path()` raises `ValueError` for path traversal attempts (names with `/`, `\`, or leading `.`), but neither the CLI nor the public API catch it. Users get an unhandled Python traceback, and API consumers get an unexpected exception type.

## Findings

- Flagged by: kieran-python-reviewer (P1), agent-native-reviewer (P2)
- Two locations: `cli.py:311-318` and `__init__.py:99-102`
- The path traversal defense itself works correctly — this is purely an error handling gap

## Fix

**CLI (`cli.py:311-318`):**
```python
except (FileNotFoundError, ValueError) as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

**Public API (`__init__.py:99-102`):**
```python
try:
    context_path = resolve_context_path(context)
except (FileNotFoundError, ValueError) as e:
    raise ResearchError(str(e)) from e
```

## Acceptance Criteria

- [ ] `--context ../evil` produces clean error message, not traceback
- [ ] `run_research(context="../evil")` raises `ResearchError`, not `ValueError`
- [ ] Tests cover both paths

## Technical Details

- **Affected files:** `research_agent/cli.py`, `research_agent/__init__.py`, tests
- **Effort:** Small (~10 lines)
