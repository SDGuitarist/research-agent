# Handoff: Complete Review Action Plan Sessions

## Context

The code review produced a `review-action-plan.md` with 8 sessions. Sessions 2 and 3 are
done. Sessions 1, 4, 5, 6, 7, and 8 remain. Some items within sessions have already been
addressed by other work (noted below).

All P1/P2/P3 todos (001-038) are complete. This handoff covers only the review action plan
sessions.

**Current test count: 527 tests, all passing.**

---

## Instructions

Do one session at a time. After each session:
1. Run `python3 -m pytest tests/ -v` (527 tests, all must pass)
2. Commit with message format: `fix: review session N — short description`
3. Push to remote
4. Stop and say DONE. Do NOT proceed to the next session.

Start each new conversation with:
> Read docs/plans/review-sessions-handoff.md. Implement Session [N]. Do only this session —
> commit, push, and stop.

---

## Session 1: Exception Handling Cleanup

**Goal:** Replace the 3 remaining bare `except Exception` with specific exceptions.

**Status:** Partially done. `search.py`, `cascade.py`, `relevance.py`, `fetch.py`, `agent.py`
are clean. Only `synthesize.py` remains.

**Files:** `research_agent/synthesize.py`

**What to do:**
- `synthesize.py:233` — bare `except Exception as e` after the `(SynthesisError, KeyboardInterrupt)` re-raise. Replace with `except (APIConnectionError, httpx.ReadError, ValueError) as e` or similar based on what `client.messages.create()` can actually raise beyond the already-caught API errors.
- `synthesize.py:336` — same pattern, check context
- `synthesize.py:551` — same pattern, check context

**Approach:** Read each function to see what calls could raise unexpected exceptions. The
pattern is already established: catch specific API errors first, re-raise SynthesisError and
KeyboardInterrupt, then the catch-all handles truly unexpected failures. Replace the catch-all
with the narrowest set that covers realistic failure modes.

**Commit:** `fix: review session 1 — replace bare except Exception in synthesize.py`

---

## Session 4: Batch Delay Optimization

**Goal:** Replace fixed inter-batch sleeps with reactive backoff (only sleep after a 429).

**Status:** Not started. The current code already uses `RATE_LIMIT_BACKOFF` reactively (sleep
only after 429 in both files). The original review plan's reference to `BATCH_DELAY` is stale
— that constant doesn't exist. **Verify the current behavior is already correct and mark done,
or fix if there's still a fixed delay.**

**Files:** `research_agent/relevance.py`, `research_agent/summarize.py`

**What to check:**
- `relevance.py:23` — `RATE_LIMIT_BACKOFF = 2.0`, used at line 290 only after rate limit
- `summarize.py:29` — `RATE_LIMIT_BACKOFF = 2.0`, used at line 244 only after rate limit
- Confirm: is there any unconditional `await asyncio.sleep()` between batches? If not, this
  session is already done — just verify and commit a no-op or doc update.

**Commit:** `fix: review session 4 — verify batch delays are already reactive`

---

## Session 5: Agent.py Deduplication

**Goal:** Extract the shared fetch→extract→cascade→summarize sequence into a private method.

**Status:** Not started.

**Files:** `research_agent/agent.py`, `tests/test_agent.py`

**What to do:**
- Read `_research_with_refinement` (line 470+) and `_research_deep` (line 529+)
- Identify the duplicated fetch/extract/cascade/summarize sequence
- Extract into `_fetch_and_summarize(self, urls, query, ...) -> list[Summary]`
- Both methods call the new helper instead of duplicating the pipeline
- Target: ~80 lines removed from agent.py
- Run full test suite — agent.py has 39 tests

**Commit:** `refactor: review session 5 — extract _fetch_and_summarize in agent.py`

---

## Session 6: Architecture Consistency

**Goal:** Clean up scattered config and dead code.

**Status:** Partially done. `ContextLoadError`/`ContextAuthError` already removed (todo 033).
`FetchError`/`ExtractionError` don't exist (already clean). Model string is already on
`ResearchMode.model` and threaded through `agent.py`. Some items remain.

**Files:** `research_agent/modes.py`, `main.py`, `CLAUDE.md`

**What to check and do:**
- [x] `FetchError`/`ExtractionError` — already don't exist, skip
- [x] Model unification — `ResearchMode.model` exists, `agent.py` threads `self.mode.model`
  to all calls. However, **13 functions still have `model: str = "claude-sonnet-4-20250514"`
  as a default parameter**. These defaults are redundant since `agent.py` always passes
  `model=self.mode.model`. Decide: keep the defaults as fallbacks, or remove them to enforce
  passing model explicitly. Recommend keeping — they make functions callable standalone.
- [ ] `EXTRACT_DOMAINS` — review plan says move from hardcoded frozenset to config. Check if
  this is worth doing or if the current hardcoded set is fine. If fine, skip.
- [ ] `main.py` — check if `REPORTS_DIR` is above functions that reference it (it should be)
- [ ] `main.py:main()` — add `-> None` return type if missing
- [ ] `CLAUDE.md` — verify architecture diagram includes `context.py` and `skeptic.py` (it
  should after todo 020 updated it)

**Commit:** `fix: review session 6 — architecture consistency cleanup`

---

## Session 7: Deeper Performance

**Goal:** Parallelism improvements for deep mode.

**Status:** Partially done.

**What's already done:**
- [x] DNS resolution is async (via `_SSRFSafeBackend` using `loop.getaddrinfo`)
- [x] `extract_all` already uses `ThreadPoolExecutor` (extract.py:130)
- [x] Skeptic evidence + timing already parallelized via `asyncio.gather` (skeptic.py:348)

**What to check:**
- All 3 items from the original plan are implemented. **Verify and mark done.**

**Commit:** `chore: review session 7 — verify performance improvements already in place`

---

## Session 8: Content Deduplication + Domain Bug

**Goal:** Add URL deduplication before summarization; fix domain matching.

**Status:** Domain bug already fixed (cascade.py:211 uses `host == d or host.endswith("." + d)`). URL dedup not done.

**Files:** `research_agent/agent.py`

**What to do:**
- [ ] Domain bug — already fixed at cascade.py:211, verify and skip
- [ ] URL dedup — in `_research_with_refinement` and `_research_deep` (or the new
  `_fetch_and_summarize` if Session 5 ran first), add deduplication of `ExtractedContent`
  by URL before passing to `summarize_all`. Something like:
  ```python
  seen_urls: set[str] = set()
  unique = []
  for content in extracted:
      if content.url not in seen_urls:
          seen_urls.add(content.url)
          unique.append(content)
  extracted = unique
  ```
- Run full test suite

**Commit:** `fix: review session 8 — add URL deduplication before summarization`

---

## Recommended Order

1. **Session 4** (verify batch delays — likely a no-op)
2. **Session 7** (verify performance — likely a no-op)
3. **Session 1** (exception cleanup — 3 targeted changes)
4. **Session 6** (architecture — small cleanup)
5. **Session 5** (agent dedup — medium refactor)
6. **Session 8** (URL dedup — small feature)

Sessions 4 and 7 are likely just verification. Sessions 1 and 6 are small. Session 5 is
the biggest refactor. Session 8 depends on Session 5 (if the dedup goes inside
`_fetch_and_summarize`).

---

## After All Sessions

Update `docs/plans/review-action-plan.md` — mark all items checked and add a completion
date at the top. Then commit: `chore: mark review action plan complete`
