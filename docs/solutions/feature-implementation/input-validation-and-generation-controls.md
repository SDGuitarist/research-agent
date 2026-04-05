---
title: "Input Validation & Generation Controls: idempotent sanitization, vague query gate, per-task temperature"
date: 2026-04-05
category: feature-implementation
tags:
  - sanitization
  - input-validation
  - temperature-controls
  - frozen-dataclass
  - prompt-injection-defense
  - MCP-parity
module: research_agent/sanitize.py, research_agent/query_validation.py, research_agent/modes.py, research_agent/agent.py, research_agent/mcp_server.py
symptoms: |
  1. Double-sanitization corrupted content (& → &amp; → &amp;amp;) — documented since Cycle 20.
  2. Vague queries like "stuff" consumed API credits with no useful output.
  3. All LLM calls used API-default temperature regardless of task type.
severity: medium
summary: |
  Three changes: (1) html.unescape() before XML escaping makes sanitize_content idempotent,
  (2) VAGUE_WORDS frozenset + meaningful_words() rejects empty/vague queries before any LLM work,
  (3) three temperature fields on ResearchMode (planning=0.2, summarize=0.5, synthesis=0.8)
  threaded to 16 API call sites. Review found 5 issues (0 P1, 3 P2, 2 P3), all fixed.
---

# Input Validation & Generation Controls (Cycle 27)

## What Was Built

Three independent features from the entropy roadmap (Cycle 27 scope):

### 1. Idempotent Sanitization

**Problem:** `sanitize_content()` was not idempotent — calling it twice double-encoded ampersands. This was a known bug documented in Cycle 20 as "defense-in-depth is a bug" when layers independently sanitize.

**Fix:** One line added to `sanitize.py`: `html.unescape(text)` before the 3 `.replace()` calls. This normalizes any pre-escaped entities back to raw characters, then re-escapes once.

**Key insight:** `html.unescape()` handles ALL HTML entities (named, decimal, hex), not just the 3 we target. This is correct — entities like `&nbsp;` become their Unicode character and pass through unchanged, since only `&`, `<`, `>` are re-escaped.

### 2. Vague Query Detection Gate

**Problem:** Queries like "stuff" or "best things" consumed API credits (decomposition, search, summarization) before producing useless results.

**Fix:** `check_query_vagueness()` in `query_validation.py` — pure Python, no LLM call. Rejects queries with fewer than 2 meaningful words or where all meaningful words are in a `VAGUE_WORDS` frozenset. Called at top of `_research_async()` before any LLM work.

**Design choices:**
- Returns `VagueQueryResult` frozen dataclass (not a direct raise) — keeps validation pure and testable
- Reuses existing `meaningful_words()` — inherits punctuation stripping, hyphen splitting, stop word removal
- `words <= VAGUE_WORDS` (subset check) means queries with ANY specific word pass — "best Python frameworks" is fine
- `VagueQueryError(ResearchError)` propagates through existing MCP error handler automatically

**Known limitation:** "tell me about technology" passes (2 meaningful words, neither in vague set). Accepted — ship heuristic, monitor, tighten later.

### 3. Per-Task Temperature Controls

**Problem:** All 16 Anthropic API calls used the default temperature regardless of task type. Classification tasks (decompose, relevance scoring) should be deterministic; synthesis tasks (report generation, skeptic review) benefit from creative variation.

**Fix:** Three float fields on `ResearchMode` frozen dataclass:
- `planning_temperature: 0.2` — classification, routing, scoring (10 call sites)
- `summarize_temperature: 0.5` — chunk summarization (1 call site via wrapper chain)
- `synthesis_temperature: 0.8` — report synthesis, skeptic, critique, mini-reports (5 call sites)

**Threading pattern:** Matches Cycle 21's model routing precedent — `temperature: float = 1.0` as default parameter on each function signature. Agent.py passes `self.mode.*_temperature` at each call site. Functions that already take `mode` (like `evaluate_sources`) read the temperature internally.

## Key Patterns

### Pattern: Unescape-then-escape for idempotent sanitization
When sanitizing content that may have been pre-sanitized, normalize first (`html.unescape`), then apply your escaping. This is cheaper and more correct than tracking "has this been sanitized" state.

### Pattern: Fail-fast validation before expensive work
Place input validation gates as early as possible in the pipeline. `check_query_vagueness()` runs before context loading, before LLM decomposition, before search — zero cost for rejected queries.

### Pattern: Per-param threading for cross-cutting concerns
When adding a config value that touches many modules (model, temperature), add it as a defaulted parameter on each function rather than passing the entire config object. This avoids coupling leaf modules to the config dataclass while following the established pattern.

### Pattern: Frozen dataclass for structured validation results
`VagueQueryResult(is_valid, message)` separates detection from handling. The validation module stays pure (no imports from errors.py), the orchestrator decides how to handle, and tests assert on fields directly without `pytest.raises`.

## Review Findings

5 findings (0 P1, 3 P2, 2 P3), all fixed in one commit:

| # | Finding | Fix |
|---|---------|-----|
| 127 | `generate_insufficient_data_response` used planning_temperature (0.2) for user-facing prose | Changed to `summarize_temperature` (0.5) |
| 128 | No test for the specific prompt injection attack vector the sanitization fix defends against | Added 4 tests: named/numeric/hex/mixed entity boundary breakout |
| 129 | MCP standalone tools (`critique_report`, `generate_followups`) used temperature=1.0 | Added explicit temperatures (0.8 and 0.2) |
| 130 | `list_research_modes` didn't show temperature values | Added temp info to output |
| 131 | MCP instructions didn't mention vague query rejection | Added one sentence |

**Cross-agent convergence:** All 7 review agents agreed the three features are architecturally sound. The only real findings were at the edges — a temperature misclassification (#127), missing regression tests (#128), and MCP parity gaps (#129-131).

## Risk Resolution

**Brainstorm risk:** "The vague word set heuristic misses subtler vague queries like 'tell me about technology'."

**What happened:** Accepted as designed. The heuristic catches the degenerate cases (empty, single-word, all-vague-words). The "technology" case has 2 meaningful non-vague words, so it passes. The set is a frozen constant — easy to update if false negatives surface in practice.

**Plan risk:** "The 3-deep wrapper chains for summarization and skeptic. Existing tests that mock at intermediate boundaries may need mock call expectations updated."

**What happened:** The `temperature: float = 1.0` default on every function meant all existing mocks survived unchanged. The Codex review caught 14 missing test cases for temperature defaults/validation/plumbing, which were added before the Claude Code review.

**Review risk:** "`test_mcp_server.py` couldn't be verified (missing fastmcp dependency)."

**What happened:** MCP server code was modified (temperature defaults, instructions, mode listing). Tests could not be run to verify. The changes are simple keyword additions that follow the existing patterns — low risk but noted.

## Three Questions

1. **Hardest pattern to extract from the fixes?** The temperature task-type classification. 15 of 16 call sites were obvious (classification vs synthesis), but `generate_insufficient_data_response` was genuinely ambiguous — it's a "classification decision" (insufficient data) that produces "user-facing prose" (the explanation). The review correctly identified this as summarization, not planning.

2. **What did you consider documenting but left out?** The `html.unescape()` performance characteristics. The performance oracle ran a thorough analysis showing sub-microsecond overhead per call, negligible vs network/API latency. Not worth a pattern — it's just "string operations are fast compared to HTTP."

3. **What might future sessions miss that this solution doesn't cover?** The MCP `test_mcp_server.py` gap. Three of the five review fixes touched `mcp_server.py`, but none could be verified with MCP-specific tests. If `fastmcp` is installed in a future cycle, those tests should be run. Also: when adding new Anthropic API call sites, remember to thread temperature — there's no linter to catch a missing `temperature=` kwarg.
