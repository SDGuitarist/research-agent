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

**Status:** DONE. All 3 bare `except Exception` in synthesize.py replaced with
`(APIConnectionError, httpx.ReadError, httpx.RemoteProtocolError, ValueError)`.

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

**Status:** DONE. Verified — both files use reactive backoff only (sleep after 429 via
`asyncio.Event`). No unconditional inter-batch delays exist. No code changes needed.

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

**Status:** DONE. Already implemented — `_fetch_extract_summarize` exists at agent.py:271
and is called by both `_research_with_refinement` (line 521) and `_research_deep` (lines
554, 580). URL deduplication is also included (lines 329-336). No code changes needed.

---

## Session 6: Architecture Consistency

**Goal:** Clean up scattered config and dead code.

**Status:** DONE. All items verified:
- [x] `FetchError`/`ExtractionError` — don't exist, clean
- [x] Model unification — defaults kept as standalone fallbacks
- [x] `EXTRACT_DOMAINS` — stable API domains, hardcoded frozenset is fine, skip
- [x] `REPORTS_DIR` — defined at main.py:19, above all references
- [x] `main() -> None` — already annotated at main.py:133
- [x] `CLAUDE.md` — includes `context.py` and `skeptic.py` in diagram
No code changes needed.

**Commit:** `fix: review session 6 — architecture consistency cleanup`

---

## Session 7: Deeper Performance

**Goal:** Parallelism improvements for deep mode.

**Status:** DONE. All 3 items verified in place:
- [x] DNS resolution is async (via `_SSRFSafeBackend` using `loop.getaddrinfo` in fetch.py)
- [x] `extract_all` uses `ThreadPoolExecutor` (extract.py:126)
- [x] Skeptic evidence + timing parallelized via `asyncio.gather` (skeptic.py:348)
No code changes needed.

**Commit:** `chore: review session 7 — verify performance improvements already in place`

---

## Session 8: Content Deduplication + Domain Bug

**Goal:** Add URL deduplication before summarization; fix domain matching.

**Status:** DONE. Both items already implemented:
- [x] Domain bug — fixed at cascade.py:211 with `host == d or host.endswith("." + d)`
- [x] URL dedup — in `_fetch_extract_summarize` at agent.py:329-336, deduplicates by URL
  before passing to `summarize_all`. No code changes needed.

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
