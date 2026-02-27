---
status: done
priority: p1
issue_id: "054"
tags: [code-review, security]
dependencies: []
---

# P1: Path traversal vulnerability in resolve_context_path()

## Problem Statement

`resolve_context_path()` in `context.py:31-52` constructs a file path by concatenating user input directly into a `Path` object without validating that the result stays within the `contexts/` directory. Two attack vectors exist:

1. **Relative traversal:** `--context ../../etc/passwd` resolves to `contexts/../../etc/passwd.md`
2. **Absolute path override:** `--context /etc/passwd` resolves to `/etc/passwd.md` because Python's `Path("a") / "/b"` returns `Path("/b")`

Security-sentinel confirmed this is exploitable: `python3 main.py --standard "test" --context ../CLAUDE` reads `CLAUDE.md` from the project root and injects its contents into LLM prompts.

## Findings

- Flagged by: security-sentinel (HIGH, confirmed exploitable), kieran-python-reviewer (LOW)
- The `.md` suffix requirement limits scope to markdown files, but any `.md` file on the filesystem is readable
- Content is sent to the Anthropic API, potentially transmitting sensitive information to a third party
- The function only checks `path.exists()`, not containment within `contexts/`

## Proposed Solutions

### Option A: Input validation + path containment check (Recommended)
Reject names with path separators, then verify the resolved path is under `contexts/`.
```python
def resolve_context_path(name: str) -> Path | None:
    if name.lower() == "none":
        return None
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"Invalid context name: {name!r} (must be a simple name, not a path)")
    path = (CONTEXTS_DIR / f"{name}.md").resolve()
    contexts_resolved = CONTEXTS_DIR.resolve()
    if not str(path).startswith(str(contexts_resolved) + "/"):
        raise ValueError(f"Context name {name!r} resolves outside contexts/ directory")
    if not path.exists():
        available = sorted(p.stem for p in CONTEXTS_DIR.glob("*.md")) if CONTEXTS_DIR.is_dir() else []
        hint = f" Available: {', '.join(available)}" if available else ""
        raise FileNotFoundError(f"Context file not found: {path}{hint}")
    return path
```
- Pros: Defense in depth — both input validation and output validation
- Cons: None significant
- Effort: Small (10 lines)
- Risk: Low

### Option B: Simple regex validation only
```python
if not re.match(r'^[a-zA-Z0-9_-]+$', name):
    raise ValueError(f"Invalid context name: {name!r}")
```
- Pros: Simplest
- Cons: No containment check — defense relies entirely on input validation
- Effort: Small (3 lines)
- Risk: Low

## Recommended Action

Option A — both input validation and containment check. Add tests for path traversal attempts.

## Technical Details

- **Affected files:** `research_agent/context.py`, `tests/test_context.py`
- **Components:** CLI input handling, file resolution

## Acceptance Criteria

- [ ] `--context ../CLAUDE` raises ValueError, not FileNotFoundError
- [ ] `--context /etc/passwd` raises ValueError
- [ ] `--context pfe` still works normally
- [ ] `--context none` still returns None
- [ ] Tests cover path traversal attempts (relative and absolute)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Security-sentinel confirmed exploitable |

## Resources

- Security review finding #1
- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
