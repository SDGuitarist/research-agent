---
title: "Patterns from the Self-Enhancing Agent Review"
date: 2026-02-23
category: architecture
tags:
  - code-review
  - exception-handling
  - prompt-injection
  - async
  - YAGNI
  - parameter-threading
  - token-budget
  - testing
module: agent.py, critique.py, context.py, cli.py, relevance.py, synthesize.py
symptoms: |
  34 findings across 3 review batches. Bare except clauses, mutable instance state
  for transient data, blocking I/O on async event loop, inconsistent parameter names,
  second-order prompt injection via YAML, YAGNI domain filtering, duplicated constants.
severity: medium
summary: |
  Seven reusable patterns extracted from fixing 23 review findings across 6 batches.
  Covers exception hygiene, state threading, async boundaries, prompt injection chains,
  token budget registration, YAGNI removal, and test quality.
---

# Patterns from the Self-Enhancing Agent Review

## Context

The self-enhancing agent feature (self-critique + adaptive prompts) was added in a
single PR. Multi-agent review found 34 findings (4 P1, 19 P2, 11 P3). Fixing them
took 7 commits across 6 batches. This document captures the reusable patterns.

## Pattern 1: Specific Exception Handling

**Problem:** `except (CritiqueError, Exception)` catches everything, hiding bugs.

**Fix:** List the actual failure modes: `except (OSError, yaml.YAMLError)`. Then remove
`CritiqueError` entirely since nothing raised it.

**Rule:** When writing a try/except, ask "what can actually go wrong here?" and list
those specific exceptions. If you can't name them, you don't understand the failure modes yet.

## Pattern 2: Thread Parameters, Don't Mutate State

**Problem:** `self._critique_context` was set in `_research_async` and read later in
`_evaluate_and_synthesize`. If the agent is reused, stale state leaks between runs.

**Fix:** Made `critique_context` a local variable and threaded it as a parameter through
`_research_with_refinement` -> `_research_deep` -> `_evaluate_and_synthesize`.

**Rule:** Transient per-run data should be local variables passed through parameters, not
instance attributes. Instance state is for configuration that's set once at init. If
you `self.x = ...` inside a method and read it in a different method, that's a coupling
smell — pass it as a parameter instead.

## Pattern 3: Async/Sync Boundary Awareness

**Problem:** `load_critique_history()` does ~20 blocking syscalls (glob, stat, read, YAML
parse). `_run_critique()` makes a 30-second Claude API call. Both ran directly on the
async event loop.

**Fix:** Wrapped both in `await asyncio.to_thread(...)`.

**Rule:** Any function that does file I/O, network calls, or CPU work over ~10ms should
be wrapped in `asyncio.to_thread()` when called from async code. Grep for `def ` (not
`async def`) functions called inside `async def` methods — those are the suspects.

## Pattern 4: Unify Parameter Names Across Modules

**Problem:** The same concept (critique guidance) had three different names:
- `critique_context` in agent.py
- `scoring_adjustments` in relevance.py
- `lessons_applied` in synthesize.py

**Fix:** Renamed all to `critique_guidance` across 4 production files and 4 test files.

**Rule:** When data flows through multiple modules, use one name everywhere. Grep for the
concept before naming a new parameter — if three modules already handle it, they should
agree on what it's called.

## Pattern 5: Second-Order Prompt Injection via Saved Data

**Problem:** Attack chain: malicious web content -> Claude generates weakness string ->
saved to YAML -> loaded in future run -> injected into prompt unsanitized.

**Fix:** Applied `sanitize_content()` to each weakness string when loading from YAML,
not just when saving.

**Rule:** Sanitize at the point of use (read), not just at the point of creation (write).
Data written today is read by a different code path tomorrow. The write path may have
sanitized, but the read path shouldn't trust that. Defense in depth: sanitize both
when writing and when reading.

## Pattern 6: Register New Components in the Token Budget

**Problem:** `critique_guidance` was injected into prompts but not registered in the
token budget system, so it couldn't be pruned when prompts were too long.

**Fix:** Added `"critique_guidance": 2` to `COMPONENT_PRIORITY` and included it in the
budget components dict before pruning.

**Rule:** Every new piece of text that goes into a prompt must be registered in the
token budget. This is easy to forget because prompts work fine in testing (short inputs).
They fail in production when real data pushes past the limit and budget pruning doesn't
know about the unregistered component.

## Pattern 7: Remove YAGNI, Don't Just Ignore It

**Problem:** `load_critique_history` had a `domain` parameter for filtering critiques by
topic. No caller ever passed it. The `_CRITIQUE_DIMENSIONS` set in context.py duplicated
the `DIMENSIONS` tuple from critique.py.

**Fix:** Removed the `domain` parameter and its filtering logic. Removed
`_CRITIQUE_DIMENSIONS` and used `DIMENSIONS` directly via import.

**Rule:** Unused parameters and duplicated constants accumulate. During review, if a
parameter has zero callers, remove it. If a constant is defined in two places, import
from the canonical source. "We might need it later" is not a reason to keep code — adding
a parameter later is a one-line change, but maintaining dead code forever is not free.

## Prevention Checklist

For any new pipeline feature, verify:

- [ ] All `except` clauses list specific exception types
- [ ] Per-run data is local, not stored on `self`
- [ ] Blocking calls inside async code are wrapped in `asyncio.to_thread()`
- [ ] The same concept uses the same parameter name in every module
- [ ] Data loaded from files is sanitized before prompt injection
- [ ] New prompt components are registered in the token budget
- [ ] No unused parameters or duplicated constants
- [ ] Tests exercise the real code path, not a reimplementation

## Three Questions

1. **Hardest pattern to extract from the fixes?** Pattern 5 (second-order prompt
   injection). The attack chain crosses three boundaries — web content -> AI output ->
   YAML file -> future prompt — making it hard to see from any single module. The fix
   is simple (sanitize at read), but the pattern itself is non-obvious.

2. **What did I consider documenting but left out, and why?** CLI parity (every feature
   should have a CLI flag). It came up in P1 #2-4 and P2 #18, but it's more of a general
   UX principle than a code pattern specific to this review. Also omitted individual test
   quality guidance — "test the real code path" is already in Pattern 2's tests and doesn't
   need its own section.

3. **What might future sessions miss that this solution doesn't cover?** The P3 findings
   (#24-34) were all skipped. Some are real improvements (f-string loggers, configurable
   critique threshold, quick mode skipping history load). A future session should triage
   them rather than forgetting they exist — they're listed in HANDOFF.md.
