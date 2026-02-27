---
status: done
priority: p2
issue_id: "057"
tags: [code-review, security]
dependencies: []
---

# P2: Unsanitized query and file previews in auto-detect LLM prompt

## Problem Statement

`auto_detect_context()` in `context.py:147-155` sends the user query and context file previews to the LLM without sanitization or XML boundary protection. The rest of the codebase uses `sanitize_content()` and XML tags (`<query>`, `<sources>`) consistently — this is the only LLM prompt that doesn't.

## Findings

- Flagged by: security-sentinel (MEDIUM)
- Learnings-researcher found docs/solutions/security/non-idempotent-sanitization-double-encode.md — confirms sanitize-once-at-boundary pattern
- The LLM response is validated against a known allowlist of context names, limiting exploitation impact
- A crafted query or malicious context file could theoretically manipulate which context is selected

## Proposed Solutions

### Option A: Sanitize inputs and add XML boundaries (Recommended)
```python
safe_query = sanitize_content(query)
# In options building:
safe_preview = sanitize_content(preview)
options.append(f"{i}. {name}\n{safe_preview}")

prompt = (
    f"Given this research query:\n\n"
    f"  <query>{safe_query}</query>\n\n"
    f"Which of these context files (if any) is relevant? ..."
)
```
- Pros: Consistent with rest of codebase, follows established patterns
- Cons: None
- Effort: Small (~5 lines)
- Risk: Low

## Recommended Action

Option A.

## Technical Details

- **Affected files:** `research_agent/context.py`, `tests/test_context.py`

## Acceptance Criteria

- [ ] Query passed through `sanitize_content()` before prompt construction
- [ ] File previews passed through `sanitize_content()` before prompt construction
- [ ] XML `<query>` tag wraps the query in the prompt
- [ ] Test with query containing `<script>` tags verifies sanitization

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | Matches existing sanitization patterns in codebase |
