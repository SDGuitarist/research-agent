---
title: "Non-Idempotent Sanitization Causes Double-Encoding Bug"
date: 2026-02-23
category: security
tags: [sanitization, prompt-injection, xml-encoding, idempotency, data-corruption]
module: sanitize.py, synthesize.py, relevance.py, decompose.py, context.py
symptoms: "&amp;amp; appearing in LLM prompts instead of &amp;; subtle data corruption in reports containing ampersands"
severity: medium
summary: "sanitize_content() is non-idempotent: calling it twice on the same string double-encodes ampersands (& → &amp; → &amp;amp;). The correct pattern is sanitize-once-at-boundary, not defense-in-depth."
---

# Non-Idempotent Sanitization Causes Double-Encoding Bug

## Problem

After extracting `sanitize_content()` into a shared module (`sanitize.py`), multiple
modules called it independently — both at the data source and at the consumption site.
This seemed like defense-in-depth but was actually a bug.

### Why `sanitize_content` is Non-Idempotent

```python
def sanitize_content(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

The `&` → `&amp;` replacement is non-idempotent:

| Call | Input | Output |
|------|-------|--------|
| 1st | `AT&T revenue` | `AT&amp;T revenue` |
| 2nd | `AT&amp;T revenue` | `AT&amp;amp;T revenue` |
| 3rd | `AT&amp;amp;T revenue` | `AT&amp;amp;amp;T revenue` |

Each additional call corrupts the data further. Any string containing `&` gets
progressively mangled.

### Where It Happened

The `critique_guidance` data flow had double-sanitization:

```
context.py: _summarize_patterns() → sanitize_content(summary)  # 1st call
    ↓
agent.py: passes critique_context to three modules
    ↓
synthesize.py line 413: sanitize_content(critique_guidance)     # 2nd call (BUG)
synthesize.py line 497: sanitize_content(critique_guidance)     # 2nd call (BUG)
```

`decompose.py` and `relevance.py` had the same pattern but were fixed in commit
`8420227`. `synthesize.py` was missed until the 9-agent review caught it.

## Root Cause

**No documented sanitization contract.** Each module independently decided to
sanitize its inputs "just in case," not knowing whether the caller had already
sanitized. The function name `sanitize_content` suggests it's safe to call anytime —
but it's not.

## Solution

### Pattern: Sanitize Once at the Data Boundary

Sanitize where untrusted data first enters the system. Downstream modules trust
that the data arrives pre-sanitized.

**Data boundaries in this codebase:**

| Data source | Sanitization site | Consumers |
|---|---|---|
| Web content (fetch/extract) | `summarize.py`, `relevance.py` | synthesize, skeptic |
| Business context file | `context.py: load_context()` | decompose, synthesize |
| Critique YAML files | `context.py: _summarize_patterns()` | decompose, relevance, synthesize |
| User query (CLI input) | `relevance.py: evaluate_sources()` | score_source |

**Documentation pattern:** At each consumption site, add a comment naming the
sanitization source:

```python
# critique_guidance is pre-sanitized by load_critique_history
```

### What Was Changed

1. **Removed** `sanitize_content()` calls on `critique_guidance` in `synthesize.py`
   (lines 413, 497) — same fix previously applied to `decompose.py` and `relevance.py`
2. **Fixed** incorrect comment in `relevance.py:122`: referenced nonexistent function
   `score_and_filter_sources`, corrected to `evaluate_sources`
3. **Added** pre-sanitization contract comments in `decompose.py` and `relevance.py`
4. **Updated** `score_source` docstring to document the pre-sanitized query precondition

### Known Remaining Call: `synthesize.py:450`

`safe_findings = sanitize_content(formatted)` sanitizes skeptic findings (LLM output)
before re-injecting into the final synthesis prompt. This is **not** a double-encode
bug — the skeptic findings are LLM-generated text that hasn't been previously
sanitized. However, the skeptic module (`skeptic.py:58`) already sanitizes its own
web inputs, so if the LLM echoes those inputs, the output could contain
already-encoded entities. This is a low-risk edge case — noting it for future review.

### Commits

- `8420227` — Removed redundant sanitize calls in decompose and relevance
- `fa4daaf` — Fixed contracts, removed double-sanitize in synthesize

## Prevention

### Rules for Future Development

1. **Never call `sanitize_content()` without checking the data flow.** Trace the value
   back to its source. If it passes through `context.py` or another sanitization
   boundary, it's already clean.

2. **When adding a new data source,** sanitize at the point of ingestion — not at
   every consumption site.

3. **When passing sanitized data through a function,** add a comment:
   `# [param] is pre-sanitized by [source function]`

4. **When writing sanitization functions,** consider idempotency. If the function
   can't be safely called twice, document this prominently.

### Future Consideration

Comments documenting pre-sanitization contracts can drift as code evolves.
A stronger approach would be a type wrapper (e.g., `SanitizedStr`) that makes the
contract compiler-checkable. This is not needed at current codebase size but worth
considering if the sanitization boundary grows more complex.

## Cross-References

- [SSRF Bypass via Proxy Services](ssrf-bypass-via-proxy-services.md) — related
  security boundary issue in cascade fallback
- [Domain Matching Substring Bypass](domain-matching-substring-bypass.md) — another
  security boundary gap found in code review
- `docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md` — 9-agent review that caught
  the remaining double-sanitization
- `docs/plans/2026-02-23-p3-do-now-fixes-plan.md` — sanitization data-flow analysis

## Three Questions

1. **Hardest pattern to extract from the fixes?** Articulating why defense-in-depth
   is the *wrong* instinct here. Normally "sanitize twice for safety" sounds
   reasonable. The insight is that idempotency is a prerequisite for defense-in-depth —
   without it, the "extra safety" layer actively corrupts data.

2. **What did you consider documenting but left out, and why?** A full inventory of
   every `sanitize_content()` call site and whether each is a boundary or consumption
   site. Left it out because it would go stale immediately — the "trace the data flow"
   rule is more durable than a static list.

3. **What might future sessions miss that this solution doesn't cover?** The `<` and
   `>` replacements in `sanitize_content` ARE idempotent (`<` → `&lt;` — the `<` is
   gone, so a second call has nothing to re-encode). Only `&` causes the cascade. A
   future developer might see this doc and incorrectly conclude that ALL XML escaping
   is non-idempotent, when really it's just `&`. But the rule "sanitize once" is
   correct regardless, so this nuance shouldn't cause harm.
