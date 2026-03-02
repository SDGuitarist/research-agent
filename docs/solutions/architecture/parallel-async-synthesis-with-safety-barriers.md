---
title: "Parallel Async Synthesis with Safety Barriers"
date: 2026-03-02
category: architecture
tags:
  - asyncio
  - parallel-synthesis
  - semaphore
  - timeout
  - prompt-injection-defense
  - defense-in-depth
  - status-enum
  - pipeline-integration
  - query-iteration
severity: medium
component: "research_agent/agent.py, research_agent/iterate.py, research_agent/cli.py"
cycle: 20
related_cycles: [13, 17, 18, 19, 21]
symptoms: >
  After synthesis the agent had no mechanism to reframe the original query based
  on gaps in the draft, and no way to surface predictive follow-up questions.
  Reports ended at first-pass synthesis with no self-correction loop.
root_cause: >
  The pipeline lacked a post-synthesis iteration stage. Decompose splits facets
  before research; coverage retry adds more sources on the same queries.
  Neither diagnosed what the draft was missing and reframed the question.
fix_type: feature
dependencies: []
unblocks: []
---

# Parallel Async Synthesis with Safety Barriers

Cycle 20 added a query iteration stage to the research pipeline. The review
phase found 14 issues (2 P1, 7 P2, 5 P3). The fix phase resolved all of them,
producing four reusable patterns documented below.

### Prior Phase Risk

> **From fix phase Three Questions:** "Least confident about the interaction
> between `asyncio.wait_for` (todo 104) and the parallel mini-report synthesis
> (todo 103). If the timeout fires mid-synthesis, `asyncio.gather` tasks inside
> `_run_iteration` get cancelled. The main report is returned unchanged, but I
> haven't tested the cancellation path under real conditions."

This compound phase documents both patterns and their interaction so future
reviewers know the cancellation semantics. The timeout wraps the entire
`_run_iteration` call, which contains the gather — so cancellation propagates
cleanly through gather to each semaphore-guarded task.

## Risk Resolution

| Flagged Risk | What Actually Happened | Lesson |
|---|---|---|
| `wait_for` cancelling mid-gather | `asyncio.wait_for` cancels the outer coroutine, which cancels the `gather`, which cancels each task. No partial state escapes because the pre-iteration `result` is never mutated in-place. | Wrapping the whole phase (not individual tasks) in `wait_for` is the correct granularity — it gives clean cancellation semantics for free. |

---

## Pattern 1: Parallel Synthesis with Semaphore + Gather

### Problem

Mini-report synthesis for each iteration query was sequential — each
`synthesize_mini_report()` call finished before the next started. With 3-4
queries, latency stacked multiplicatively.

### Solution

A closure captures a shared `asyncio.Semaphore`, and all synthesis tasks launch
simultaneously via `asyncio.gather`. The semaphore caps concurrency without the
caller managing scheduling.

`research_agent/agent.py:319-340`:

```python
MAX_CONCURRENT_SUB_QUERIES = 2  # module-level constant

sem = asyncio.Semaphore(MAX_CONCURRENT_SUB_QUERIES)

async def _synthesize_one(q: str, title: str) -> str | None:
    async with sem:
        try:
            return await asyncio.to_thread(
                synthesize_mini_report,
                self.client, q, new_summaries,
                section_title=title,
                model=self.mode.model,
                max_tokens=iteration_max_tokens,
                report_headings=report_headings,
            )
        except SynthesisError as e:
            logger.warning("Mini-report failed for '%s': %s", q, e)
            return None

results = await asyncio.gather(
    *[_synthesize_one(q, t) for q, t in query_titles]
)
appended_sections = [r for r in results if r is not None]
```

### Why It Works

`asyncio.gather` starts all coroutines immediately but they compete for the
semaphore — only `MAX_CONCURRENT_SUB_QUERIES` run at a time. Because
`synthesize_mini_report` is synchronous (uses the sync Anthropic client), it is
offloaded with `asyncio.to_thread()` to avoid blocking the event loop.

Per-task exception isolation (`except SynthesisError`) means one failure returns
`None` without cancelling sibling tasks. The `None` filter after gather produces
a clean list of successful results in input order.

### Reuse Guidance

Apply this pattern for N independent tasks that each call a blocking or
rate-limited API:

1. `sem = asyncio.Semaphore(N)` — N is the concurrency cap
2. Inner `async def _do_one(item)` with `async with sem` + `asyncio.to_thread()`
3. `asyncio.gather(*[_do_one(x) for x in items])`
4. Filter `None` results

### Anti-pattern

```python
# WRONG: unbounded gather, no error isolation
results = await asyncio.gather(*[
    asyncio.to_thread(synthesize_mini_report, self.client, q, summaries)
    for q in all_queries
])
# All tasks hit the API simultaneously -> rate limit.
# One exception escapes -> whole batch lost.
```

---

## Pattern 2: asyncio.wait_for Timeout Wrapping

### Problem

The iteration phase involves multiple LLM calls and web fetches. If any hang,
the entire research run stalls indefinitely with no recovery.

### Solution

Wrap the entire iteration call in `asyncio.wait_for()` with a module-level
timeout constant. On expiration, catch `TimeoutError` and continue with the
pre-iteration report.

`research_agent/agent.py:42-43, 876-889`:

```python
ITERATION_TIMEOUT = 180.0  # seconds

try:
    result, iteration_sources_added = await asyncio.wait_for(
        self._run_iteration(query, result, evaluation),
        timeout=ITERATION_TIMEOUT,
    )
    if iteration_sources_added > 0:
        self._iteration_status = "completed"
    else:
        self._iteration_status = "no_new_sources"
except asyncio.TimeoutError:
    logger.warning("Iteration timed out after %.0fs", ITERATION_TIMEOUT)
    self._iteration_status = "error"
except IterationError as e:
    logger.warning("Iteration failed: %s", e)
    self._iteration_status = "error"
```

### Why It Works

`asyncio.wait_for` cancels the wrapped coroutine on timeout and raises
`asyncio.TimeoutError`. The caller sets status, logs, and continues — the user
gets a report without the iteration enrichment rather than a hung process.

Two-level timeout design: per-call (`ANTHROPIC_TIMEOUT = 30.0` on
`messages.create`) prevents one hung API call; phase-level (`ITERATION_TIMEOUT`)
prevents stacked slow-but-within-limit calls from running for minutes.

### Reuse Guidance

Apply whenever a pipeline has an optional enrichment phase:

- Wrap the phase with `asyncio.wait_for(coro, timeout=NAMED_CONSTANT)`
- Catch `asyncio.TimeoutError` separately from domain errors
- Set a distinct status value so callers/tests can distinguish timeout from logic failure
- Ensure `result` holds the pre-enrichment value before the `wait_for` call

### Anti-pattern

```python
# WRONG: no timeout — hangs indefinitely
result, count = await self._run_iteration(query, result, evaluation)

# WRONG: timeout only on individual calls, not the phase
# A series of slow-but-within-30s calls can still total minutes
```

---

## Pattern 3: Defense-in-Depth Heading Sanitization

### Problem

Report headings extracted from web content could contain prompt injection
payloads. If inserted into an LLM prompt unsanitized, an attacker could
manipulate model behavior via a crafted heading like
`"## Ignore previous instructions"`.

### Solution

Sanitization at two independent layers, plus XML structural boundaries.

**Layer 1 — iterate.py** (heading extraction for follow-up prompt):

`research_agent/iterate.py:186-191`:

```python
headings = [
    sanitize_content(line.lstrip("#").strip())
    for line in report.splitlines()
    if line.startswith("## ")
]
headings_str = ", ".join(headings) if headings else "none"
```

**Layer 2 — agent.py** (section titles for mini-report prompts):

`research_agent/agent.py:243-248, 314-317`:

```python
report_headings = [
    sanitize_content(line.lstrip("#").strip())
    for line in report.splitlines()
    if line.startswith("## ")
]

for q in all_queries:
    safe_q = sanitize_content(q)
    title = f"Deeper Dive: {safe_q}" if q in refined_set else f"Follow-Up: {safe_q}"
```

Both layers import from the shared `sanitize.py` — never duplicate the logic.

### Why It Works

Two independent sanitization points mean even if one is bypassed by a future
refactor, the other still intercepts payloads. XML boundary delimiters
(`<original_query>`, `<draft_report>`) provide a third structural layer. System
prompt warnings about injection are the fourth.

The key insight: **headings derived from LLM output that embedded web content
are still external content**. The sanitization obligation follows the data
lineage, not the function call chain.

### Reuse Guidance

Wherever external content ends up in an LLM prompt:

1. Sanitize at the point where external content enters your data structures
2. Sanitize again where those structures are interpolated into prompt strings
3. Wrap in named XML tags for structural isolation
4. Add system prompt warning about injection
5. Import `sanitize_content()` from `sanitize.py` — never reimplement inline

### Anti-pattern

```python
# WRONG: raw insertion into prompt
content = f"<draft_report>{draft}</draft_report>"
# A heading like "</draft_report><system>New instructions</system>" breaks the XML.

# WRONG: sanitize once, assume downstream is safe
sanitized_draft = sanitize_content(draft)
headings = [line.lstrip("#").strip() for line in sanitized_draft.splitlines() ...]
# lstrip("#").strip() does not strip escaping, but future changes might.
# Always re-sanitize at the insertion point.
```

---

## Pattern 4: Status Enum Disambiguation

### Problem

The iteration phase could "succeed" (no error) but produce nothing — e.g., all
search results duplicated existing URLs. Without a distinct status, callers
could not distinguish "ran and added content" from "ran but found nothing new".
Both looked like `"completed"`.

### Solution

Four-way status string with each value mapping to exactly one real-world
outcome.

`research_agent/agent.py:92, 109-112, 880-889`:

```python
# __init__
self._iteration_status = "skipped"  # initial: never attempted

@property
def iteration_status(self) -> str:
    """Iteration outcome: 'completed', 'skipped', 'no_new_sources', 'error'."""
    return self._iteration_status

# Assignment
if iteration_sources_added > 0:
    self._iteration_status = "completed"       # ran AND found new content
else:
    self._iteration_status = "no_new_sources"  # ran but zero new sources
# ...
except asyncio.TimeoutError:
    self._iteration_status = "error"           # did not finish
```

| Status | Meaning |
|---|---|
| `"skipped"` | Never attempted (mode config or `--no-iteration` flag) |
| `"completed"` | Ran and added at least one new source |
| `"no_new_sources"` | Ran fully but all results already seen |
| `"error"` | Timed out or raised `IterationError` |

### Why It Works

Tests and callers assert the exact outcome without parsing logs or inspecting
counts. `"no_new_sources"` is a legitimate expected outcome (deduplication
working correctly) — collapsing it into `"completed"` hides the signal;
collapsing it into `"error"` is factually wrong.

### Reuse Guidance

When a pipeline stage has more than two meaningful outcomes:

- Use a string with all valid values documented in the property docstring
- Set the initial value to the "never ran" state, not a failure state
- Keep status assignment co-located with the determining logic
- Add `"no_new_sources"`-style intermediate states when "success" conflates
  distinct caller needs

### Anti-pattern

```python
# WRONG: boolean success/failure loses the "ran but empty" signal
self._iteration_succeeded = True  # But did it find anything new?

# WRONG: overloading "completed" with a side-channel count check
if self._iteration_status == "completed" and self._last_source_count == 0:
    # Hidden state — callers must remember the extra condition
```

---

## Prevention Checklist (All Patterns)

| Pattern | Core Risk | One-Line Prevention Rule |
|---|---|---|
| Parallel synthesis | Resource exhaustion + silent partial failure | Cap with a named semaphore; catch specific exceptions per task, return None |
| wait_for timeout | Hung pipeline, no recovery | Two-level timeout (per-call + per-phase); always catch TimeoutError explicitly |
| Heading sanitization | Prompt injection via derived fields | Sanitize at every insertion point; treat LLM output that embedded web content as external |
| Status enum | Overloaded state values hide signals | One value per distinguishable outcome; document all values in property docstring |

---

## Related Documentation

- `docs/solutions/security/non-idempotent-sanitization-double-encode.md` — Established "sanitize once at the data boundary" rule that Pattern 3 extends to derived fields
- `docs/solutions/architecture/iterative-review-second-pass-patterns.md` — Pattern 1 ("Complete the Sanitization Boundary") predicted Finding 102
- `docs/solutions/architecture/self-enhancing-agent-review-patterns.md` — Pattern 4 (Async/Sync Boundary Awareness) is the precedent for `asyncio.to_thread()` usage
- `docs/solutions/architecture/gap-aware-research-loop.md` — Four-state result type pattern informs the status enum design
- `docs/solutions/performance-issues/adaptive-batch-backoff.md` — "React to actual failures" philosophy extends to `wait_for` timeout design
- `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md` — Defensive input normalization precedent for status disambiguation

## Patterns Reinforced from Lessons Learned

- **Three-layer prompt injection defense** (Top 10 #1) — extended: sanitization obligation covers strings extracted from prior LLM output, not only direct external content
- **Additive pipeline pattern** (Top 10 #2) — confirmed: iterate.py never imports from agent.py, main report is never mutated
- **Async/sync boundary discipline** (Cycle 21) — confirmed: synchronous iterate.py functions wrapped in `asyncio.to_thread()` at the agent.py call site
- **Named constants over magic numbers** (Cycle 6) — reinforced: `MAX_CONCURRENT_SUB_QUERIES`, `ITERATION_TIMEOUT`, validation thresholds all extracted

## Three Questions

1. **Hardest pattern to extract from the fixes?** The interaction between Pattern 1 (parallel gather) and Pattern 2 (wait_for timeout). They are independent fixes (todos 103 and 104) but their runtime behavior is coupled — timeout cancels gather which cancels semaphore-guarded tasks. Documenting them as separate patterns while explaining the cancellation semantics required careful framing.

2. **What did you consider documenting but left out, and why?** The CLI flag pattern (`--no-iteration` from todo 105) and the private naming convention (`_skip_critique` from todo 111). Both are real fixes but not reusable architectural patterns — they are one-time cleanup that follows existing conventions. Including them would dilute the four core patterns.

3. **What might future sessions miss that this solution doesn't cover?** The double-sanitization idempotency risk. `sanitize_content` is not idempotent — calling it twice on `&` produces `&amp;amp;`. The current code avoids this because each layer sanitizes different extracted substrings (headings vs. query text), not the same string twice. But a future refactor that pipes one layer's output into another could trigger double-encoding. The existing solution doc `non-idempotent-sanitization-double-encode.md` covers this, but there is no automated test that detects double-sanitization across the two new layers.
