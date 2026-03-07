# Codex Plan Review Handoff — Cycle 24: Swappable Context Profiles

**Branch:** `main`
**Date:** 2026-03-06
**Phase:** Plan review (pre-implementation)
**Tests:** 920 passing (`python3 -m pytest tests/ -v`)

## What This Plan Proposes

Add 4 new YAML frontmatter fields to context files (`contexts/*.md`) and a `--list-contexts` CLI flag. The existing context system already has YAML parsing, `--context` flag, auto-detection, and `ContextResult`/`ReportTemplate` dataclasses. This cycle extends it with structured fields that affect pipeline behavior.

## Plan Document

`docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md`

## Brainstorm Document

`docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md`

## Key Architectural Decisions to Validate

### 1. New `ContextProfile` dataclass (separate from `ReportTemplate`)

**Decision:** Create a new `ContextProfile` frozen dataclass in `context_result.py` with 4 fields (`preferred_domains`, `blocked_domains`, `gap_schema`, `synthesis_tone`). Carried on `ContextResult` as `profile: ContextProfile | None = None`.

**Rationale:** `ReportTemplate` holds report structure (section headings, context_usage). Profile fields are operational pipeline parameters (domain filtering, scoring boost, tone). Different concerns → different dataclass.

**Review focus:** Is separating into two dataclasses the right call, or would extending `ReportTemplate` be simpler? Does the `ContextProfile` API feel consistent with existing patterns (`ReportTemplate`, `ResearchMode`)?

### 2. Blocked domains: hard filter at search level

**Decision:** `filter_blocked_urls(results, blocked_domains)` in `search.py`, called after every search call site in `agent.py` (6+ locations). Applied before `_split_prefetched()`. Suffix matching with dot-boundary.

**Review focus:**
- Is `search.py` the right location, or should filtering happen in `agent.py`?
- Is suffix matching correct? (`example.com` blocks `sub.example.com` but not `notexample.com`)
- Are there search paths we missed? Key call sites to verify:
  - `_research_with_refinement()` pass 1 + pass 2
  - `_research_deep()` pass 1 + pass 2
  - `_search_sub_queries()` (decomposition + iteration)
  - `_try_coverage_retry()`

### 3. Preferred domains: post-aggregation boost

**Decision:** Apply +0.5 boost to `source["score"]` after `_aggregate_by_source()` in `evaluate_sources()`. Keep `SourceScore.score` as `int`; use transient `_boosted_score` float for gate comparison only.

**Review focus:**
- Is +0.5 the right magnitude? On a 1-5 scale with cutoff at 3, this means a score-3 source becomes 3.5 (stays in), score-2 becomes 2.5 (still out). Is that the desired behavior?
- Is the transient `_boosted_score` approach clean, or would changing `SourceScore.score` to `float` be more honest?
- Should `preferred_domains` be a new parameter on `evaluate_sources()`, or passed through the mode/context object?

### 4. Synthesis tone: presets + free-text + XML boundary

**Decision:** Three presets (`executive`, `technical`, `casual`) as a constants dict. Unrecognized strings treated as free-text. Sanitized with `sanitize_content()` and wrapped in `<tone_instruction>` XML tag. Injected into `synthesize_report()` and `synthesize_final()` only (NOT `synthesize_draft()` or `synthesize_mini_report()`).

**Review focus:**
- Are the preset definitions appropriate for their target audiences?
- Is `<tone_instruction>` XML wrapping sufficient defense for free-text tone, given it goes into the `<instructions>` zone (trusted)?
- Is skipping `synthesize_draft()` correct? The draft is designed for objective factual analysis, but should tone affect word choice even there?

### 5. Gap schema: CLI precedence

**Decision:** CLI `--schema` takes precedence over profile `gap_schema`. Warning logged if both are set. `gap_schema` path validated (reject `..`, absolute paths), resolved relative to project root.

**Review focus:**
- Is "resolve relative to project root" correct, or should it resolve relative to the context file's directory?
- Is the precedence rule intuitive? Could it surprise users?

## Implementation Sessions (5 total, ~280 lines)

| Session | Scope | Lines | Key files |
|---------|-------|-------|-----------|
| 1 | `ContextProfile` dataclass + YAML parsing | ~80 | `context_result.py`, `context.py`, `pfe.md` |
| 2 | `blocked_domains` hard filter | ~60 | `search.py`, `agent.py` |
| 3 | `preferred_domains` relevance boost | ~40 | `relevance.py`, `agent.py` |
| 4 | `synthesis_tone` presets + injection | ~50 | `synthesize.py`, `agent.py` |
| 5 | `gap_schema` fallback + `--list-contexts` CLI | ~50 | `agent.py`, `cli.py` |

## Flagged Risks (from brainstorm + plan Feed-Forward)

1. **Blocked domains coverage** — 6+ search call sites in `agent.py`. Missing one means blocked content leaks in specific modes. Plan says grep for all `search(` calls.
2. **Preferred domains boost distortion** — +0.5 on 1-5 scale. Plan says it's small enough not to distort, but should we verify with test data?
3. **Tone prompt injection** — Free-text goes into `<instructions>` zone. Plan says context files are trusted-author input. Is that assumption safe?

## How to Review

```bash
# Read the plan
cat docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md

# Read the brainstorm for rationale
cat docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md

# Understand existing patterns
cat research_agent/context_result.py
cat research_agent/context.py
cat research_agent/relevance.py
```

For each architectural decision, evaluate:
1. **Correctness** — Does the proposed approach handle all edge cases?
2. **Consistency** — Does it follow existing codebase patterns?
3. **Simplicity** — Is there a simpler alternative that achieves the same goal?
4. **Safety** — Any prompt injection, path traversal, or type safety risks?
5. **Completeness** — Are there gaps the plan didn't address?

## Key Codebase Conventions

- Mock where the name is imported FROM, not where it's used
- Frozen dataclasses for configuration (`ResearchMode`, `ReportTemplate`)
- `sanitize_content()` at boundary, never double-sanitize
- Additive pattern: new stages layer on without changing downstream modules
- Three-layer prompt injection defense: sanitize + XML boundaries + system prompt
- `ContextResult` uses four-state enum (loaded/not_configured/empty/failed)

## Plan Reference

Full plan with acceptance criteria and test counts: `docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md`
