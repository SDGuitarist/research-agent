# Brainstorm: P3 Triage — Self-Enhancing Agent Review

**Date:** 2026-02-23
**Source:** Review findings #24-34 from `docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md`
**Also:** Skipped P2s #19, #20, #22

---

### Prior Phase Risk

> "The P3 findings (#24-34) are all deferred. Some are real improvements (f-string loggers, configurable critique threshold). They should be triaged, not forgotten."

This brainstorm addresses that directly — triaging each finding into do-now, do-later, or skip.

---

## Findings Inventory

### P3 Findings (11 items)

| # | Finding | Files | Effort |
|---|---------|-------|--------|
| 24 | f-string in logger calls | ~40 calls across 10 files | High churn |
| 25 | Duplicate scores tuple in CritiqueResult | critique.py | Low |
| 26 | Double sanitization of critique context | context.py, decompose.py | Low |
| 27 | Timestamp collision in critique filename | critique.py | Low |
| 28 | `bool` bypasses `isinstance(val, int)` validation | context.py:153 | Trivial |
| 29 | Quick mode loads critique history unnecessarily | agent.py:203 | Trivial |
| 30 | Redundant sanitize calls in per-source scoring | relevance.py:123-137 | Low |
| 31 | Critique threshold not configurable | context.py (hardcoded 3.0 in CritiqueResult.overall_pass) | Medium |
| 32 | Survivorship bias in pattern summary | context.py:171 | Medium |
| 33 | Various test quality issues | test_relevance.py, test_decompose.py, test_critique.py | Low |
| 34 | Minor code tidiness (grab bag) | Various | Low |

### Skipped P2s (3 items, process-only)

| # | Finding | Type |
|---|---------|------|
| 19 | Missing plan document in `docs/plans/` | Process gap (already noted) |
| 20 | Commit size convention violated | Process (future discipline) |
| 22 | Critique saved before report persisted | Acceptable for CLI |

---

## Triage Decisions

### Do Now (1 session, ~60 lines)

These are real bugs or clear improvements with low effort:

**#28 — bool/int validation bug** (Correctness)
- `True` and `False` are `int` subclasses in Python, so `isinstance(True, int)` returns `True`
- A critique YAML with `source_diversity: true` (boolean) would pass validation as score 1
- Fix: `if isinstance(val, bool) or not isinstance(val, int)` at context.py:153
- **Verdict: Fix — it's a real bug**

**#29 — Quick mode loads critique history** (Performance)
- Quick mode skips critique entirely but still reads all YAML files from disk
- Wasted I/O on every quick run
- Fix: `if self.mode.name != "quick":` guard at agent.py:202
- **Verdict: Fix — simple guard, measurable improvement**

**#26 — Double sanitization** (Code quality)
- `context.py:225` sanitizes the full summary, but individual weakness strings are already sanitized at `context.py:216`
- `decompose.py:142` re-sanitizes `critique_guidance` that was already sanitized in context.py
- Fix: Remove the redundant downstream calls
- **Verdict: Fix — redundant work and confusing for future readers**

**#30 — Redundant sanitize in per-source scoring loop** (Performance)
- `relevance.py:123-125` sanitizes query, title, and summary inside the per-source loop
- Query is the same every iteration — sanitize it once before the loop
- Fix: Move `safe_query = sanitize_content(query)` above the loop
- **Verdict: Fix — easy optimization**

**#25 — Duplicate scores tuple** (Code quality)
- `CritiqueResult.overall_pass` builds a scores tuple inline at critique.py:61-64
- If a 6th dimension is added, this tuple must be updated manually
- Fix: Add `@property def _scores(self)` that returns the tuple, use in `overall_pass`
- Also useful if mean_score or summary formatting is needed later
- **Verdict: Fix — prevents future inconsistency**

### Do Later (separate session, needs more thought)

**#31 — Critique threshold not configurable**
- Currently hardcoded `mean >= 3.0 and all(s >= 2)` in `CritiqueResult.overall_pass`
- Making it configurable means threading a threshold through CycleConfig or ResearchMode
- Not urgent — the default threshold is reasonable
- **Verdict: Defer to next feature cycle**

**#32 — Survivorship bias in pattern summary**
- `_summarize_patterns` only looks at passing critiques
- Missing the "what keeps going wrong" signal from failing runs
- Needs design: separate summary? Merge into same output?
- **Verdict: Defer — design question, not a quick fix**

**#27 — Timestamp collision in critique filenames**
- `critique-{slug}_{timestamp}.yaml` with second-precision timestamps
- Two critiques in the same second would collide (unlikely but possible in tests)
- Fix would add UUID suffix, but adds a dependency or import
- **Verdict: Defer — extremely unlikely in practice**

### Skip (not worth the churn)

**#24 — f-string in logger calls**
- Would touch ~40 logger calls across 10 files for negligible performance gain
- Python's logging lazy evaluation only matters when the log level is disabled
- This agent logs at WARNING level in production — most of these are warnings that DO get evaluated
- The f-string syntax is more readable than `%s` formatting
- **Verdict: Skip — high churn, negligible benefit, debatable best practice**

**#33 — Test quality issues**
- Duplicate fixtures, inconsistent asyncio marks, unused imports
- Real but low-impact — tests pass and test the right things
- **Verdict: Skip — address opportunistically when touching those files**

**#34 — Minor code tidiness (grab bag)**
- `Counter[str]` annotation, directory validation, unsanitized param names
- Too scattered for a focused session
- **Verdict: Skip — address opportunistically**

### Process Items (not code changes)

**#19 — Missing plan document:** Already acknowledged. Going forward, every feature follows the full brainstorm -> plan -> work -> review loop. No action needed.

**#20 — Commit size:** Already acknowledged. Discipline, not code. No action needed.

**#22 — Critique saved before report:** Acceptable for a CLI tool. If this becomes a library, revisit. No action needed.

---

## Summary

| Category | Findings | Action |
|----------|----------|--------|
| Do Now | #25, #26, #28, #29, #30 | 1 work session (~60 lines) |
| Do Later | #27, #31, #32 | Future cycle |
| Skip | #24, #33, #34 | Not worth the churn |
| Process | #19, #20, #22 | Already noted |

The "Do Now" items are a single focused session: 5 mechanical fixes, all under 15 lines each, no design decisions needed.

---

## Three Questions

1. **Hardest decision in this session?** Whether to include #24 (f-string loggers) in "Do Now." It was flagged by 3 review agents and is a real Python convention. But touching 40+ lines across 10 files for negligible runtime benefit in a CLI tool felt like churn for churn's sake. The readability argument actually favors f-strings.

2. **What did you reject, and why?** Batching #31 (configurable threshold) with the quick fixes. It's tempting because it's "just adding a parameter," but threading configuration through frozen dataclasses means touching modes.py, CycleConfig, and the CLI — that's a design session, not a cleanup.

3. **Least confident about going into the next phase?** Whether #26 (double sanitization) is truly redundant or if the downstream calls serve as defense-in-depth. Need to trace the data flow carefully in the plan phase to confirm removing them doesn't open a gap.
