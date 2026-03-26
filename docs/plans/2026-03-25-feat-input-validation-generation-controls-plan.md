---
title: "Cycle 27: Input Validation + Generation Controls"
type: feat
status: active
date: 2026-03-25
cycle: 27
origin: docs/brainstorms/2026-03-25-cycle-27-input-validation-generation-controls-brainstorm.md
feed_forward:
  risk: "The proper-noun edge case in vague query detection. Capitalization heuristic may reject lowercase brands (adidas) and short valid queries (AI ethics)."
  verify_first: true
---

# Cycle 27: Input Validation + Generation Controls

## Enhancement Summary

**Deepened on:** 2026-03-25
**Agents used:** security-sentinel, performance-oracle, code-simplicity-reviewer, best-practices-researcher (html.unescape), framework-docs-researcher (Anthropic API)

### Key Improvements
1. Dropped `summarize_temperature` (YAGNI — 1 call site, speculative default) → 2 fields instead of 3
2. Fixed error message example ("Tesla" passes the gate; changed to "stuff")
3. Proper-noun check must inspect original token before lowercasing (meaningful_words lowercases)
4. Expanded sanitization test corpus with entity edge cases (`&amp;amp;`, `&copy;`, `&nbsp;`, `&#999999;`)
5. Clarified VagueQueryError is a UX gate, not a security control

### New Considerations Discovered
- `html.unescape` decodes ALL 2,231 HTML5 entities (`&copy;` → `©`, `&nbsp;` → `\xa0`). Only `&`, `<`, `>` get re-escaped. Safe in prompt context but important to know.
- Anthropic API temperature range is 0.0-1.0 (not 0.0-2.0). Default is 1.0 when omitted. `temperature=0.0` is NOT fully deterministic.
- Extended thinking requires `temperature=1.0` — not relevant now but document for future.

## Prior Phase Risk

> "The proper-noun edge case in vague query detection. 'Tesla' is one word but has clear research intent. A capitalization heuristic is the plan, but edge cases remain: all-lowercase brand names ('adidas'), acronyms ('NASA'), and queries that are short but valid ('AI ethics')." — Brainstorm Feed-Forward

**Resolution:** Lowered the threshold from 3 to 2 meaningful words and defined a concrete test corpus with 15 edge cases (see Acceptance Criteria). This lets "AI ethics" (2 words) pass while still rejecting "stuff" (1 word). The proper-noun exception applies only to single-word queries via a capitalization-or-all-caps heuristic. Lowercase brands like "adidas" will be rejected — acceptable tradeoff since users can add a second word ("adidas research").

## Overview

Three features that harden the pipeline's input boundary and stabilize LLM output:

1. **Vague query detection** — reject garbage queries before any API call
2. **Idempotent sanitization** — fix the double-encoding bug with `html.unescape` + `html.escape`
3. **Per-task temperature controls** — stabilize classification, tune synthesis creativity

Estimated scope: ~120 lines across ~20 files, 6 commits. Three independent features, each deployable separately.

## What Exactly Is Changing

| Feature | Files modified | Files created | Lines (est.) |
|---------|---------------|---------------|-------------|
| Vague query detection | `errors.py`, `query_validation.py`, `agent.py` | `tests/test_vague_query.py` | ~50 |
| Idempotent sanitization | `sanitize.py`, `tests/test_sanitize.py`, `synthesize.py` (comment) | — | ~20 |
| Per-task temperature | `modes.py`, `agent.py`, + 10 modules with API calls, `mcp_server.py` | `tests/test_temperature.py` | ~60 |

## What Must Not Change

- All 938 existing tests pass (except `test_ampersand_before_angle_brackets` which asserts the bug being fixed — update expected value)
- Module function signatures remain backward-compatible (new params have defaults)
- Sanitization behavior for single-call paths (first call produces identical output for raw text)
- `ResearchMode` construction by existing callers (new fields have defaults)
- Temperature threading is coordinated from `agent.py`, but 13 modules already import `modes.py` directly (mostly for `DEFAULT_MODEL` and `AUTO_DETECT_MODEL` constants). The new temperature fields do not affect these existing imports since modules receive temperature as a function parameter, not by importing it from modes.

## Proposed Solution

### Feature 1: Vague Query Detection

**Gate location:** `agent.py` inside `research_async()`, before any mode-specific branching. This catches CLI, MCP, and all modes (including quick, which skips `decompose_query()`).

The brainstorm placed it in `decompose.py`, but SpecFlow analysis found that quick mode bypasses decompose entirely — a `--quick "stuff"` query would waste API calls. Moving the gate to the agent entry point makes it universal.

**Heuristic (concrete):**
1. Run `meaningful_words(query)` from existing `query_validation.py` — strips stopwords, returns set of content words
2. If `len(meaningful_words) >= 2` → pass
3. If `len(meaningful_words) == 1` → find the matching **original token** from `query.split()` (before lowercasing). Strip surrounding punctuation and quotes from the token first (same `strip(',.?!;:\\"\'()[]')` that `meaningful_words` uses internally). Then check: if the stripped token starts with an uppercase letter OR is all-caps with length >= 2 → pass (proper-noun/acronym exception). Examples: `'"Tesla"'` → strip quotes → `'Tesla'` → starts uppercase → PASS. `"NASA!"` → strip punctuation → `"NASA"` → all-caps → PASS. `"'stuff'"` → strip quotes → `"stuff"` → lowercase → REJECT.
4. Otherwise → raise `VagueQueryError("Query too vague for research. Please add specific terms — e.g., 'climate change policy' instead of 'stuff'.")`

**Exception class:** `VagueQueryError(ResearchError)` in `errors.py`. Simple subclass, no custom `__init__`. This is a **UX quality gate, not a security control** — the docstring must say so explicitly. Prompt injection defense remains the existing three-layer architecture (sanitize + XML boundaries + system prompt). Inheriting from `ResearchError` means:
- CLI: caught by existing `except ResearchError` in `cli.py:374` → clean exit with message
- MCP: caught by existing `except ResearchError` in `mcp_server.py` → converted to `ToolError`
- **Python API:** `run_research()` and `run_research_async()` in `__init__.py` both call `agent.research_async()` internally, so the gate fires for direct library callers too. `VagueQueryError` propagates as a `ResearchError` subclass — callers already catching `ResearchError` will see it. Update the `run_research()` docstring's Raises section to mention `VagueQueryError` explicitly.

**Test corpus (14 cases):**

| Query | Meaningful words | Proper noun? | Result |
|-------|-----------------|--------------|--------|
| `"stuff"` | 1: {stuff} | No | REJECT |
| `"what's up"` | 2: {what's, up} | — | PASS (what's survives stopwords — only "what" is a stopword) |
| `"it"` | 1: {it} | No | REJECT |
| `"a"` | 0: {} (stopword) | — | REJECT |
| `"Tesla"` | 1: {tesla} | Yes (starts uppercase) | PASS |
| `"NASA"` | 1: {nasa} | Yes (all-caps, len>=2) | PASS |
| `"AI"` | 1: {ai} | Yes (all-caps, len>=2) | PASS |
| `"adidas"` | 1: {adidas} | No (lowercase) | REJECT |
| `"AI ethics"` | 2: {ai, ethics} | — | PASS |
| `"climate change"` | 2: {climate, change} | — | PASS |
| `"San Diego wedding venues"` | 4 | — | PASS |
| `"2024"` | 1: {2024} | No | REJECT |
| `"what is AI"` | 1: {ai} (after stopwords) | Yes (all-caps) | PASS |
| `"   "` | 0 | — | REJECT (empty after strip) |

**Note on non-English:** `meaningful_words()` uses `.split()` which works on whitespace. CJK queries without spaces would be 1 "word" and rejected unless they match the proper-noun heuristic. This is acceptable for v1 — the tool is English-focused. Document as a known limitation.

### Feature 2: Idempotent Sanitization

**Implementation:**

```python
import html

def sanitize_content(text: str) -> str:
    return html.escape(html.unescape(text), quote=False)
```

**Why `html.unescape` first:** `html.escape()` alone is NOT idempotent — `html.escape("&amp;")` produces `"&amp;amp;"`, the exact same double-encoding bug. The `unescape` step normalizes any pre-escaped entities back to raw characters, then `escape` encodes them exactly once.

**`quote=False`:** Escapes only `&`, `<`, `>` — matching current behavior. The default `quote=True` would also escape `"` to `&quot;`, which is unnecessary since all sanitized content goes into XML-delimited prompt blocks, not HTML attributes.

**Behavioral changes (intentional):**
- `sanitize_content("&amp;")` → `"&amp;"` (was `"&amp;amp;"` — this is the fix)
- `sanitize_content("&lt;script&gt;")` → `"&lt;script&gt;"` (was `"&amp;lt;script&amp;gt;"` — no longer double-encodes)
- Numeric entities like `&#39;` get decoded then re-escaped to their character form — net safe

**html.unescape edge cases (verified idempotent):**
- `html.unescape` decodes ALL 2,231 HTML5 entities: `&copy;` → `©`, `&nbsp;` → `\xa0`, `&mdash;` → `—`. Only `&`, `<`, `>` get re-escaped by `html.escape`. Other decoded entities (©, \xa0, etc.) pass through as Unicode. Safe in prompt context — these go into XML-delimited blocks, not rendered HTML.
- Malformed entities without semicolons (`&amp` → `&amp;`): normalizes on first call, stable after. `f(f(x)) == f(x)` holds.
- Out-of-range numeric refs (`&#999999;`): decoded to Unicode character. Lossy but stable. `f(f(x)) == f(x)` holds.
- Unknown named entities (`&nonexistent;`): `unescape` leaves as-is, `escape` encodes the `&`. On second call, `unescape` decodes `&amp;` back, producing same result. `f(f(x)) == f(x)` holds.
- Double-encoded from web (`&amp;amp;`): normalizes to `&amp;`. `f(f(x)) == f(x)` holds.
- `&nbsp;` decodes to `\xa0` (non-breaking space), NOT regular space. `.strip()` will not remove it. Not a bug but worth knowing.

**Test updates:**
- Update `test_ampersand_before_angle_brackets` to assert new idempotent behavior
- Add `test_idempotent`: assert `sanitize_content(sanitize_content(x)) == sanitize_content(x)` for expanded corpus: `"&amp;"`, `"&lt;script&gt;"`, `"AT&T"`, `"&amp;amp;"`, `"&copy;"`, `"&nbsp;"`, `"&#999999;"`, `"&nonexistent;"`, `"plain text"`, `"&amp"` (no semicolon)
- Add `test_quote_false`: assert `"` passes through unescaped

**Stale comment:** Update `synthesize.py:545-546` comment that says "sanitize_content is not idempotent" — it is now.

### Feature 3: Per-Task Temperature Controls

**New fields on `ResearchMode`** (frozen dataclass in `modes.py`):

```python
planning_temperature: float = 0.2    # decompose, relevance, context detect, query refine, coverage gaps
synthesis_temperature: float = 0.8   # report synthesis, skeptic, critique, follow-ups, summarization
```

Two tiers, not three. The brainstorm proposed a separate `summarize_temperature = 0.5`, but it would serve exactly 1 call site (`summarize_chunk`) with a speculative default. YAGNI — route summarization to `synthesis_temperature` for now. Add a third field only if a future cycle finds evidence summarization needs independent tuning.

**Validation in `__post_init__`:** Assert `0.0 <= t <= 1.0` for each temperature field. Raise `ValueError` on violation. The Anthropic API range is confirmed 0.0-1.0 (not 0.0-2.0). Default when omitted is 1.0. `temperature=0.0` reduces randomness but is NOT fully deterministic per Anthropic docs.

**Threading pattern:** Same as model routing — `agent.py` passes `temperature=self.mode.<tier>_temperature` to each module function. Each module function adds `temperature: float = 1.0` as a defaulted parameter (backward-compatible). The temperature is forwarded to `messages.create()` / `messages.stream()` as a kwarg.

**Complete call site routing table:**

| # | File:Line | Function | Task type | Temperature field |
|---|-----------|----------|-----------|-------------------|
| 1 | `decompose.py:102` | `decompose_query` | classification | `planning_temperature` |
| 2 | `relevance.py:161` | `score_source` (via retry) | classification | `planning_temperature` |
| 3 | `relevance.py:435` | `insufficient_data_response` | synthesis | `synthesis_temperature` |
| 4 | `context.py:414` | `auto_detect_context` | classification | `planning_temperature` |
| 5 | `search.py:241` | `refine_query` | classification | `planning_temperature` |
| 6 | `coverage.py:250` | `identify_coverage_gaps` | classification | `planning_temperature` |
| 7 | `summarize.py:121` | `summarize_chunk` (via retry) | summarization | `synthesis_temperature` |
| 8 | `iterate.py:73` | `generate_refined_queries` | classification | `planning_temperature` |
| 9 | `iterate.py:194` | `generate_followup_questions` | synthesis | `synthesis_temperature` |
| 10 | `critique.py:205` | `evaluate_report` | synthesis | `synthesis_temperature` |
| 11 | `critique.py:280` | `critique_from_file` | synthesis | `synthesis_temperature` |
| 12 | `skeptic.py:76` | `run_skeptic_pass` (via retry) | synthesis | `synthesis_temperature` |
| 13 | `synthesize.py:342` | `synthesize_report` (stream) | synthesis | `synthesis_temperature` |
| 14 | `synthesize.py:458` | `synthesize_draft` (stream) | synthesis | `synthesis_temperature` |
| 15 | `synthesize.py:689` | `synthesize_final` (stream) | synthesis | `synthesis_temperature` |
| 16 | `synthesize.py:831` | `synthesize_mini_report` | synthesis | `synthesis_temperature` |
| 17 | `mcp_server.py:196` | `critique_report` (local client) | synthesis | hardcoded `0.8` |
| 18 | `mcp_server.py:253` | `generate_followups` (local client) | synthesis | hardcoded `0.8` |

**MCP server special case:** `mcp_server.py` constructs its own `Anthropic()` clients for two tool functions (critique_report, generate_followups). These are outside the `ResearchMode` pipeline. Add `temperature=0.8` directly to these two `messages.create()` calls. No parameter threading needed — they're standalone.

**`iterate.py` routing rationale:** `generate_refined_queries` (line 73) is a planning task — it analyzes gaps and produces structured query suggestions → `planning_temperature`. `generate_followup_questions` (line 194) generates user-facing prose questions → `synthesis_temperature`.

## Implementation Phases

### Phase 1: Idempotent Sanitization (~1 commit, smallest blast radius)

**Commit 1:** `fix(27): make sanitize_content idempotent with html.unescape+escape`
- Modify `sanitize.py`: replace `.replace()` chain with `html.escape(html.unescape(text), quote=False)`
- Update `tests/test_sanitize.py`: fix `test_ampersand_before_angle_brackets` expected value, add `test_idempotent` (10-case corpus), add `test_quote_false`
- Update `synthesize.py:545-546` stale "not idempotent" comment + any others found via grep
- Run full test suite — expect 1 test failure fixed, 0 regressions

### Phase 2: Vague Query Detection (~2 commits)

**Commit 2:** `feat(27): add VagueQueryError and vague query gate`
- Add `VagueQueryError(ResearchError)` to `errors.py` with docstring: "Rejects queries too vague to produce useful research results. This is a UX gate, not a security control."
- Add `_check_query_not_vague(query: str)` function in `query_validation.py` (alongside existing `meaningful_words`)
- Call it in `agent.py:research_async()` before mode branching
- Import from `query_validation.py`

**Commit 3:** `test(27): add vague query detection test corpus`
- Create `tests/test_vague_query.py` with all 14 test corpus cases
- Test error message content
- Test that `VagueQueryError` is a `ResearchError` subclass
- Test Python API path: `run_research_async("stuff")` raises `VagueQueryError`
- Update `run_research()` docstring in `__init__.py` to list `VagueQueryError` in Raises

### Phase 3: Per-Task Temperature (~3 commits, most files touched)

**Commit 4:** `feat(27): add temperature fields to ResearchMode`
- Add 2 fields to `ResearchMode` dataclass in `modes.py`
- Add validation in `__post_init__`
- Add temperature to the debug log line in `agent.py:423-424`

**Commit 5:** `feat(27): thread temperature to all API call sites`
- Update each module function to accept `temperature: float = 1.0`
- Update each `messages.create()` / `messages.stream()` call to pass `temperature=temperature`
- Update `agent.py` to pass the correct temperature tier at each call site
- Hardcode `temperature=0.8` for the two MCP server local clients

**Commit 6:** `test(27): add temperature threading tests`
- Create `tests/test_temperature.py`
- Test that `ResearchMode` validates temperature range
- Test that default temperatures match expected values
- Mock-based tests that verify `temperature` kwarg is passed to `messages.create()`

## How We'll Know It Worked

1. `sanitize_content(sanitize_content(x)) == sanitize_content(x)` for all test corpus inputs
2. `--quick "stuff"` and `--standard "stuff"` both exit with `VagueQueryError`, zero API calls
3. `--quick "Tesla"` proceeds normally (proper-noun exception)
4. `run_research("stuff")` raises `VagueQueryError` (Python API path via `__init__.py`)
5. All 14 test corpus queries produce expected pass/fail results
5. `temperature` kwarg present in every `messages.create()` and `messages.stream()` call (verified via mock tests)
6. All 938+ existing tests pass (with 1 test updated for new sanitization behavior)

## Most Likely Way This Plan Is Wrong

The `html.unescape()` step could have unexpected effects on content containing HTML numeric entities (like `&#39;` or `&#x3C;`). These get decoded to raw characters then re-escaped. The net result should be safe (raw `<` gets escaped back to `&lt;`), but if any downstream code depends on the specific entity format (numeric vs named), it could break. **Mitigation:** the test corpus includes entity edge cases, and the full test suite catches regressions.

## Dependencies & Risks

- **No external dependencies.** All three features use stdlib (`html` module) and existing internal utilities (`meaningful_words`, `STOP_WORDS`).
- **Risk: temperature changes affect output quality.** Classification tasks getting 0.2 instead of the default 1.0 will produce more deterministic outputs. This is the intended effect but could surface if any test depends on varied LLM output.
- **Risk: sanitization behavior change in edge cases.** The `unescape` step normalizes entity formats. Mitigated by comprehensive test corpus.

## Sources & References

### Origin

- **Brainstorm:** [docs/brainstorms/2026-03-25-cycle-27-input-validation-generation-controls-brainstorm.md](docs/brainstorms/2026-03-25-cycle-27-input-validation-generation-controls-brainstorm.md)
- Key decisions carried forward: VagueQueryError (not auto-refine), html.escape (not guard pattern), temperature on ResearchMode (not separate map)

### Prior Lessons

- `docs/solutions/security/non-idempotent-sanitization-double-encode.md` — sanitize once at boundary
- `docs/solutions/architecture/tiered-model-routing-planning-vs-synthesis.md` — route by task type
- LESSONS_LEARNED.md: "Temperature is a style knob, not an epistemic knob" — prompt semantics before generation controls

### Internal References

- `research_agent/query_validation.py` — `meaningful_words()`, `STOP_WORDS`
- `research_agent/errors.py` — exception hierarchy
- `research_agent/modes.py` — frozen dataclass pattern
- `docs/research/2026-03-09-entropy-fixes-roadmap.md` — C27 roadmap spec

## Feed-Forward

- **Hardest decision:** Gate placement. The brainstorm said `decompose.py` but SpecFlow analysis proved quick mode bypasses decompose entirely. Moving to `agent.research_async()` is the right call but changes the brainstorm's approach. Second hardest: dropping `summarize_temperature` — the roadmap spec included it but simplicity review proved YAGNI (1 call site, speculative default).
- **Rejected alternatives:** (1) Threshold of 3 meaningful words — rejected because "AI ethics" (2 words) is clearly valid. (2) `html.escape()` without `html.unescape()` — not actually idempotent, defeats the purpose. (3) Passing full `ResearchMode` to modules — breaks the existing pattern where modules receive primitive params. (4) Three temperature tiers — `summarize_temperature` serves 1 call site with no evidence it needs independent tuning. (5) New `validation.py` module — `query_validation.py` already exists and is the natural home.
- **Least confident:** The `html.unescape` entity normalization. Verified idempotent (`f(f(x)) == f(x)`) for all edge cases including `&copy;`, `&nbsp;`, `&#999999;`, `&nonexistent;`, and `&amp;amp;`. But `html.unescape` decodes ALL 2,231 HTML5 entities — `&copy;` becomes `©` and stays `©` (not re-escaped). Safe for prompt context but different from current behavior where only `&`, `<`, `>` are touched. The expanded 10-case idempotency test corpus covers this, but production web content may contain entity combinations we haven't seen.
