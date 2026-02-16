# Review Action Plan — Cycle 17

**Date:** 2026-02-13
**Source:** Parallel review session (Kieran Python, Performance Oracle, Architecture Strategist)
**Status:** Complete (2026-02-15)

---

## Session 1: Exception Handling Cleanup (Low effort, high impact)

**Goal:** Replace all bare `except Exception` with specific exceptions per CLAUDE.md convention.

**Files:** `search.py`, `cascade.py`, `relevance.py`, `synthesize.py`, `fetch.py`, `agent.py`

- [x] `search.py:59` — catch Tavily-specific errors instead of `Exception`
- [x] `cascade.py:154` — catch Tavily-specific errors
- [x] `relevance.py:159, 414` — catch `(APIError, RateLimitError, APIConnectionError, APITimeoutError)`
- [x] `synthesize.py:188, 291, 500` — add `except (SynthesisError, KeyboardInterrupt): raise` before catch-all
- [x] `fetch.py:164` — catch `ValueError` specifically (what `urlparse` raises)
- [x] `agent.py:623` — catch specific API errors for pass 2 summarization

---

## Session 2: Typed Returns (Low effort, high impact)

**Goal:** Replace the 3 remaining `-> dict` returns with dataclasses for full pipeline consistency.

**Files:** `decompose.py`, `relevance.py` + their tests

- [x] Create `DecompositionResult` dataclass in `decompose.py` (fields: `sub_queries`, `is_complex`, `reasoning`)
- [x] Create `SourceScore` dataclass in `relevance.py` (fields: `url`, `title`, `score`, `explanation`)
- [x] Create `RelevanceEvaluation` dataclass in `relevance.py` (fields: `decision`, `decision_rationale`, `surviving_sources`, `dropped_sources`, `total_scored`, `total_survived`, `refined_query`)
- [x] Update all consumers in `agent.py` to use attribute access instead of dict keys
- [x] Update tests

---

## Session 3: Quick Performance Wins (Low effort, medium impact)

**Goal:** Fix the easy performance issues that don't require architectural changes.

**Files:** `synthesize.py`, `agent.py`, `search.py`, `cascade.py`, `extract.py`

- [x] `synthesize.py` (3 locations) — replace `full_response += text` with list + `"".join()`
- [x] `agent.py:434, 580` — wrap `refine_query()` in `asyncio.to_thread()`
- [x] `agent.py:612` — remove redundant `if new_contents` check (skipped: check is valid, not redundant)
- [x] `extract.py:48, 54` — extract magic number `100` to `MIN_EXTRACTED_TEXT_LENGTH` constant
- [x] `search.py`, `cascade.py` — reuse TavilyClient via singleton or pass-through instead of re-instantiating

---

## Session 4: Batch Delay Optimization (Low effort, high impact)

**Goal:** Replace fixed batch delays with adaptive backoff. Saves 6-9 seconds per deep run.

**Files:** `relevance.py`, `summarize.py`

- [x] `relevance.py` — reactive backoff only (sleep after 429 via `asyncio.Event`)
- [x] `summarize.py` — reactive backoff only (sleep after 429 via `asyncio.Event`)
- [x] No unconditional inter-batch delays exist — already correct

---

## Session 5: Agent.py Deduplication (Medium effort, medium impact)

**Goal:** Extract shared fetch/extract/cascade/summarize sequence to reduce orchestrator complexity.

**Files:** `agent.py`

- [x] Extract `_fetch_extract_summarize()` private method (agent.py:271)
- [x] Called by both `_research_with_refinement` and `_research_deep`
- [x] URL deduplication included in the shared method (agent.py:329-336)
- [x] All three modes (quick/standard/deep) work correctly

---

## Session 6: Architecture Consistency (Low effort, low impact)

**Goal:** Clean up scattered config and dead code.

**Files:** `errors.py`, `cascade.py`, `modes.py`, `decompose.py`, `search.py`, `relevance.py`, `skeptic.py`, `main.py`, `CLAUDE.md`

- [x] `FetchError`/`ExtractionError` — don't exist, already clean
- [x] `EXTRACT_DOMAINS` — stable API domains, hardcoded frozenset is appropriate
- [x] Model unification — `ResearchMode.model` exists, threaded through all calls; defaults kept as standalone fallbacks
- [x] `REPORTS_DIR` — defined at main.py:19, above all references
- [x] `main() -> None` — already annotated at main.py:133
- [x] CLAUDE.md architecture diagram includes `context.py` and `skeptic.py`

---

## Session 7: Deeper Performance (Medium effort, high impact)

**Goal:** Parallelism improvements for deep mode. Saves ~7-17 seconds.

**Files:** `skeptic.py`, `extract.py`, `fetch.py`

- [x] Parallelize skeptic evidence + timing agents via `asyncio.gather` (skeptic.py:348)
- [x] Parallelize `extract_all` with `ThreadPoolExecutor` (extract.py:126)
- [x] Async DNS resolution in `fetch.py` using `loop.getaddrinfo()` via `_SSRFSafeBackend`

---

## Session 8: Content Deduplication + Domain Bug (Low effort, low impact)

**Files:** `agent.py`, `cascade.py`

- [x] URL-based deduplication in `_fetch_extract_summarize` (agent.py:329-336)
- [x] Domain matching fixed at cascade.py:211 — `host == d or host.endswith("." + d)`

---

## Notes

- Sessions are scoped to ~50-100 lines of changes each
- Run `python3 -m pytest tests/ -v` after every session (527 tests, all must pass)
- All 8 sessions complete
