---
status: complete
priority: p2
issue_id: "102"
tags: [code-review, security, prompt-injection]
dependencies: []
unblocks: []
sub_priority: 1
---

# Unsanitized headings injected into LLM prompts

## Problem Statement

Section headings are extracted from the report and injected directly into LLM prompts without passing through `sanitize_content()`. While the report is LLM output (not raw web content), a sophisticated attacker could craft web content that, after synthesis, produces headings containing prompt injection payloads.

## Findings

- **security-sentinel**: MEDIUM — defense-in-depth gap in three-layer pattern
- **learnings-researcher**: Confirmed — `non-idempotent-sanitization-double-encode.md` recommends sanitizing at consumption boundary

**Locations:**
- `research_agent/iterate.py:176-180` — headings extracted from unsanitized `report`, joined at line 181, injected at line 199
- `research_agent/agent.py:242-245` — headings extracted for `synthesize_mini_report()` without sanitization

## Proposed Solutions

### Option A: Sanitize headings after extraction (Recommended)
Apply `sanitize_content()` to each heading string after extraction.

```python
headings = [
    sanitize_content(line.lstrip("#").strip())
    for line in report.splitlines()
    if line.startswith("## ")
]
```

- **Pros:** Consistent with three-layer defense, minimal code change
- **Cons:** Slight overhead (negligible — list of ~5-10 short strings)
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria

- [ ] Headings sanitized in `iterate.py:generate_followup_questions()`
- [ ] Headings sanitized in `agent.py:_run_iteration()`
- [ ] Tests verify sanitized headings in prompts
