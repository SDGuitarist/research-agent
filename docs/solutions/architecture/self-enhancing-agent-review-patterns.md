---
title: "Self-Enhancing Agent: Patterns from Multi-Agent Review"
date: 2026-02-23
category: architecture
tags:
  - self-critique
  - agent-native
  - prompt-injection
  - async
  - code-review
  - compound-engineering
  - YAGNI
  - exception-handling
  - parameter-threading
  - token-budget
  - testing
module: agent.py, critique.py, context.py, cli.py, relevance.py, synthesize.py
symptoms: |
  34 findings from 9-agent review of the self-critique feature. Key clusters:
  agent observability gap, convention regression, sync/async mismatch,
  naming debt, dead code, mutable state leaks, prompt injection holes.
severity: high
summary: |
  Multi-agent code review of the self-critique feedback loop caught 34 issues
  (4 P1, 19 P2, 11 P3). Fixed across 7 commits in 6 batches. Documents 10
  reusable patterns, positive findings, and process learnings.
---

# Self-Enhancing Agent: Patterns from Multi-Agent Review

### Prior Phase Risk

> "The `--no-critique` flag has no dedicated test. The existing
> `test_quick_mode_skips_critique` test covers the early-return path in
> `_run_critique`, and the `skip_critique` check uses the same code path."

Accepted risk: the code path is shared with quick mode's skip logic, which is
tested. A dedicated test would be a P3 improvement, not a blocker.

## Context

The self-critique feature (Tier 2 adaptive prompts) adds a post-report quality
evaluation loop. After each research run, Claude scores 5 dimensions, saves
YAML, and future runs load patterns to improve prompts. Built in 4 commits
(+1091 lines), reviewed by 9 specialized agents (90 raw findings, 34 unique
after dedup), fixed in 7 commits across 6 batches.

## Pattern 1: Agent Observability is Non-Negotiable

**Problem:** The critique system worked internally but was invisible to CLI
users and programmatic consumers. No way to invoke it, see results, skip it,
or read history. (P1 #2-4, P2 #14, #18 — the highest-impact cluster.)

**Rule:** Every feature needs three agent-facing surfaces:
1. **Invoke** — Can the agent call it independently? (`--critique <path>`)
2. **Observe** — Can the agent see the output? (print summary, return in API)
3. **Control** — Can the agent skip or configure it? (`--no-critique`)

Features without all three are incomplete for agent use.

## Pattern 2: Specific Exception Handling

**Problem:** `except (CritiqueError, Exception)` catches everything, hiding
bugs. `CritiqueError` was defined but never raised — dead infrastructure.

**Fix:** Listed actual failure modes: `except (OSError, yaml.YAMLError)`.
Removed `CritiqueError` entirely.

**Rule:** When writing try/except, ask "what can actually go wrong here?" and
list those specific exceptions. If you can't name them, you don't understand
the failure modes yet.

## Pattern 3: Thread Parameters, Don't Mutate State

**Problem:** `self._critique_context` was set in `_research_async` and read
later in `_evaluate_and_synthesize`. If the agent is reused, stale state leaks.

**Fix:** Made it a local variable, threaded as a parameter through the call
chain: `_research_async` -> `_evaluate_and_synthesize` -> downstream stages.

**Rule:** Transient per-run data should be local variables passed through
parameters, not instance attributes. If you `self.x = ...` inside a method
and read it in a different method, that's a coupling smell.

## Pattern 4: Async/Sync Boundary Awareness

**Problem:** `load_critique_history()` does ~20 blocking syscalls (glob, stat,
read, YAML parse). `_run_critique()` makes a 30-second Claude API call. Both
ran directly on the async event loop.

**Fix:** Wrapped both in `await asyncio.to_thread(...)`.

**Rule:** Any function that does file I/O, network calls, or CPU work over
~10ms should be wrapped in `asyncio.to_thread()` when called from async code.
Grep for `def ` (not `async def`) functions called inside `async def` methods.

## Pattern 5: One Name Per Data, Across All Stages

**Problem:** The same critique context string was called `critique_context` in
decompose, `scoring_adjustments` in relevance, and `lessons_applied` in
synthesize. Three names for one thing obscure data lineage.

**Fix:** Unified to `critique_guidance` everywhere. Added consistent
`<scoring_guidance>` XML tags in relevance to match other stages.

**Rule:** When data flows through a pipeline, use one name end-to-end. Grep
for the concept before naming a new parameter — if three modules handle it,
they should agree on what it's called.

## Pattern 6: Second-Order Prompt Injection via Saved Data

**Problem:** Attack chain: malicious web content -> Claude generates weakness
string -> saved to YAML -> loaded in future run -> injected into prompt
unsanitized. The write path truncated to 200 chars, but the read path trusted
the stored data.

**Fix:** Applied `sanitize_content()` to each weakness string when loading
from YAML, not just when saving.

**Rule:** Sanitize at the point of use (read), not just at creation (write).
The three-layer defense (sanitize + XML boundaries + system prompt warning)
must be applied at every injection point. Don't rely on source trust — even
data written by your own code may have been influenced by attacker content.

## Pattern 7: Register New Components in the Token Budget

**Problem:** `critique_guidance` was injected into prompts but not registered
in the token budget system. The budget pruner couldn't prune it when tokens
were tight.

**Fix:** Added `"critique_guidance": 2` to `COMPONENT_PRIORITY` and included
it in `budget_components` before pruning.

**Rule:** Every piece of text injected into a prompt must be registered in the
token budget. This is easy to forget because prompts work fine in testing
(short inputs). They fail in production when real data pushes past the limit.

## Pattern 8: Remove YAGNI, Don't Just Ignore It

**Problem:** `load_critique_history` had a `domain` parameter for filtering
critiques by topic — no caller ever passed it. `_CRITIQUE_DIMENSIONS` in
context.py duplicated `DIMENSIONS` from critique.py.

**Fix:** Removed the `domain` parameter and its filtering logic. Replaced
`_CRITIQUE_DIMENSIONS` with import from `critique.py`.

**Rule:** Unused parameters and duplicated constants accumulate. If a parameter
has zero callers, remove it. If a constant is defined in two places, import
from the canonical source. Adding a parameter later is a one-line change;
maintaining dead code forever is not free.

## Pattern 9: Test the Agent, Not Your Mocks

**Problem:** `TestAgentCritiqueHistoryThreading` manually set
`agent._critique_context = critique_ctx.content` instead of calling the actual
method. Tested Python assignment, not agent behavior.

**Fix:** Replaced with integration tests that mock dependencies (API calls,
file I/O) and assert critique_guidance reaches actual downstream methods.

**Rule:** Mock the agent's dependencies, not the agent itself. If your test
manually sets private state, it's testing the language runtime, not your code.

## Pattern 10: Return Types for All Consumers

**Problem:** `research()` returned `str`. Programmatic consumers had to reach
into private `self._last_critique` to get quality data.

**Fix:** Added `CritiqueResult` field to `ResearchResult` dataclass. Both CLI
and programmatic consumers get structured data from the same return path.

**Rule:** Design return types for your actual consumers. A shared dataclass
unifies the CLI path and the programmatic path. Don't make consumers reach
into private state.

## Positive Patterns (Confirmed by Review)

These strengths were noted by multiple agents and should be maintained:

1. **Graceful degradation** — Critique never crashes the pipeline. Quick mode
   skips entirely. API failures return defaults.
2. **Additive integration** — New module layers on without changing downstream.
   Mirrors skeptic.py pattern from Cycle 16.
3. **Frozen dataclasses** — CritiqueResult matches ResearchMode, ContextResult.
   Immutable by design.
4. **YAML safe_load + schema validation** — Defense-in-depth against code
   execution and malformed data.
5. **Slug sanitization** — `re.sub(r"[^a-z0-9_]", "", slug)` prevents path
   traversal in critique filenames.
6. **Self-improving feedback loop** — Past critiques influence future behavior.
   Novel agent-native pattern.

## Process Learning: Don't Skip Phases

The compound engineering loop was violated — Plan phase was skipped. Symptoms:

- Commits 3-9x oversized (460, 334 lines vs. 50-100 convention)
- Known anti-patterns reintroduced (bare `except Exception`)
- Design choices went undocumented

The 6 fix batches proved the intended large changes *could* be broken into
smaller, focused commits. Skipping Plan doesn't save time — it guarantees
rework in Review.

## Prevention Checklist

For any new pipeline feature, verify:

- [ ] Feature has invoke / observe / control surfaces for agents
- [ ] All `except` clauses list specific exception types
- [ ] Per-run data is local, not stored on `self`
- [ ] Blocking calls in async code wrapped in `asyncio.to_thread()`
- [ ] Same concept uses same parameter name in every module
- [ ] Data loaded from files sanitized before prompt injection
- [ ] New prompt components registered in token budget
- [ ] No unused parameters or duplicated constants
- [ ] Tests exercise real code paths, not reimplementations
- [ ] Return types expose data to all consumers (not just CLI)

## Metrics

| Metric | Value |
|--------|-------|
| Raw findings (9 agents) | 90 |
| Unique findings (after dedup) | 34 |
| P1 Critical | 4 (all fixed in batch 1) |
| P2 Important | 19 (fixed across batches 2-6 + final commit) |
| P3 Nice-to-have | 11 (deferred, tracked in REVIEW-SUMMARY.md) |
| Tests added during fixes | +50 (558 → 608) |
| Fix commits | 7 focused commits |

## Three Questions

1. **Hardest pattern to extract from the fixes?** Pattern 6 (second-order
   prompt injection). The attack chain crosses three boundaries — web content
   -> AI output -> YAML file -> future prompt — making it hard to see from any
   single module. The fix is simple (sanitize at read), but the pattern itself
   is non-obvious.

2. **What did I consider documenting but left out, and why?** The 11 P3
   findings (f-string loggers, duplicate test fixtures, bool bypass in
   validation, configurable critique threshold). They're real issues but don't
   represent patterns — they're one-off cleanup items. Documenting them would
   dilute signal. They're tracked in REVIEW-SUMMARY.md for a future cleanup.

3. **What might future sessions miss that this solution doesn't cover?** The
   review tested code quality but never tested critique *output quality* —
   whether Claude produces useful scores given process metadata. The feedback
   loop is wired correctly; whether it produces signal is an empirical question
   that requires running real reports and evaluating score trends over time.
