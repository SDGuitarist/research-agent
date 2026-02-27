---
title: "Iterative Review: What a Second 9-Agent Pass Reveals"
date: 2026-02-26
category: architecture
tags:
  - code-review
  - multi-agent
  - compound-engineering
  - state-management
  - api-parity
  - performance
  - sanitization
  - defense-in-depth
module: context.py, agent.py, sanitize.py, __init__.py, cli.py, synthesize.py
symptoms: |
  38 findings (2 P1, 17 P2, 19 P3) from 9-agent review of the same codebase
  that was reviewed once before. First review caught 10 skill issues + 7 context
  security issues (todos 054-060). Second review found 2 data corruption bugs,
  6-agent consensus on module-level cache, and API parity gaps.
severity: high
summary: |
  Second full 9-agent review of the background-research-agents feature after
  initial fixes (054-060) caught 38 new issues. Documents 5 patterns: complete
  the sanitization boundary, eliminate module-level mutable state, close
  API parity gaps, right-size models for sub-tasks, and use cross-agent
  consensus as severity signal. All 27 actionable todos resolved in 18 commits.
---

# Iterative Review: What a Second 9-Agent Pass Reveals

### Prior Phase Risk

> "The 16 untracked todo files with 'pending' in their filenames but
> `status: done` inside. They create noise in `git status` and could confuse
> future sessions scanning by filename."

Accepted risk: this is a file management concern, not a code quality issue.
The files were committed in `242bbcf`. No impact on patterns documented here.

## Risk Resolution

| Flagged Risk | What Happened | Lesson |
|---|---|---|
| Double-sanitization (performance-oracle P2 + security-sentinel P1) | Combined two agents' perspectives to realize `sanitize_content` is non-idempotent AND called per-consumer — active data corruption, not just future risk | Cross-agent synthesis reveals higher severity than any single agent sees |
| Module-level cache (6 agents flagged) | Replaced with per-run instance parameter; no thread safety, size, or test pollution issues remain | When 6/9 agents flag the same thing, fix it immediately — consensus is a strong signal |
| API parity gaps (agent-native-reviewer P2) | Exposed `skip_critique`, `max_sources` params + exported `CritiqueResult`, `ReportInfo`, `get_reports` | Features built for CLI first accumulate API debt; review catches it |
| Stale todo filenames | Committed all 16 todo files in doc cleanup commit | Housekeeping items left unresolved create noise for every future session |

## Context

The background-research-agents feature went through two review cycles:

1. **First review** (6 agents, skills-focused): 10 findings on skill
   instructions (shell escaping, timestamp collision, path traversal). Plus
   7 context security findings (054-060). All fixed.
2. **Second review** (9 agents, full codebase): 38 findings on the Python
   code that was untouched in the first pass. 55 raw findings before dedup.

The second pass was not redundant — it found 2 P1 bugs (data corruption,
unhandled exception) that the first pass missed entirely because it focused
on skills and security boundaries.

## Pattern 1: Complete the Sanitization Boundary

**Problem:** The first cycle documented the "sanitize once at boundary" pattern
and listed `context.py: load_context()` as the boundary for context files.
But `load_full_context()` returned raw content — sanitization happened at
4 consumer sites (synthesize_draft, synthesize_final, decompose, skeptic).
The boundary existed in documentation, not in code.

**Evidence:** Deep mode reports passed context through both `synthesize_draft`
and `synthesize_final`. Each called `sanitize_content()`. Result: `R&D`
became `R&amp;amp;D` in final reports.

**Fix (commit `76f0471`):** Moved `sanitize_content()` into `load_full_context()`
immediately after `content = path.read_text().strip()`. Removed all 4
per-consumer sanitize calls. Extracted `build_context_block()` helper into
`sanitize.py` to standardize the XML wrapping (commit `99c89ba`).

**Rule:** When you document a sanitization boundary, verify the implementation
matches. A pattern documented in a solution file but not enforced in code is
a false sense of security. Grep for the sanitization function — if it's called
at consumers, the boundary leaked.

## Pattern 2: Module-Level Mutable State is a Magnet for Bugs

**Problem:** `_context_cache` was a module-level `dict` in `context.py`.
Six of nine review agents flagged it independently — the strongest cross-agent
consensus in the entire review.

Issues identified:
- **Thread safety:** No lock. Concurrent async calls could corrupt it.
- **Size bound:** No eviction. Long-running processes accumulate entries.
- **Test pollution:** Tests relied on `tmp_path` uniqueness to avoid collisions.
- **Cross-instance leakage:** `clear_context_cache()` cleared state for ALL
  agent instances, not just the caller's.

**Fix (commit `1b615cc`):** Replaced with a `new_context_cache()` factory
function returning a fresh `dict`. `ResearchAgent.__init__` creates one per
instance. `load_full_context()` accepts an optional `cache` parameter —
callers that don't pass it get no caching (safe default).

**Rule:** Module-level mutable state (`_cache = {}`, `_instances = []`,
`_config = {}`) is almost always wrong in library code. It works in scripts
but breaks when the module is used as a library (concurrent callers, test
isolation, instance independence). Prefer instance-level state or explicit
parameter passing. If you must cache at module level, use
`functools.lru_cache` with a size bound.

**Why 6 agents flagged it:** Each agent saw it through a different lens —
thread safety (performance-oracle), test pollution (code-simplicity), API
boundary (architecture-strategist), data integrity (data-integrity-guardian).
The fix addresses all lenses because the root cause is singular: mutable state
at the wrong scope.

## Pattern 3: Close API Parity Gaps During Review

**Problem:** The public API (`__init__.py`) exposed `run_research()` and
`run_research_async()`, but:
- Accessed private attributes (`agent._last_source_count`,
  `agent._last_gate_decision`) instead of using public properties
- Did not expose `skip_critique` or `max_sources` parameters
- Did not export `CritiqueResult`, `ReportInfo`, or `get_reports`
- `ValueError` from `resolve_context_path()` propagated as an unhandled
  exception instead of `ResearchError`

**Fixes:**
- Commit `4463f94`: Added `last_source_count` and `last_gate_decision` as
  public `@property` on `ResearchAgent`
- Commit `c1991b9`: Added `skip_critique`/`max_sources` params to public API,
  exported missing types in `__all__`
- P1 ValueError fix: Changed CLI `except FileNotFoundError` to
  `except (FileNotFoundError, ValueError)` with clean error message

**Rule:** When building features CLI-first, API parity debt accumulates
silently. Each CLI flag that isn't mirrored in the public API is a gap that
blocks programmatic consumers (including agents). Review is the right time to
close these gaps — the agent-native-reviewer agent specifically checks for
this pattern.

**Checklist for new features:**
- [ ] Every CLI flag has a corresponding public API parameter
- [ ] Return types include all data consumers need (not just the report string)
- [ ] Private attributes accessed externally get public `@property` wrappers
- [ ] Exceptions at API boundaries are wrapped in `ResearchError`
- [ ] New types are exported in `__all__`

## Pattern 4: Right-Size Models for Sub-Tasks

**Problem:** `auto_detect_context()` used Sonnet for a trivial classification
task: given a query and a list of context file previews, pick the best match
or say "none." This added 1-3 seconds of latency to every run where `contexts/`
existed but no `--context` flag was given.

**Fix (commit `7f6073e`):** Two optimizations:
1. **Model downgrade:** Created `AUTO_DETECT_MODEL` constant using Haiku
   instead of Sonnet. The task is simple classification — Haiku handles it
   reliably at 10x lower latency.
2. **Short-circuit:** When `contexts/` contains exactly one `.md` file, skip
   the LLM call entirely and return that file. No ambiguity to resolve.

**Rule:** Not every LLM call needs the same model. Classification, routing,
and selection tasks rarely need the most capable model. Ask: "Would a human
need to think hard about this?" If not, use a smaller/faster model. Add
short-circuits for degenerate cases (0 or 1 options) that don't need an LLM
at all.

## Pattern 5: Cross-Agent Consensus Predicts Severity

**Observation from this review:**

| Finding | Agents that flagged it | Assigned severity |
|---------|----------------------|-------------------|
| Module-level cache | 6 agents | P2 |
| Path traversal string prefix | 3 agents | P2 |
| Private attribute access | 2 agents | P2 |
| Context sanitization architecture | 2 agents | P2 → P1 (combined) |
| Double-sanitization bug | 2 agents | P1 |

Findings flagged by 3+ agents were always P2 or higher. Findings flagged by
only 1 agent were more likely to be P3.

**Rule for multi-agent review triage:** When synthesizing findings across
agents, weight cross-agent consensus heavily. A finding that independently
appears in 3+ agent reports represents a genuine architectural concern, even
if individual agents rated it P3. One agent seeing something could be noise;
three agents seeing it is signal.

**Corollary:** When two agents flag related-but-different aspects of the same
issue (performance-oracle sees "redundant work," security-sentinel sees
"architectural risk"), synthesize them — the combined perspective often reveals
higher severity than either alone. This is how P1 #2 (double-sanitization)
was correctly escalated.

## What the Second Pass Caught That the First Missed

| Category | First pass (6 agents) | Second pass (9 agents) |
|----------|----------------------|----------------------|
| Focus | Skills + security boundaries | Full Python codebase |
| P1 findings | 2 (shell injection, timestamp) | 2 (data corruption, unhandled exception) |
| Architectural findings | 0 | 5 (cache, sanitization boundary, API parity, section branching, context resolution duplication) |
| Performance findings | 0 | 3 (auto-detect latency, duplicate source building, token approximation) |
| Total | 10 | 38 |

**Why:** The first pass was scoped to skill instructions and security
concerns. The second pass cast a wider net. The architectural and performance
findings require agents that read the full codebase, not just the diff.

**Lesson:** Scoped reviews are efficient but create blind spots. A full
codebase review after feature stabilization catches architectural debt that
incremental reviews miss. The compound engineering loop should include at
least one full review per feature, not just scoped reviews of each commit.

## Metrics

| Metric | Value |
|--------|-------|
| Review agents | 9 |
| Raw findings | ~55 |
| Unique findings (after dedup) | 38 |
| P1 Critical | 2 |
| P2 Important | 17 |
| P3 Nice-to-have | 19 |
| Actionable todos created | 27 |
| Todos resolved | 27 (100%) |
| Fix commits | 18 (76f0471..242bbcf) |
| Tests (final count) | 714 passing |
| Cross-agent consensus findings | 5 (flagged by 2+ agents) |

## Cross-References

- [Non-Idempotent Sanitization](../security/non-idempotent-sanitization-double-encode.md) — First instance of this bug (critique_guidance path); this cycle completed the fix (context path)
- [Context Path Traversal Defense](../security/context-path-traversal-defense-and-sanitization.md) — First review's security fixes (054-060); this cycle refined with `is_relative_to`
- [Skill-Only Features](skill-only-features-background-research.md) — First review's skill patterns; second review focused on Python code
- [Self-Enhancing Agent Patterns](self-enhancing-agent-review-patterns.md) — Prior review cycle with similar multi-agent approach; Pattern 3 (thread parameters) reappeared here as Pattern 2 (module-level state)

## Three Questions

1. **Hardest pattern to extract from the fixes?** Pattern 1 (complete the
   sanitization boundary). The first cycle's solution doc explicitly listed
   `context.py: load_context()` as the sanitization site for context files.
   But the implementation didn't match — `load_full_context()` returned raw
   content. Extracting the pattern required admitting that a documented
   boundary can be wrong, and that "sanitize at boundary" is only as good as
   the boundary actually being implemented.

2. **What did you consider documenting but left out, and why?** Individual
   P3 fixes (token approximation, f-string logging, synthesize branching,
   docstring gaps). These are one-off cleanup items already tracked in the
   review summary. Documenting them here would dilute the architectural
   patterns. The P3 list in REVIEW-SUMMARY.md serves as the reference.

3. **What might future sessions miss that this solution doesn't cover?** The
   relationship between review scope and finding quality. This doc shows that
   a second full review found 38 new issues — but doesn't answer when
   diminishing returns kick in. A third full review might find 5 issues or
   50. There's no heuristic for "this codebase has been reviewed enough."
   The pragmatic answer is: review until P1 count drops to zero, then stop.
