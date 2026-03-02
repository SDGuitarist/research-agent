# Review Context — Research Agent

## Risk Chain

**Brainstorm risk:** "Whether the refinement step is meaningfully different from what decompose + coverage retry already do."

**Plan mitigation:** Gap-first refinement prompt (FAIR-RAG MISSING:/QUERY: format) forces diagnosis before query generation — structurally different from decompose (facet splitting) and coverage retry (more sources on same queries).

**Work risk (from Feed-Forward):** "Whether `synthesize_mini_report()` will produce useful sections even with the heading exclusion list — without the main report as negative context, the LLM may still regurgitate."

**Review resolution:** 14 findings (2 P1, 7 P2, 5 P3) from 8 agents. All resolved. Top issues: unsanitized headings in prompts (P2), sequential mini-report synthesis (P2, 10-25s perf hit), no overall iteration timeout (P2).

**Fix risk (from Three Questions):** "The interaction between `asyncio.wait_for` and the parallel mini-report synthesis. If the timeout fires mid-synthesis, `asyncio.gather` tasks inside `_run_iteration` get cancelled."

**Compound resolution:** Documented cancellation semantics — `wait_for` cancels outer coroutine → cancels `gather` → cancels each task. Pre-iteration `result` is never mutated, so no partial state escapes.

## Files to Scrutinize

| File | What changed | Risk area |
|------|-------------|-----------|
| `research_agent/agent.py` | Parallel synthesis (gather+semaphore), wait_for timeout, heading sanitization, status enum | Cancellation under timeout; sanitization at all insertion points |
| `research_agent/iterate.py` | Gap-first refinement, three-perspective follow-ups, heading extraction sanitization, named constants | Double-sanitization idempotency if layers chain |
| `research_agent/cli.py` | `--no-iteration` flag, iteration status display | CLI/MCP parity |
| `research_agent/synthesize.py` | `synthesize_mini_report()` non-streaming | System prompt copied from `synthesize_report()` — must stay in sync |

## Plan Reference

`docs/plans/2026-03-01-feat-query-iteration-plan.md`
