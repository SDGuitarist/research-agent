---
title: "feat: Remove Business-Domain Assumptions from Pipeline Prompts"
type: feat
status: active
date: 2026-02-27
origin: docs/brainstorms/2026-02-26-flexible-context-system-brainstorm.md
feed_forward:
  risk: "Dynamic template generation (Key Decision #4) — LLM-produced report sections are hard to test and less predictable than hardcoded templates"
  verify_first: true
---

# feat: Remove Business-Domain Assumptions from Pipeline Prompts

## Prior Phase Risk

> **Least confident:** Dynamic template generation (Key Decision #4). Having the LLM produce domain-appropriate report sections from the context file is powerful but hard to test and less predictable than hardcoded templates.

**Resolution:** Defer dynamic template generation. The existing YAML frontmatter template system already lets each context file define its own sections. The generic 4-section fallback is good enough for context files without templates. A CLI hint nudges users to add frontmatter. This avoids the extra LLM call, unpredictable output, and testing complexity. See "Decisions" below.

## Overview

The flexible context system's infrastructure (Layers 1-3 from the brainstorm) is **already implemented**: section slicing was removed, `--context` flag exists, auto-detect works, YAML frontmatter templates work. What remains is removing hardcoded business-domain language from prompts so non-PFE queries produce clean, domain-generic output.

## Problem Statement

Seven places in the pipeline still assume competitive/business analysis regardless of context:

1. **`summarize.py:99-101`** — Deep mode structured extraction asks for "KEY QUOTES from reviews/marketing" and "TONE: persuasion approach" unconditionally
2. **`synthesize.py:220`** — Template-present path says "Business context is provided in `<research_context>`"
3. **`synthesize.py:225`** — Quick mode fallback instruction says "Business context is provided"
4. **`synthesize.py:498-501`** — Final synthesis fallback says "positioning, threats, opportunities, and actionable recommendations tailored to the business"
5. **`synthesize.py:612`** — System prompt says "business context"
6. **`decompose.py:111`** — Query decomposition says "relevant to the user's business"
7. **`context_result.py:26`** — Docstring says "business context" (cosmetic but violates acceptance criteria)

Additionally:
- Auto-detect's single-file short-circuit always loads `pfe.md` even for unrelated queries
- Legacy `research_context.md` duplicates `contexts/pfe.md` and creates a behavioral inconsistency
- Pre-existing double-sanitization bug in `context.py:_summarize_patterns()` (lines 411, 420)

## Decisions (Resolving Brainstorm Open Questions)

### Decision 1: No dynamic template generation (resolves brainstorm Feed-Forward risk)

**Chose:** Option A — keep generic 4-section fallback for context files without YAML templates.

**Why:** The YAML template system already exists and works. Users who want custom sections add frontmatter. Dynamic generation adds an LLM call (~$0.002/run), inconsistent output between runs, and testing complexity for marginal benefit. A CLI hint is cheaper.

**Rejected:** Option B (LLM-generated templates) — the brainstorm correctly flagged this as risky. Option C (require YAML) — too strict for new users.

### Decision 2: PFE keeps its template, no special treatment (resolves Open Question #1)

PFE's report sections come from `contexts/pfe.md`'s YAML frontmatter, same as any other context file. No hardcoded PFE template in code. `--context pfe` produces similar output to today because the template defines the same 8+2 sections.

### Decision 3: Remove single-file short-circuit in auto-detect

When `contexts/` has exactly one file, the system currently skips the LLM and always loads it. This means "Python async best practices" gets PFE business context injected. One Haiku call (~$0.0003, ~500ms) is worth the relevance check. Performance oracle confirmed: negligible vs. the 20-60s pipeline.

### Decision 4: Remove legacy `research_context.md` fallback

Both files have identical content. The legacy path loads without a template (producing generic sections) while `contexts/pfe.md` loads with a template (producing 8+2 sections). Same content, different behavior = confusing. Remove the legacy file and `DEFAULT_CONTEXT_PATH`.

### Decision 5: Generic structured extraction for deep mode

Replace business-domain structured fields with generic ones:
- `KEY QUOTES` → `KEY EVIDENCE` (direct quotes or data points that support the main claims)
- `TONE` → `PERSPECTIVE` (the source's analytical stance or framing, or "N/A")

> **Research insight:** "PERSPECTIVE" outperforms "METHODOLOGY" because it captures how the source frames its argument without assuming a specific analytical method. Works for academic papers (empirical vs theoretical), news (investigative vs editorial), and marketing alike. "METHODOLOGY" is too narrow for non-academic sources. (Source: prompt template analysis, arxiv 2504.02052v2)

### Decision 6: Use `logger.warning()` not `print(file=sys.stderr)` for warnings

The codebase has a clear separation: `logger.warning()` in library modules, `print(file=sys.stderr)` only in `cli.py`. Adding stderr prints to `context.py` would break this pattern and create two parallel warning channels. Instead, use `logger.warning()` everywhere and let the CLI logging config control visibility.

> **Pattern insight:** All 14 existing warnings in `context.py` use `logger.warning()`. Zero use `print(file=sys.stderr)`. (Source: pattern-recognition-specialist)

### Decision 7: Drop auto-detect preview improvement (YAGNI)

The plan originally proposed using the `name` field from YAML frontmatter for auto-detect previews. This is speculative — no evidence the current 5-line preview fails. Ship without it, iterate if auto-detect struggles in practice. Users can always use `--context pfe` explicitly.

> **Simplicity insight:** "This is a classic 'just in case' feature. Ship without it, see if auto-detect actually fails in practice." (Source: code-simplicity-reviewer)

## Proposed Solution

Eight targeted changes across 5 files, plus legacy cleanup, a pre-existing bug fix, and tests. Organized into 2 work sessions (~80-100 lines each, tests co-located with code changes).

## Technical Considerations

- **Sanitization contract**: All context content is sanitized once at load boundary in `context.py`. No new sanitization needed (see `docs/solutions/security/non-idempotent-sanitization-double-encode.md`).
- **Path traversal**: Already defended in `resolve_context_path()` with two-layer validation (see `docs/solutions/security/context-path-traversal-defense-and-sanitization.md`).
- **Template parsing**: Already hardened with edge case handling (see `docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md`).
- **ContextResult states**: Four-state enum (loaded/not_configured/empty/failed) already exists and handles all outcomes.
- **Double-sanitization bug**: `_summarize_patterns()` at `context.py:411,420` calls `sanitize_content()` on individual strings AND on the assembled summary. Fix by removing the summary-level call at line 420 (keep per-field sanitization, consistent with `_parse_template()` pattern). See `docs/solutions/security/non-idempotent-sanitization-double-encode.md`.
- **Prompt design**: Anthropic docs confirm Claude responds well to descriptive generic instructions. No evidence of quality regression when replacing domain-specific with well-crafted generic extraction fields. (Source: best-practices-researcher)

## System-Wide Impact

- **Interaction graph**: Changes to `summarize.py` affect deep mode pass 1 and 2 in `agent.py`. Changes to `synthesize.py` affect all three synthesis functions. Changes to `decompose.py` affect query decomposition (only the prompt text, not logic). No callbacks or observers involved.
- **Error propagation**: Context loading errors bubble up as `ContextResult.failed()`, which is already handled gracefully. New `logger.warning()` calls do not change error flow.
- **State lifecycle risks**: None — all changes are to prompt text and a single conditional guard. No new state is introduced.
- **API surface parity**: The public API (`run_research`, `run_research_async`) already accepts `context` parameter. No API changes needed.
- **Integration test scenarios**: (1) Deep mode + `--context none` should produce no business-domain language in structured extraction. (2) Auto-detect with single file + unrelated query should select "none". (3) Removing `research_context.md` should not break runs when `contexts/pfe.md` exists.

## Implementation Plan

### Session 1: Generic Prompts + Tests (~100 lines)

**Files:** `summarize.py`, `synthesize.py`, `decompose.py`, `context_result.py`, `tests/test_summarize.py`, `tests/test_synthesize.py`, `tests/test_decompose.py` (if needed)

**Prompt changes:**

1. **`summarize.py:99-101`** — Replace structured extraction format:
   ```
   # Before
   KEY QUOTES: [2-3 exact phrases from reviews/marketing, or "None found"]
   TONE: [one sentence on persuasion approach, or "N/A"]

   # After
   KEY EVIDENCE: [2-3 direct quotes or data points that support the main claims, or "None found"]
   PERSPECTIVE: [one sentence on the source's analytical stance or framing, or "N/A"]
   ```

2. **`synthesize.py:220`** — Template-present path in `synthesize_report()`:
   ```
   # Before
   "Business context is provided in <research_context>."

   # After
   "Research context is provided in <research_context>."
   ```

3. **`synthesize.py:225`** — Quick mode fallback instruction in `synthesize_report()`:
   ```
   # Before
   "Business context is provided in <research_context>. Use it for ..."

   # After
   "Research context is provided in <research_context>. Use it for ..."
   ```

4. **`synthesize.py:498-501`** — Fallback context instruction in `synthesize_final()`:
   ```
   # Before
   "Reference specific positioning, threats, opportunities, and actionable
   recommendations tailored to the business."

   # After
   "Reference specific details from the context to ground your
   recommendations in the user's situation."
   ```

5. **`synthesize.py:612`** — System prompt in `synthesize_final()`:
   ```
   # Before
   "The business context in <research_context> is trusted."

   # After
   "The research context in <research_context> is trusted."
   ```

6. **`decompose.py:111`** — Query decomposition prompt:
   ```
   # Before
   "specific and relevant to the user's business"

   # After
   "specific and relevant to the user's context"
   ```

**Docstring updates:**

7. **`context_result.py:26`** — `context_usage` docstring: "business context" → "research context"
8. **`summarize.py:171,222`** — `summarize_content()` and `summarize_all()` docstrings: update "FACTS/KEY QUOTES/TONE" → "FACTS/KEY EVIDENCE/PERSPECTIVE"

**Test updates (same session — keep suite green):**

9. Update `tests/test_summarize.py` assertions that check "KEY QUOTES" and "TONE" field names
10. Update `tests/test_synthesize.py` assertions that check "business" in fallback instructions

**Acceptance criteria:**
- [ ] No prompt text in any `.py` file contains "business", "marketing", "persuasion", "positioning", or "threats" (except `contexts/pfe.md`)
- [ ] All existing tests pass with updated assertions
- [ ] `grep -rn "business" research_agent/ --include="*.py"` returns zero results

### Session 2: Auto-Detect Fix + Legacy Cleanup + Bug Fix + Tests (~80 lines)

**Files:** `context.py`, `tests/test_context.py`, `tests/test_agent.py`

**Code changes:**

1. **Remove single-file short-circuit** in `auto_detect_context()` (`context.py:264-269`):
   - Delete the `if len(available) == 1: return ...` block
   - Single-file case now goes through the LLM relevance check like multi-file

2. **Remove `DEFAULT_CONTEXT_PATH`** (`context.py:18`):
   - Delete `DEFAULT_CONTEXT_PATH = Path("research_context.md")`
   - In `load_full_context()`, when `context_path is None`, return `ContextResult.not_configured()` immediately (guard before any `.exists()` call)
   - Update docstring at `context.py:172`: "defaults to research_context.md" → "None returns not_configured"

3. **Delete `research_context.md`** from project root (content already in `contexts/pfe.md`)

4. **Fix double-sanitization** in `_summarize_patterns()` (`context.py:420`):
   - Remove `return sanitize_content(summary)` → `return summary`
   - Per-field sanitization at line 411 is sufficient (consistent with `_parse_template()` pattern)

**Test updates (same session):**

6. **Rewrite `test_single_context_shortcircuits_llm`** (`tests/test_context.py:630-643`):
   - Old: asserts LLM is NOT called for single file
   - New: mock LLM to return "none", verify no context loaded; mock LLM to return "pfe", verify context loaded

7. **Add legacy fallback removal test** — verify `load_full_context(None)` returns `not_configured`

8. **Add double-sanitization fix test** — verify `_summarize_patterns()` output does not double-encode `&`

9. **Update any tests referencing `research_context.md`** or `DEFAULT_CONTEXT_PATH`

**Acceptance criteria:**
- [ ] Auto-detect with single file + unrelated query can return "none"
- [ ] `research_context.md` no longer exists
- [ ] `load_full_context(None)` returns `ContextResult.not_configured()`
- [ ] `_summarize_patterns()` with `&` in weakness text produces `&amp;` (not `&amp;amp;`)
- [ ] All 754+ tests pass
- [ ] No test references `research_context.md` as an expected file

## Acceptance Criteria (Overall)

- [ ] `python3 main.py --deep "Python async best practices"` produces a report with no business-domain language
- [ ] `python3 main.py --context pfe --deep "competitor analysis"` produces PFE-templated report (same as today)
- [ ] `python3 main.py --standard "general query"` with only `contexts/pfe.md` available: auto-detect may select "none"
- [ ] `grep -rn "business" research_agent/ --include="*.py"` returns zero results
- [ ] No pre-existing double-sanitization bug in `_summarize_patterns()`
- [ ] All tests pass
- [ ] Legacy `research_context.md` removed

## Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Changing structured extraction format affects deep mode output quality | Keep same number of fields, use descriptive brackets. Research confirms no quality regression with well-crafted generic instructions. |
| Removing single-file short-circuit adds Haiku call cost | ~$0.0003 and ~500ms per run. Negligible vs. 20-60s pipeline. Performance oracle approved. |
| Removing `research_context.md` breaks users who have it but not `contexts/` | `load_full_context(None)` returns `not_configured` — agent runs without context, which is correct behavior. No migration message needed (personal CLI tool, not a library). |
| Tests that hard-assert on prompt text will break | Tests updated in same session as code changes (Sessions 1 and 2 each include their own test updates). |
| Pre-existing double-sanitization in `_summarize_patterns()` | Fixed opportunistically in Session 2 while already modifying `context.py`. |

## Sources & References

- **Origin brainstorm:** [docs/brainstorms/2026-02-26-flexible-context-system-brainstorm.md](docs/brainstorms/2026-02-26-flexible-context-system-brainstorm.md) — Key decisions carried forward: three-layer design, flexible parsing, multiple context files, auto-detect
- **Institutional learnings:**
  - [docs/solutions/security/non-idempotent-sanitization-double-encode.md](docs/solutions/security/non-idempotent-sanitization-double-encode.md) — sanitize once at boundary
  - [docs/solutions/security/context-path-traversal-defense-and-sanitization.md](docs/solutions/security/context-path-traversal-defense-and-sanitization.md) — two-layer path validation
  - [docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md](docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md) — template parsing edge cases
  - [docs/solutions/logic-errors/conditional-prompt-templates-by-context.md](docs/solutions/logic-errors/conditional-prompt-templates-by-context.md) — gate domain-specific prompts on context presence
- **Deepening research:**
  - Prompt template analysis (arxiv 2504.02052v2) — universal structure across domains, descriptive field names outperform domain-specific ones
  - [Anthropic prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — Claude handles generic instructions well when brackets are descriptive
  - [Anthropic prompt templates and variables](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables) — parameterize Context and Output Format, keep structure fixed
- **SpecFlow analysis:** 17 gaps identified, 10 critical questions resolved. Key gaps addressed: domain-biased extraction (Gap 1), business-specific fallback instructions (Gap 2-4), single-file short-circuit (Gap 5), legacy duplication (Gap 8-9), silent failures (Gap 11-13)
- **Review agents:** 7 agents, 0 critical findings, 2 medium (missed code locations + double-sanitization bug), rest are low/informational. All performance concerns approved. Security audit: net positive (reduces attack surface).
- **Current code references:** `summarize.py:99-101`, `synthesize.py:220,225,498-501,612`, `decompose.py:111`, `context_result.py:26`, `context.py:18,264-269,411,420`

## Feed-Forward

- **Hardest decision:** Whether to remove the single-file short-circuit in auto-detect. It's a UX tradeoff — one extra LLM call vs. always getting context for unrelated queries. Chose correctness. Performance oracle confirmed negligible cost.
- **Rejected alternatives:** (1) Dynamic template generation — brainstorm's highest risk, deferred. (2) Requiring YAML frontmatter on all context files — too strict. (3) Keeping `research_context.md` as a "quick start" — confusing behavioral inconsistency not worth the convenience. (4) `print(file=sys.stderr)` for warnings — breaks library/CLI separation. (5) Auto-detect preview improvement via YAML `name` field — YAGNI, no evidence current preview fails.
- **Least confident:** Whether "PERSPECTIVE" produces better extraction than "METHODOLOGY" in practice. The research supports it theoretically, but deep mode output should be spot-checked after Session 1 to verify. If extraction quality drops, revert to "METHODOLOGY" or experiment with "ANALYSIS APPROACH".
