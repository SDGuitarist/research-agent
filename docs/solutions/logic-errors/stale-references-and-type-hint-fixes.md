---
title: "Resolve stale section references and type hints after refactoring"
date: 2026-02-28
category: logic-errors
tags: [refactoring, stale-references, type-hints, prompt-engineering]
components: [synthesize, critique]
severity: P2
root_cause: "Section numbering refactoring moved generic final sections to start at 5 via _DEFAULT_FINAL_START, but hardcoded 'Section 11' strings remained in prompts, docstrings, and tests; CritiqueResult.from_parsed type hint did not account for string values alongside int scores"
commits: ["a802b3d"]
related_todos: ["085", "086", "087"]
---

# Stale References and Type Hint Fixes After Refactoring

## Problem

After refactoring `synthesize.py` to extract `_build_default_final_sections()` with `_DEFAULT_FINAL_START = 5`, several stale references remained:

- **Docstring** said "Produce sections 9-12/13" and "Sections 1-8" — ranges that no longer matched any code path
- **Prompt strings** said "For Section 11 (Adversarial Analysis)" in both deep and standard skeptic paths — coupling LLM instructions to magic numbers
- **Comment** said "skip Section 11" — brittle to future constant changes
- **Type hint** `dict[str, int]` on `CritiqueResult.from_parsed` didn't match actual data shape `dict[str, int | str]` from `_parse_critique_response()`
- **Test name** `test_skips_section_11_when_no_findings` referenced the old numbering

None of these caused test failures or runtime errors. The prompt references created ambiguity for the LLM (which sees both the numbered section list and the prose instruction), and the type hint would produce false alarms under strict type checking.

## Root Cause

String-based references to section numbers weren't mechanically linked to the `_DEFAULT_FINAL_START` constant. When the constant changed from an implicit 11 to 5, the strings were left behind because:

1. **No single source of truth** — section identifiers appeared as magic numbers in multiple places (prompts, comments, docstrings)
2. **Intent vs. implementation divergence** — docstrings spoke about "Section 11" as a human-facing label, but the code only cared about positional ordering
3. **Type hint based on intent, not observation** — the hint expressed "scores are integers" rather than matching the actual union type returned by the parser

## Solution

### Fix 085: Replace section numbers with section names

All hardcoded "Section 11" in prompts became semantic labels:

- `"For Section 11 (Adversarial Analysis)"` → `"For the **Adversarial Analysis** section"`
- `"skip Section 11"` comment → `"skip Adversarial Analysis"`
- Docstring: "Produce sections 9-12/13" → "Produce final analytical sections"
- Docstring: "Sections 1-8" → "Factual analysis"

Section names are stable across refactoring; numbering is an implementation detail.

### Fix 087: Accurate type hint

`from_parsed(cls, parsed: dict[str, int], ...)` → `dict[str, int | str]`

Matches the actual return shape of `_parse_critique_response()`, which returns int scores for 5 dimensions plus str values for `weaknesses` and `suggestions`.

### Fix 086: Semantic test name

`test_skips_section_11_when_no_findings` → `test_skips_adversarial_analysis_when_no_findings`

Updated assertion from `"11. **Adversarial Analysis**" not in prompt` to `"**Adversarial Analysis**" not in prompt.split("Skip")[0]` — verifies the section list (before the "Skip" instruction) doesn't contain Adversarial Analysis, without depending on numbering.

## Prevention Strategies

### 1. Use section names in prompts, not numbers

When writing LLM prompt instructions that reference report sections, use the section heading name ("the **Adversarial Analysis** section") rather than a position number ("Section 11"). Numbers change when sections are added/removed; names are stable.

### 2. Name tests after behavior, not implementation details

Test names should describe what's being tested, not how:
- Bad: `test_skips_section_11_when_no_findings` (couples to numbering)
- Good: `test_skips_adversarial_analysis_when_no_findings` (describes behavior)

### 3. Type hints should match actual data flow

When writing type hints on factory methods or consumers, check what the producer actually returns — not what you intend to use. If a parser returns `dict[str, int | str]`, the consumer's hint should reflect that, even if the consumer only reads the `int` values.

### 4. Search for stale string references when refactoring

Before completing a refactoring that changes numbering, naming, or structure:
```bash
grep -r "Section [0-9]" research_agent/synthesize.py
grep -r "section_[0-9]" tests/test_synthesize.py
```

## Risk Resolution

**Risk flagged by review:** "Whether the LLM actually produces better output with 'Section 11' or 'the Adversarial Analysis section' in the prompt" — the behavioral impact is unknowable without A/B testing.

**Resolution:** The fix reduces ambiguity (section name is unambiguous; "Section 11" conflicts with the numbered list showing it at position 5). Even if the LLM compensated for the stale reference, removing the inconsistency is strictly better.

## Cross-References

- `docs/solutions/logic-errors/conditional-prompt-templates-by-context.md` — prompt template parameterization pattern
- `docs/solutions/architecture/domain-agnostic-pipeline-design.md` — removing hardcoded domain language from prompts
- `docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md` — Fix 082 (bare `list` type hint), Fix 078 (stale PFE section names)
- `todos/088-pending-p3-default-final-start-coupling.md` — related: `_DEFAULT_FINAL_START = 5` magic constant coupling

## Three Questions

1. **Hardest pattern to extract from the fixes?** Distinguishing "stale string references" from "prompt engineering choices." The Section 11 references weren't bugs — they were design decisions that became stale. The pattern is: any string that encodes a position is a maintenance liability when positions change.

2. **What did you consider documenting but left out, and why?** A `TypedDict` for the critique response shape (`CritiqueData`). It's a good idea but over-engineering for the current scope — the `dict[str, int | str]` fix is sufficient and the codebase doesn't use `TypedDict` elsewhere.

3. **What might future sessions miss that this solution doesn't cover?** The `_DEFAULT_FINAL_START = 5` coupling (todo 088) is still pending. If someone adds a 5th generic draft section, the constant silently produces wrong numbering. This doc covers the symptom (stale refs) but not the root coupling.
