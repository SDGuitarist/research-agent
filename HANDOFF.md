# Handoff: Template-per-Context — Fix-Batched Phase Complete

## Current State

**Project:** Research Agent
**Phase:** Fix-batched complete — ready for compound
**Branch:** `main`
**Date:** February 27, 2026

---

## Prior Phase Risk

> "What might this review have missed? The template feature has been validated against exactly one input shape (PFE context file). If a second context file is added with a different structure (e.g., no `final` sections, no `context_usage`, very long descriptions), edge cases may surface."

**How addressed:** Fix 079 adds empty-sections validation, and fix 077 ensures all template field values are sanitized regardless of length or content. The "second context file" risk remains for untested structural variations, but the defensive parsing is now stronger.

---

## What Was Done This Session

### Batch 1 — P1 Fixes (commit 47aba21)
- **075:** Replaced `body if body else raw` with `body` in `_parse_template()` at 3 locations — frontmatter-only files no longer leak YAML into LLM prompts
- **076:** Changed `stripped.find("---", 3)` to `stripped.find("\n---", 3)` — embedded `---` in YAML values no longer splits on the wrong delimiter
- Added 4 new tests: frontmatter-only, empty-body, embedded separator, empty frontmatter

### Batch 2 — P2 Context Fixes (commit 1a2a6b3)
- **077:** Applied `sanitize_content()` to all template field values (headings, descriptions, context_usage, name) after YAML parsing
- **079:** Reject templates where both draft and final sections are empty — prevents mixed template/generic behavior
- **082:** Parameterized bare `list` type hint to `list[dict[str, str]]`
- Added 3 new tests: sanitized fields, empty-sections rejection, empty-draft-with-valid-final

### Batch 3 — P2 Synthesize Fixes (commit 6e0712a)
- **078:** Removed `elif context` legacy branch (18 lines) with hardcoded PFE section names. Genericized fallback context_instruction strings. No PFE-specific strings remain in synthesize.py.
- **081:** Replaced mutable `n += 1` counter with list-building + `enumerate()` in `_build_final_sections()`
- Updated 2 tests that asserted PFE section names

### Batch 4 — P2 API Fix (commit 6572949)
- **080:** Added `ContextResult`, `ContextStatus`, `ReportTemplate` to `__init__.py` imports and `__all__`
- Updated public API test

### Test Results
- 754 tests passing after all 4 batches (was 748 before, +6 new tests)
- No regressions

### Files Changed
- `research_agent/context.py` — fixes 075, 076, 077, 079, 082
- `research_agent/synthesize.py` — fixes 078, 081
- `research_agent/__init__.py` — fix 080
- `tests/test_context.py` — 7 new/updated tests
- `tests/test_synthesize.py` — 2 updated tests
- `tests/test_public_api.py` — updated __all__ assertion
- `todos/075-082` — all renamed from pending to done

---

## Three Questions

1. **Hardest fix in this batch?** Fix 078 (remove legacy PFE fallbacks) — required tracing through 3 locations in synthesize.py, identifying which tests asserted PFE-specific strings, and verifying the generic branch handles context-without-template correctly. The `elif context` branch looked load-bearing but was actually dead code with PFE assumptions.

2. **What did you consider fixing differently, and why didn't you?** For fix 077 (sanitize template fields), considered sanitizing at each consumption site in synthesize.py instead of at the parse boundary. Rejected because that's the anti-pattern documented in `non-idempotent-sanitization-double-encode.md` — sanitize once at the data boundary, not at every consumer.

3. **Least confident about going into compound phase?** The interaction between fix 075 (empty body) and fix 079 (empty sections validation). A context file with only frontmatter and no body now returns `("", template)` — but `load_full_context` calls `sanitize_content("")` which returns `""`, so `raw_content` is truthy but `content` is empty. The ContextResult will be `loaded` with empty content but a valid template. This is correct behavior for a template-only file, but it's an edge case worth documenting.

---

## Next Phase

**Compound** — Document patterns learned from these fixes in `docs/solutions/`.

### Prompt for Next Session

```
Read HANDOFF.md. Run /workflows:compound to document lessons from fix-batched todos 075-082. Key patterns: (1) sanitize-at-boundary applied to YAML template fields, (2) legacy code removal when feature supersedes it, (3) frontmatter parsing conventions (\n--- delimiter). Relevant files: research_agent/context.py, research_agent/synthesize.py, docs/solutions/. Do only compound phase — stop after writing the solutions doc.
```
