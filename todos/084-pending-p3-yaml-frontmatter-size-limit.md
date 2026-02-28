---
status: pending
priority: p3
issue_id: "084"
tags: [code-review, security, defense-in-depth]
dependencies: []
unblocks: []
sub_priority: 2
---

# P3: Optional YAML frontmatter size limit

## Problem Statement

`_parse_template()` parses YAML frontmatter without a size limit. While `yaml.safe_load()` prevents code execution, extremely large frontmatter (YAML billion-laughs via anchors/aliases) could cause CPU/memory spikes.

## Findings

- Flagged by: security-sentinel (Finding 2, Low severity)
- Context files are local author-controlled files — risk is very low
- This is optional defense-in-depth hardening

## Proposed Solutions

### Option A: Add size check before `yaml.safe_load()`

```python
MAX_YAML_FRONTMATTER_BYTES = 8192  # 8 KB
if len(yaml_block) > MAX_YAML_FRONTMATTER_BYTES:
    logger.warning("YAML frontmatter exceeds size limit (%d bytes)", len(yaml_block))
    return (raw, None)
```

- **Effort:** Small (3 lines)
- **Risk:** None — 8 KB is generous for template metadata

## Technical Details

**Affected files:**
- `research_agent/context.py` — `_parse_template()` (add size check before line 64)

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-27 | Created from code review | Flagged by Security Sentinel |
