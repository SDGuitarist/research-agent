# Cycle 11: Chunk Fan-Out Rate Limiting Fix

## Context

The 429 rate limit errors during summarization are caused by chunk fan-out, not batch size. `summarize_content` fires all chunks per source in parallel via `asyncio.gather`, so a batch of 5 sources x 5 chunks = 25 simultaneous API calls — far exceeding the 30K tokens/min tier. Batch size reductions from 12 to 5 in Cycle 10 treated the symptom. This plan fixes the root cause.

Research findings: `reports/cycle11_semaphore_research.md`

---

## Commit 1: Semaphore Fix (Root Cause)

### File: `research_agent/summarize.py`

**Step 1 — Add constant (after line 28)**

```python
# Maximum concurrent API calls for chunk summarization
MAX_CONCURRENT_CHUNKS = 3
```

Place after `BATCH_DELAY = 3.0` with the other batching constants. Value of 3 based on research: at 30K tokens/min tier with ~1,350 tokens/call and ~2s latency, sustainable concurrency is ~0.74. Semaphore=3 keeps 429 rate at ~15-20% (handled by existing 1-retry logic).

**Step 2 — Modify `summarize_all` (lines 237-247) to create and pass semaphore**

In `summarize_all`, create the semaphore before the batch loop and pass it to each `summarize_content` call:

```python
async def summarize_all(...) -> list[Summary]:
    all_summaries = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)  # NEW

    for batch_start in range(0, len(contents), BATCH_SIZE):
        batch = contents[batch_start:batch_start + BATCH_SIZE]
        if batch_start > 0:
            await asyncio.sleep(BATCH_DELAY)
        tasks = [
            summarize_content(client, content, model, structured=structured,
                              max_chunks=max_chunks, semaphore=semaphore)  # CHANGED
            for content in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # ... rest unchanged
```

This follows the exact pattern from `fetch.py:230` (semaphore created in `fetch_urls`, passed to `_fetch_single`) and `cascade.py:88` (semaphore created in `_fetch_via_jina`, passed to `_jina_single`).

**Step 3 — Modify `summarize_content` signature (line 171) to accept optional semaphore**

Add `semaphore: asyncio.Semaphore | None = None` as last parameter:

```python
async def summarize_content(
    client: AsyncAnthropic,
    content: ExtractedContent,
    model: str = "claude-sonnet-4-20250514",
    structured: bool = False,
    max_chunks: int = MAX_CHUNKS_PER_SOURCE,
    semaphore: asyncio.Semaphore | None = None,  # NEW
) -> list[Summary]:
```

Default `None` preserves backward compatibility — existing tests and direct callers continue working without changes.

**Step 4 — Wrap each `summarize_chunk` call with the semaphore (lines 194-205)**

Replace the bare `summarize_chunk` calls in the task list with a semaphore-guarded wrapper:

```python
    chunks = _chunk_text(content.text, max_chunks=max_chunks)

    async def _guarded_summarize(chunk: str) -> Summary | None:
        if semaphore is not None:
            async with semaphore:
                return await summarize_chunk(
                    client=client, chunk=chunk, url=content.url,
                    title=content.title, model=model, structured=structured,
                )
        return await summarize_chunk(
            client=client, chunk=chunk, url=content.url,
            title=content.title, model=model, structured=structured,
        )

    tasks = [_guarded_summarize(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

Why a local wrapper instead of modifying `summarize_chunk` directly:
- `summarize_chunk` stays unchanged — no signature change, no test impact on `TestSummarizeChunk`
- The semaphore wraps the leaf-level API call (inside `summarize_chunk`) without nesting through `summarize_content`'s gather — no deadlock risk
- When `semaphore is None` (direct callers, tests), behavior is identical to current code

**Step 5 — Update docstring for `summarize_content`**

Add `semaphore` to the Args docstring:

```
        semaphore: Optional semaphore for concurrency limiting across sources
```

### File: `tests/test_summarize.py`

**Step 6 — Add `MAX_CONCURRENT_CHUNKS` to imports (line 6-16)**

Add `MAX_CONCURRENT_CHUNKS` to the existing import block from `research_agent.summarize`.

**Step 7 — Add constant validation test (after line 408)**

Add to `test_batch_constants_are_reasonable`:

```python
    assert 1 <= MAX_CONCURRENT_CHUNKS <= 10
```

**Step 8 — Add a dedicated semaphore concurrency test**

New test in `TestSummarizeAll` class that verifies the semaphore actually limits concurrency:

```python
@pytest.mark.asyncio
async def test_summarize_all_limits_concurrent_chunks(self):
    """Verify that chunk summarization respects the concurrency semaphore."""
    max_concurrent_observed = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracked_create(**kwargs):
        nonlocal max_concurrent_observed, current_concurrent
        async with lock:
            current_concurrent += 1
            max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
        await asyncio.sleep(0.01)  # Simulate API latency
        async with lock:
            current_concurrent -= 1
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Summary")]
        return mock_response

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = tracked_create

    # Create enough content to exceed MAX_CONCURRENT_CHUNKS
    contents = [
        ExtractedContent(url=f"http://example.com/{i}", title=f"Title {i}",
                         text="Word " * 2000)  # Long enough to produce multiple chunks
        for i in range(4)
    ]

    result = await summarize_all(mock_client, contents)
    assert len(result) > 0
    assert max_concurrent_observed <= MAX_CONCURRENT_CHUNKS
```

### File: `CLAUDE.md`

**Step 9 — Update Known Limitations section (line 74)**

Change:
```
- **429 rate limit warnings** during deep mode summarization (30K tokens/min tier) — batched (12/batch, 3s delay) with 1 retry per chunk, but not eliminated at current tier.
```
To:
```
- **429 rate limit warnings** during deep mode summarization (30K tokens/min tier) — chunk concurrency capped at 3 (`MAX_CONCURRENT_CHUNKS`), batched 5 sources/batch with 3s inter-batch delay, 1 retry per chunk. Reduced but not fully eliminated at current tier.
```

### Verification — Commit 1

1. `python3 -m pytest tests/test_summarize.py -v` — all existing + new tests pass
2. `python3 -m pytest tests/ -v` — full suite (290+ tests) passes
3. Manual smoke test: `python3 main.py --standard "test query" -v` — observe no 429s in verbose output (or significantly fewer than before)
4. Manual deep mode test: `python3 main.py --deep "test query" -v` — the worst-case path; verify 429s are reduced

---

## Commit 2: Batch Size / Delay Tuning

### File: `research_agent/summarize.py`

**Step 1 — Increase BATCH_SIZE from 5 to 8 (line 27)**

```python
BATCH_SIZE = 8
```

With the semaphore capping concurrent API calls at 3, batch size controls how many sources are *dispatched* per round, not how many API calls are in flight. 8 sources x 3-5 chunks = 24-40 chunks queued, but only 3 run at a time. Safe.

**Step 2 — Reduce BATCH_DELAY from 3.0 to 1.5 (line 28)**

```python
BATCH_DELAY = 1.5
```

The semaphore is now the primary rate control. BATCH_DELAY serves as a secondary breathing window for the rolling token budget. 1.5s is conservative enough to provide recovery without the 6s+ idle overhead the 3.0s delay caused for 12-source deep mode runs.

### File: `tests/test_summarize.py`

**Step 3 — No test changes needed**

- `test_batch_constants_are_reasonable` asserts `5 <= BATCH_SIZE <= 20` — BATCH_SIZE=8 passes
- Same test asserts `BATCH_DELAY >= 1.0` — BATCH_DELAY=1.5 passes

### File: `CLAUDE.md`

**Step 4 — Update Known Limitations to reflect new values**

Update the batch description to say "8 sources/batch with 1.5s inter-batch delay".

### Verification — Commit 2

1. `python3 -m pytest tests/test_summarize.py -v` — all tests pass (constant assertions still hold)
2. `python3 -m pytest tests/ -v` — full suite passes
3. Manual smoke test: `python3 main.py --deep "test query" -v` — verify that the larger batch size + shorter delay does NOT reintroduce 429s (the semaphore should prevent it)
4. Compare wall time against commit 1 — should be faster due to reduced idle time from BATCH_DELAY

---

## Files Modified

| File | Commit 1 | Commit 2 |
|------|----------|----------|
| `research_agent/summarize.py` | Add `MAX_CONCURRENT_CHUNKS`, semaphore in `summarize_all`, guard in `summarize_content` | Change `BATCH_SIZE` 5→8, `BATCH_DELAY` 3.0→1.5 |
| `tests/test_summarize.py` | Add import, constant test, concurrency test | No changes |
| `CLAUDE.md` | Update Known Limitations | Update batch values |

## Out of Scope

- `relevance.py` — confirmed 1 call per source, no fan-out
- Shared semaphore across summarize + relevance — sequential in pipeline
- Retry-outside-semaphore refactor — future cycle
- SDK `max_retries=0` — future cycle
- Word count tuning, standard mode template — Cycle 12
