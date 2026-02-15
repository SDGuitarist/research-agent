# Review Action Plan — Cycle 17

**Date:** 2026-02-13
**Source:** Parallel review session (Kieran Python, Performance Oracle, Architecture Strategist)
**Status:** Pending implementation

---

## Session 1: Exception Handling Cleanup (Low effort, high impact)

**Goal:** Replace all bare `except Exception` with specific exceptions per CLAUDE.md convention.

**Files:** `search.py`, `cascade.py`, `relevance.py`, `synthesize.py`, `fetch.py`, `agent.py`

- [ ] `search.py:59` — catch Tavily-specific errors instead of `Exception`
- [ ] `cascade.py:154` — catch Tavily-specific errors
- [ ] `relevance.py:159, 414` — catch `(APIError, RateLimitError, APIConnectionError, APITimeoutError)`
- [ ] `synthesize.py:188, 291, 500` — add `except (SynthesisError, KeyboardInterrupt): raise` before catch-all
- [ ] `fetch.py:164` — catch `ValueError` specifically (what `urlparse` raises)
- [ ] `agent.py:623` — catch specific API errors for pass 2 summarization

---

## Session 2: Typed Returns (Low effort, high impact)

**Goal:** Replace the 3 remaining `-> dict` returns with dataclasses for full pipeline consistency.

**Files:** `decompose.py`, `relevance.py` + their tests

- [ ] Create `DecompositionResult` dataclass in `decompose.py` (fields: `sub_queries`, `is_complex`, `reasoning`)
- [ ] Create `SourceScore` dataclass in `relevance.py` (fields: `url`, `title`, `score`, `explanation`)
- [ ] Create `RelevanceEvaluation` dataclass in `relevance.py` (fields: `decision`, `decision_rationale`, `surviving_sources`, `dropped_sources`, `total_scored`, `total_survived`, `refined_query`)
- [ ] Update all consumers in `agent.py` to use attribute access instead of dict keys
- [ ] Update tests

---

## Session 3: Quick Performance Wins (Low effort, medium impact)

**Goal:** Fix the easy performance issues that don't require architectural changes.

**Files:** `synthesize.py`, `agent.py`, `search.py`, `cascade.py`, `extract.py`

- [x] `synthesize.py` (3 locations) — replace `full_response += text` with list + `"".join()`
- [x] `agent.py:434, 580` — wrap `refine_query()` in `asyncio.to_thread()`
- [ ] `agent.py:612` — remove redundant `if new_contents` check (skipped: check is valid, not redundant)
- [x] `extract.py:48, 54` — extract magic number `100` to `MIN_EXTRACTED_TEXT_LENGTH` constant
- [x] `search.py`, `cascade.py` — reuse TavilyClient via singleton or pass-through instead of re-instantiating

---

## Session 4: Batch Delay Optimization (Low effort, high impact)

**Goal:** Replace fixed batch delays with adaptive backoff. Saves 6-9 seconds per deep run.

**Files:** `relevance.py`, `summarize.py`

- [ ] `relevance.py` — remove or reduce fixed `BATCH_DELAY = 3.0` between scoring batches
- [ ] `summarize.py` — remove or reduce fixed `BATCH_DELAY = 1.5` between summarize batches
- [ ] Implement simple adaptive backoff: only delay after receiving a 429
- [ ] Test with `--deep` to verify no rate limit issues

---

## Session 5: Agent.py Deduplication (Medium effort, medium impact)

**Goal:** Extract shared fetch/extract/cascade/summarize sequence to reduce orchestrator complexity.

**Files:** `agent.py`

- [ ] Extract `_fetch_and_summarize()` private method from repeated logic in `_research_with_refinement` and `_research_deep`
- [ ] Reduce `agent.py` by ~80 lines
- [ ] Verify all three modes (quick/standard/deep) still work correctly
- [ ] Run full test suite

---

## Session 6: Architecture Consistency (Low effort, low impact)

**Goal:** Clean up scattered config and dead code.

**Files:** `errors.py`, `cascade.py`, `modes.py`, `decompose.py`, `search.py`, `relevance.py`, `skeptic.py`, `main.py`, `CLAUDE.md`

- [ ] Remove `FetchError` and `ExtractionError` from `errors.py` (never raised)
- [ ] Move `EXTRACT_DOMAINS` from hardcoded frozenset to config (field on `ResearchMode` or loaded from context)
- [ ] Unify model strings: add `model` field to `ResearchMode`, thread through to `decompose_query`, `refine_query`, `score_source`, skeptic functions
- [ ] Move `REPORTS_DIR` above functions that reference it in `main.py`
- [ ] Add `-> None` return type to `main()`
- [ ] Update CLAUDE.md architecture diagram to include `context.py` and `skeptic.py`

---

## Session 7: Deeper Performance (Medium effort, high impact)

**Goal:** Parallelism improvements for deep mode. Saves ~7-17 seconds.

**Files:** `skeptic.py`, `extract.py`, `fetch.py`

- [ ] Parallelize skeptic evidence + timing agents (they don't depend on each other), only frame depends on both
- [ ] Parallelize `extract_all` with `ThreadPoolExecutor` (~1-2 sec savings)
- [ ] Make DNS resolution async in `fetch.py` using `loop.getaddrinfo()` instead of blocking `socket.getaddrinfo()`

---

## Session 8: Content Deduplication + Domain Bug (Low effort, low impact)

**Files:** `agent.py`, `cascade.py`

- [ ] Add URL-based deduplication before summarization in `agent.py` (prevents wasted API calls on duplicate content)
- [ ] Fix domain matching in `cascade.py:159` — `host.endswith("yelp.com")` matches `evilyelp.com`. Use `host == d or host.endswith("." + d)`

---

## Notes

- Sessions are scoped to ~50-100 lines of changes each
- Run `python3 -m pytest tests/ -v` after every session (385 tests, all must pass)
- Sessions 1-4 are highest priority (quick wins, strong consensus across reviewers)
- Sessions 5-8 can be done in any order based on what matters most
- Total estimated deep-mode speedup from all performance fixes: 13-29 seconds (15-30%)
