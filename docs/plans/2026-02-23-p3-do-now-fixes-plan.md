# Plan: P3 "Do Now" Fixes (#25, #26, #28, #29, #30)

**Date:** 2026-02-23
**Source:** `docs/brainstorms/2026-02-23-p3-triage-brainstorm.md`
**Estimated:** ~60 lines changed, 1 work session

---

### Prior Phase Risk

> "Whether #26 (double sanitization) is truly redundant or if the downstream calls serve as defense-in-depth. Need to trace the data flow carefully in the plan phase to confirm removing them doesn't open a gap."

**Resolution:** Traced the full data flow. The `_summarize_patterns()` function in `context.py:225` already sanitizes its return value via `sanitize_content(summary)`. This summary is what becomes `critique_guidance` in agent.py. Downstream consumers (`decompose.py:142`, `relevance.py:137`) re-sanitize the same string — this is redundant, not defense-in-depth, because the string never passes through an unsanitized boundary between context.py and those consumers. Removing the downstream calls is safe.

Additionally, `context.py:216` sanitizes individual weakness strings, then `context.py:225` sanitizes the concatenated summary that includes those already-sanitized strings. The inner sanitize (line 216) is the meaningful one; the outer sanitize (line 225) is the redundant layer. However, removing the outer one is riskier (future changes to `_summarize_patterns` might add unsanitized content). **Decision:** Keep the outer sanitize at 225, remove only the downstream re-sanitizations in decompose.py and relevance.py. This preserves one sanitization boundary at the producer while eliminating the truly redundant consumer-side calls.

---

## Fix #28 — bool/int validation bug (context.py:153)

**Problem:** `isinstance(True, int)` returns `True` in Python because `bool` is a subclass of `int`. A malformed critique YAML with `source_diversity: true` would pass validation as score 1 (`True == 1`).

**File:** `research_agent/context.py:153`

**Current code:**
```python
if not isinstance(val, int) or not (1 <= val <= 5):
    return False
```

**Fix:**
```python
if isinstance(val, bool) or not isinstance(val, int) or not (1 <= val <= 5):
    return False
```

**Test:** Add a test in `tests/test_context.py` that passes a critique dict with `source_diversity: True` (bool) and asserts `_validate_critique_yaml` returns `False`.

**Lines changed:** ~1 (code) + ~8 (test)

---

## Fix #29 — Quick mode loads critique history (agent.py:202-205)

**Problem:** Quick mode never uses critique guidance (it skips decomposition's adaptive prompts and doesn't pass critique to scoring). But `load_critique_history` still runs — reading and parsing YAML files from disk on every quick run.

**File:** `research_agent/agent.py:202-205`

**Current code:**
```python
critique_context: str | None = None
critique_ctx = await asyncio.to_thread(load_critique_history, META_DIR)
if critique_ctx:
    critique_context = critique_ctx.content
    logger.info("Loaded critique history for adaptive prompts")
```

**Fix:** Wrap the load in a mode guard:
```python
critique_context: str | None = None
if self.mode.name != "quick":
    critique_ctx = await asyncio.to_thread(load_critique_history, META_DIR)
    if critique_ctx:
        critique_context = critique_ctx.content
        logger.info("Loaded critique history for adaptive prompts")
```

**Test:** Existing tests mock `load_critique_history`. No new test needed — the guard is trivially correct. Verify existing tests still pass.

**Lines changed:** ~2

---

## Fix #26 — Double sanitization (decompose.py:142, relevance.py:137)

**Problem:** `critique_guidance` is already sanitized by `_summarize_patterns()` in context.py before it reaches agent.py. Two downstream consumers re-sanitize it:
1. `decompose.py:142` — `safe_critique = sanitize_content(critique_guidance)`
2. `relevance.py:137` — `safe_adjustments = sanitize_content(critique_guidance)`

Both are redundant since the string was sanitized at the producer (context.py:225).

**File 1:** `research_agent/decompose.py:142`

**Current:**
```python
if critique_guidance:
    safe_critique = sanitize_content(critique_guidance)
    critique_block = f"""
<critique_guidance>
{safe_critique}
</critique_guidance>
"""
```

**Fix:** Remove the sanitize call, use `critique_guidance` directly:
```python
if critique_guidance:
    critique_block = f"""
<critique_guidance>
{critique_guidance}
</critique_guidance>
"""
```

**File 2:** `research_agent/relevance.py:137`

**Current:**
```python
if critique_guidance:
    safe_adjustments = sanitize_content(critique_guidance)
    safe_adjustments = truncate_to_budget(safe_adjustments, 500)
    adjustments_block = ...
```

**Fix:** Remove the sanitize call, keep the truncation:
```python
if critique_guidance:
    safe_adjustments = truncate_to_budget(critique_guidance, 500)
    adjustments_block = ...
```

**Test:** No new tests needed — behavior is identical (sanitize_content is idempotent). Verify existing tests pass.

**Lines changed:** ~4

---

## Fix #30 — Redundant sanitize in per-source scoring (relevance.py:123)

**Problem:** `score_source()` is called once per source via `asyncio.gather` (line 302). Inside it, `sanitize_content(query)` and `sanitize_content(critique_guidance)` run on every call even though `query` and `critique_guidance` are identical across all sources in the batch.

**File:** `research_agent/relevance.py`

**Approach:** Pre-sanitize `query` once at the call site (in `score_and_filter_sources`, around line 297) and pass the sanitized version to `score_source`. Inside `score_source`, use `query` directly for the prompt (rename to make intent clear with a comment). Keep `sanitize_content` for `title` and `summary` since those differ per-source.

**Caller fix (line ~297):**
```python
safe_query = sanitize_content(query)
# ... in the loop:
tasks = [score_source(safe_query, summary, ...) for summary in batch]
```

**score_source fix (line 123):**
```python
# query is pre-sanitized by caller
safe_title = sanitize_content(summary.title or "Untitled")
safe_summary = sanitize_content(summary.summary)
```
Remove `safe_query = sanitize_content(query)` from line 123. Use `query` directly in the prompt (it's already sanitized).

Note: This combines with Fix #26's removal of the critique_guidance re-sanitize at line 137, so both redundancies are addressed together.

**Test:** No new tests needed — `score_source` is only called from `score_and_filter_sources`. Verify existing tests pass.

**Lines changed:** ~4

---

## Fix #25 — Duplicate scores tuple in CritiqueResult (critique.py:61-64, 70-73)

**Problem:** The `(source_diversity, claim_support, coverage, geographic_balance, actionability)` tuple is built identically in both `overall_pass` and `mean_score` properties. If a 6th dimension is added, both must be updated manually.

**File:** `research_agent/critique.py:58-74`

**Fix:** Add a `_scores` property that returns the tuple once, used by both:
```python
@property
def _scores(self) -> tuple[int, ...]:
    return tuple(getattr(self, d) for d in DIMENSIONS)

@property
def overall_pass(self) -> bool:
    """True if mean >= 3.0 AND no dimension below 2."""
    scores = self._scores
    mean = sum(scores) / len(scores)
    return mean >= 3.0 and all(s >= 2 for s in scores)

@property
def mean_score(self) -> float:
    return sum(self._scores) / len(self._scores)
```

This uses the existing `DIMENSIONS` tuple (line 26-32), so adding a 6th dimension automatically propagates.

**Test:** No new tests — `overall_pass` and `mean_score` behavior is unchanged. Verify existing tests pass.

**Lines changed:** ~8

---

## Session Plan

All 5 fixes in a single work session. Order by dependency:

1. **#28** (bool/int bug) — standalone, no dependencies
2. **#29** (quick mode guard) — standalone, no dependencies
3. **#25** (scores tuple) — standalone, no dependencies
4. **#26 + #30** (sanitization cleanup) — do together since both touch relevance.py

**Commit strategy:** One commit per fix, message format `fix(scope): description (#N)`.

Expected commits:
1. `fix(context): reject bool values in critique YAML validation (#28)`
2. `fix(agent): skip critique history load in quick mode (#29)`
3. `refactor(critique): extract _scores property to deduplicate tuple (#25)`
4. `fix(sanitize): remove redundant sanitize calls in decompose and relevance (#26, #30)`

**Verification:** Run `python3 -m pytest tests/ -v` after all fixes. All 607+ tests must pass.

---

## Three Questions

1. **Hardest decision in this session?** Whether to keep the outer `sanitize_content(summary)` at context.py:225 or remove it along with the downstream calls. Chose to keep it — it's the producer's sanitization boundary and costs nothing. Removing it would save one call but create a subtle contract where `_summarize_patterns` returns unsanitized content if future edits add raw strings.

2. **What did you reject, and why?** Adding a `pre_sanitized: bool` parameter to `score_source()` to support both sanitized and unsanitized callers. Over-engineering — `score_source` has exactly one caller and is an internal function. Just pre-sanitize at the call site and document with a comment.

3. **Least confident about going into the next phase?** The `_scores` property using `getattr(self, d) for d in DIMENSIONS` — it works because DIMENSIONS entries match the dataclass field names exactly, but if someone renames a field without updating DIMENSIONS, it would silently return an AttributeError at runtime. The frozen dataclass makes this unlikely (you'd get a test failure immediately), but it's worth double-checking the field names match during implementation.
