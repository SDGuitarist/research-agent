---
title: "Defensive YAML Frontmatter Parsing — Sanitization, Validation, and Legacy Cleanup"
date: 2026-02-27
category: logic-errors
tags: [yaml-parsing, frontmatter, sanitize-at-boundary, prompt-injection-defense, legacy-cleanup, type-safety]
module: research_agent/context.py, research_agent/synthesize.py, research_agent/__init__.py
symptoms:
  - "Raw YAML leaked into LLM prompts when context files had no body after frontmatter"
  - "Embedded `---` in YAML values split the template at the wrong position"
  - "Unsanitized template field values could inject content into synthesis prompts"
  - "Hardcoded PFE section names persisted after template system superseded them"
  - "Templates with empty section lists silently produced structureless reports"
severity: high
summary: "Eight fixes to the YAML frontmatter template parser: five harden parsing and sanitization boundaries, two remove legacy code superseded by the template system, one exports missing types. Core pattern: every new data source entering the system needs its own sanitize-at-boundary call."
---

# Defensive YAML Frontmatter Parsing

**Cycle 20 review fixes (075-082)** | 2026-02-27

## Prior Phase Risk

> "The interaction between fix 075 (empty body) and fix 079 (empty sections validation). A context file with only frontmatter and no body now returns `("", template)` — but `load_full_context` calls `sanitize_content("")` which returns `""`, so `raw_content` is truthy but `content` is empty. The ContextResult will be `loaded` with empty content but a valid template. This is correct behavior for a template-only file, but it's an edge case worth documenting."

Addressed below in [Edge Case: Template-Only Context Files](#edge-case-template-only-context-files).

---

## Problem

Eight issues were found in the YAML frontmatter template system introduced in cycle 20. They cluster into four themes:

### Theme 1: Parsing Correctness (Fixes 075, 076)

**Fix 075 — Body fallback leaked YAML into reports.** Three locations in `_parse_template()` used `body if body else raw`. If a context file contained only YAML frontmatter with no content below the closing `---`, `body` would be empty, and the fallback returned the entire raw file — YAML delimiters and all — as report content.

**Fix 076 — Delimiter search matched `---` inside YAML values.** The closing delimiter was found with `stripped.find("---", 3)`, which would match a literal `---` inside a YAML value like `description: "use --- for breaks"`, producing a malformed split.

### Theme 2: Security (Fix 077)

Template field values (headings, descriptions, `context_usage`, `name`) were inserted directly into LLM prompts without sanitization. The project's sanitize-at-boundary pattern (documented in `non-idempotent-sanitization-double-encode.md`) was applied to file body content but not to structured YAML fields — they entered through a different code path (`_parse_template` rather than direct file read) and bypassed `sanitize_content()`.

### Theme 3: Legacy Code and Validation (Fixes 078, 079)

**Fix 078 — Hardcoded PFE section names.** An `elif context` branch in `synthesize_final()` contained 18 lines with hardcoded section names ("Competitive Implications", "Positioning Advice"). The template system made this branch dead code, but it was never removed.

**Fix 079 — Empty template silently accepted.** A `ReportTemplate` with empty `draft_sections` and empty `final_sections` was returned as valid. Downstream code would iterate over nothing and produce a structureless report.

### Theme 4: Code Quality (Fixes 080, 081, 082)

- **080:** `ContextResult`, `ContextStatus`, `ReportTemplate` missing from `__init__.py` exports
- **081:** Mutable counter (`n += 1`) instead of `enumerate()` in `_build_final_sections()`
- **082:** Bare `list` type hint where `list[dict[str, str]]` was the actual type

---

## Root Cause

These eight issues exist together because cycle 20 introduced a new subsystem as an additive layer, and three things were not completed:

1. **The old branch was not removed.** The `elif context` PFE branch was left in place when the template system was added. Additive patterns reduce risk during implementation but require a cleanup pass.

2. **The sanitize-at-boundary pattern was applied to one artifact (file body) but not the new artifact (template fields).** YAML parsing produces structured values through a different code path than the file body read — it needs its own boundary.

3. **New types were added but not fully wired up.** Not exported, not validated at construction time, and helpers written in first-pass style.

The parsing bugs (075, 076) reflect under-tested edge cases: a file with no body after frontmatter, and a YAML value containing `---`. Both are rare, which is why they survived initial testing.

---

## Solution

### Fix 075 — Remove body fallback

```python
# Before (3 locations)
return body if body else raw, template

# After
return body, template
```

Empty string is correct for frontmatter-only files. The fallback undid the parsing.

### Fix 076 — Require newline before closing delimiter

```python
# Before
end = stripped.find("---", 3)

# After
end = stripped.find("\n---", 3)
```

YAML frontmatter convention: `---` must appear at the start of a line.

### Fix 077 — Sanitize template fields at parse boundary

```python
draft_sections = tuple(
    (sanitize_content(h), sanitize_content(d))
    for h, d in _parse_sections(draft_raw)
)
context_usage = sanitize_content(tmpl.get("context_usage", ""))
name = sanitize_content(data.get("name", ""))
```

All string fields pass through `sanitize_content()` once, at parse time. Downstream consumers receive pre-sanitized values.

### Fix 078 — Remove legacy PFE branch

Deleted 18-line `elif context` branch with hardcoded section names. Generic fallback handles context-without-template:

```python
# Generic fallback (no template)
context_instruction = (
    "Use the business context in <research_context> for analytical and "
    "recommendation sections. Reference specific positioning, threats, "
    "opportunities, and actionable recommendations tailored to the business."
)
```

### Fix 079 — Validate template has sections

```python
if not draft_sections and not final_sections:
    logger.warning("Template has no sections defined — ignoring")
    return (body, None)
```

Returns `(body, None)` — downstream code already handles "no template."

### Fix 081 — Replace mutable counter with enumerate

```python
# Before
n = len(template.draft_sections)
for heading, desc in template.final_sections:
    n += 1
    parts.append(f"{n}. **{heading}** — {desc}")

# After
parts = [
    f"{i}. **{heading}** — {description}"
    for i, (heading, description) in enumerate(sections, draft_count + 1)
]
```

---

## Key Pattern

**Every new data source entering the system needs its own sanitize-at-boundary call.**

The project already documents the rule: sanitize once, at the point where untrusted content crosses into the system. When cycle 20 introduced YAML frontmatter as a new input stream, it created a new boundary. The file body was sanitized at file-read time. Template field values arrive through a different code path (`_parse_template`) and must be sanitized at that path's boundary.

General rule: **when you add a new parser that produces values destined for LLM prompts, add `sanitize_content()` at the point where that parser returns its output.**

Secondary pattern: **YAML frontmatter delimiters are line-anchored.** The `---` that closes a frontmatter block must appear at the start of a line. Any string search for the closing delimiter must require a leading newline (`\n---`).

---

## Edge Case: Template-Only Context Files

Fixes 075 and 079 interact to define correct behavior for a file with only YAML frontmatter:

```markdown
---
name: PFE Entertainment Report
template:
  context_usage: Use for all Pacific Flow Entertainment queries
  draft:
    - Market Overview: Size, growth rate, key players
  final:
    - Strategic Recommendation: Actionable advice for PFE
---
```

**What `_parse_template()` returns:** `("", template)` — empty body, valid `ReportTemplate`.

**How `ContextResult` reflects this:** Status is `LOADED`, content is `""`, template is populated. The file was found and parsed. There's no prose to include, but the template drives section headings normally.

**What downstream code does:** `synthesize_final()` receives `context=""` and `template=template`. Empty context means no business prose in the report preamble. The template drives section headings. This is correct — the author chose to express structure without prose.

**The trap fix 075 prevented:** `body if body else raw` would have set content to the entire raw file — YAML delimiters, field names, and all — as garbled report text.

**The trap fix 079 prevents (separately):** A file with `draft: []` and `final: []` is not a usable template. Fix 079 returns `(body, None)`, so downstream code falls back to generic sections rather than generating a section-less report.

---

## Prevention

### Rules for Future Development

1. **Never fall back to raw input when parsed result is empty.** An empty parsed result means "nothing to use," not "parsing failed, try the original." If you need to distinguish parse failure from empty content, use an explicit error path.

2. **Match delimiters line-aware, not substring-wide.** Search for `\n---` (newline-prefixed) rather than bare `---`. Add a test with the delimiter embedded inside content values.

3. **Sanitize every input stream independently.** When a parser produces values from the same file as other data, those values are a separate input stream. Trace each value to its boundary and verify `sanitize_content()` is called there.

4. **Export new types from `__init__.py` in the same PR that defines them.** Missing exports force imports from internal modules, creating brittle dependencies.

### Checklist: Adding a New Frontmatter Field

1. Add field to the dataclass with type hint and default value
2. If the field holds file/user content: sanitize it in `_parse_template()` after YAML parsing
3. If the field has structural requirements: validate before returning the template
4. Export new types from `__init__.py` and `__all__`
5. Test: valid value, empty value, injection attempt, missing field
6. Update docstrings

### When to Remove Legacy Code

A code path is ready for removal when:
- Newer code handles all cases the old code handled
- The old path is no longer reachable from non-test code
- Tests pass using the new code path

Process: delete in a focused commit, check for orphaned helpers only used by the deleted code, verify full test suite passes.

---

## Risk Resolution

- **Flagged:** Fix-batched phase flagged the interaction between fix 075 (empty body) and fix 079 (empty sections) as an edge case worth documenting
- **What happened:** The interaction is correct — `("", template)` is valid for template-only files, and empty-section templates are correctly rejected. The two fixes address orthogonal concerns (body content vs template structure)
- **Lesson:** When two fixes modify the same function's return path, trace their interaction on the edge cases where both apply. Document the combined behavior explicitly — it's easy for future developers to see fix 075 and fix 079 individually but miss how they compose

---

## Cross-References

- [`non-idempotent-sanitization-double-encode.md`](../security/non-idempotent-sanitization-double-encode.md) — Fix 077 extends the sanitize-at-boundary pattern to YAML template fields, applying the same rule documented here for a new data source
- [`conditional-prompt-templates-by-context.md`](conditional-prompt-templates-by-context.md) — Fixes 075-076 and 079 harden the YAML parsing that feeds the conditional template branching documented here
- [`context-path-traversal-defense-and-sanitization.md`](../security/context-path-traversal-defense-and-sanitization.md) — Fix 077 reuses the same `sanitize_content()` contract for a new input stream from the same context file
- [`pip-installable-package-and-public-api.md`](../architecture/pip-installable-package-and-public-api.md) — Fix 080 follows the `__all__` export convention established here
- [`adversarial-verification-pipeline.md`](adversarial-verification-pipeline.md) — Fixes 078-079 clean up the synthesis pipeline to support generic templates flowing through the draft-skeptic-final architecture

### Commits

- `47aba21` — Fixes 075, 076 (parsing correctness)
- `1a2a6b3` — Fixes 077, 079, 082 (sanitization, validation, type hints)
- `6e0712a` — Fixes 078, 081 (legacy removal, enumerate)
- `6572949` — Fix 080 (public API exports)

---

## Three Questions

1. **Hardest pattern to extract from the fixes?** Articulating why fixes 075 and 079 compose correctly despite both modifying `_parse_template()`'s return path. Fix 075 says "empty body is valid" and fix 079 says "empty sections are not valid" — these look contradictory until you see they address different axes (content vs structure). The edge case section exists because this interaction is non-obvious.

2. **What did you consider documenting but left out, and why?** A full audit of every `sanitize_content()` call site to verify no other YAML-parsed fields are missed. Left it out because the `non-idempotent-sanitization-double-encode.md` solution already established the "trace the data flow" rule, which is more durable than a static inventory that goes stale.

3. **What might future sessions miss that this solution doesn't cover?** If a new frontmatter field is added that contains structured data (e.g., a list of URLs or a nested dict), `sanitize_content()` on its string representation may not be sufficient — it escapes `<>&` but doesn't handle other injection vectors. The current fields are all plain strings, so this isn't a problem yet, but a complex field type would need its own sanitization strategy.
