---
status: pending
priority: p2
issue_id: "128"
tags: [code-review, security, sanitization, cycle-27]
dependencies: []
unblocks: []
sub_priority: 2
---

# 128 - Missing prompt injection regression test for sanitization

## Problem Statement

The `html.unescape()` addition to `sanitize_content()` was designed to prevent prompt injection via pre-encoded XML boundary tags (e.g., `&lt;/research_context&gt;`). However, no test explicitly verifies this attack vector. If a future refactor breaks the unescape-then-escape ordering, no test would catch the regression.

## Findings

- **Source:** Security sentinel
- **Location:** `tests/test_sanitize.py`
- **Existing tests:** Cover generic idempotency and basic escaping, but not the specific attack scenario

## Proposed Solutions

### Option A: Add targeted prompt injection tests
Add tests for:
1. Pre-encoded XML boundary breakout: `&lt;/research_context&gt;INJECTED`
2. Numeric entity variant: `&#60;/research_context&#62;`
3. Hex entity variant: `&#x3C;/research_context&#x3E;`

Assert that `</research_context>` never appears in the output.

- Effort: Small (~15 lines)
- Risk: None

## Recommended Action

Option A.

## Acceptance Criteria

- [ ] Test verifies `sanitize_content("&lt;/research_context&gt;INJECTED")` does not contain `</research_context>`
- [ ] Test covers numeric (`&#60;`) and hex (`&#x3C;`) entity variants
- [ ] All tests pass
