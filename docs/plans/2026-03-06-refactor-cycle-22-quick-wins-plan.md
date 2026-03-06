---
title: "refactor: Cycle 22 quick wins — housekeeping batch"
type: refactor
status: active
date: 2026-03-06
feed_forward:
  risk: "Double-Haiku path (iterate planning + relevance scoring) not tested end-to-end"
  verify_first: false
---

# refactor: Cycle 22 Quick Wins — Housekeeping Batch

## Overview

Five small, independent housekeeping items deferred from Cycles 20-21. Each follows
established patterns and requires minimal design. Grouped into one cycle because
none justifies a full brainstorm→plan→work→review→compound loop individually.

**Dropped:** `cost_estimate` strings — already complete (all modes populated).

## Items

### 1. Validate `refine_query()` output (`search.py`)

**Problem:** `refine_query()` returns the LLM's refined query string without any
validation. It has `max_tokens=50` but no word count, overlap, or content checks.
Every other query generation path (`decompose_query`, `generate_refined_queries`,
`generate_followup_questions`) uses `validate_query_list()`.

**Fix:** After extracting the refined string (line 233), validate with:
```python
validated = validate_query_list(
    [refined],
    min_words=MIN_REFINED_WORDS,    # 3
    max_words=MAX_REFINED_WORDS,    # 10 (prompt says 3-8, allow margin)
    max_results=1,
    reference_queries=[original_query],
    max_reference_overlap=0.8,       # lenient — refinement should relate
    label="Refined query",
)
if not validated:
    logger.info("Refined query rejected by validation: %s", refined)
    return original_query
return validated[0]
```

**Constants:** Add `MIN_REFINED_WORDS = 3` and `MAX_REFINED_WORDS = 10` at module
level in `search.py`. Import `validate_query_list` from `.query_validation`.

**Overlap threshold:** 0.8 (lenient), not 0.6 like `iterate.py`. Refinement is
intentionally close to the original — it's filling gaps, not diverging.

**Files:** `research_agent/search.py`
**Tests:** `tests/test_search.py` — add 3 tests:
- Refined query passes validation → returned
- Refined query too short → falls back to original
- Refined query too long → falls back to original

---

### 2. Standalone `generate_followups` MCP tool (`mcp_server.py`)

**Problem:** `generate_followup_questions()` is only callable internally via
`_run_iteration()`. MCP clients can't ask "what should I research next?" without
running a full research cycle.

**Fix:** Add a new MCP tool following the `critique_report` pattern:

```python
@mcp.tool
def generate_followups(query: str, report_filename: str, num_questions: int = 3) -> str:
    """Generate follow-up research questions for a completed report.

    Suggests what to research next based on gaps in the report.
    Requires ANTHROPIC_API_KEY.

    Args:
        query: The original research query.
        report_filename: Report to analyze. Use list_saved_reports to find files.
        num_questions: Number of follow-up questions (1-5, default 3).
    """
```

**Implementation:**
1. Validate `report_filename` with `_validate_report_filename()`
2. Clamp `num_questions` to 1-5
3. Read the report file
4. Call `generate_followup_questions(client, query, report, num_questions, model=planning_model)`
5. Format `QueryGenerationResult.items` as numbered list
6. Return rationale + questions

**Model routing:** Use `AUTO_DETECT_MODEL` (Haiku) — follow-up generation is a
planning task, matches Cycle 21 routing decisions.

**MCP instructions update:** Add `generate_followups` to the `instructions` field
per the agent-native parity checklist.

**Files:** `research_agent/mcp_server.py`
**Tests:** `tests/test_mcp_server.py` — add 2 tests:
- Valid report → returns numbered questions
- Invalid filename → raises ToolError

---

### 3. `iteration_sections` field on `ResearchResult` (`results.py`)

**Problem:** Iteration mini-reports are concatenated into the main `report` string
but not exposed as structured data. MCP clients and programmatic consumers can't
distinguish main report content from iteration additions.

**Fix:** Add a tuple field to `ResearchResult`:

```python
iteration_sections: tuple[str, ...] = field(default=())
```

**Population:** In `agent.py`'s `_run_iteration()`, collect the mini-report
strings before concatenation. Pass them to the `ResearchResult` constructor.
The current code builds sections as a list of strings in the loop — capture that
list as a tuple.

**Backward compatible:** Default `()` means existing callers see no change.
The `report` field still contains the full text (main + iteration sections).

**Files:** `research_agent/results.py`, `research_agent/agent.py`
**Tests:** `tests/test_agent.py` — add 2 tests:
- Iteration completes → `iteration_sections` is non-empty tuple
- Iteration skipped → `iteration_sections` is empty tuple

---

### 4. Per-query source count observability (`results.py`, `agent.py`)

**Problem:** `sources_used` is a single int. No visibility into which sub-queries
produced sources vs. which returned nothing. Useful for debugging "why did this
query only find 3 sources?" questions.

**Fix:** Add a dict field to `ResearchResult`:

```python
source_counts: dict[str, int] = field(default_factory=dict)
```

**Population:** In `_search_sub_queries()`, the per-query counts are already
logged (line 540: `logger.info("→ \"%s\": %d results (%d new)")`). Return them
alongside the results. Then in the calling methods (`_research_deep`,
`_research_with_refinement`), accumulate into the dict.

**Approach — minimal change:** Rather than refactoring `_search_sub_queries`
return type, build the dict in the calling method by iterating the `tried` list
and counting sources per query. The data is already available; it just needs
collection into a dict.

**Format:** `{"original query": 5, "sub-query 1": 3, "refined query": 4}`

**Files:** `research_agent/results.py`, `research_agent/agent.py`
**Tests:** `tests/test_agent.py` — add 1 test:
- Standard mode research → `source_counts` dict has entries

---

### 5. Double-Haiku path e2e test (`tests/test_agent.py`)

**Problem:** Both `planning_model` (decompose, refine) and `relevance_model`
(evaluate_sources) default to Haiku. The compound path through iteration
(planning → search → relevance scoring) hasn't been tested end-to-end.

**Fix:** One integration test that verifies model routing through the full path:

```python
@pytest.mark.asyncio
async def test_double_haiku_planning_and_relevance_routing(self):
    """Both planning and relevance calls route to Haiku (AUTO_DETECT_MODEL)."""
    mode = ResearchMode.standard()
    agent = ResearchAgent(api_key="test-key", mode=mode)
    # ... mock search, fetch, summarize, etc.
    result = await agent.research_async("test query")

    # Verify decompose received planning_model
    mock_decompose.assert_called_once()
    assert mock_decompose.call_args[1]["model"] == AUTO_DETECT_MODEL

    # Verify evaluate_sources received mode with relevance_model
    mock_evaluate.assert_called_once()
    call_mode = mock_evaluate.call_args[1]["mode"]
    assert call_mode.relevance_model == AUTO_DETECT_MODEL
```

**Pattern:** Follow existing relevance gate tests (lines 596-638 in test_agent.py)
which mock `evaluate_sources` and assert on the result. Add model routing assertions.

**Files:** `tests/test_agent.py`

---

## Session Plan

All 5 items are independent — order by dependency (validation first, then MCP tool
that uses the validated function, then structured fields, then tests).

### Session 1: Items 1-3 (validation, MCP tool, iteration_sections)

1. Add `validate_query_list` to `refine_query()` in `search.py` + tests
2. Add `generate_followups` MCP tool in `mcp_server.py` + tests
3. Add `iteration_sections` field to `ResearchResult` + populate in `agent.py` + tests
4. Commit each item separately (~50 lines each)

### Session 2: Items 4-5 (observability, e2e test)

1. Add `source_counts` field to `ResearchResult` + populate in `agent.py` + test
2. Add double-Haiku e2e integration test
3. Run full test suite: `python3 -m pytest tests/ -v`
4. Commit each item separately

**Estimated total:** ~200-250 lines across 5 commits.

## Acceptance Criteria

- [x] `refine_query()` validates output with `validate_query_list()`, falls back to original on rejection
- [x] `generate_followups` MCP tool exposed and documented in instructions
- [x] `ResearchResult.iteration_sections` populated as tuple of mini-report strings
- [x] `ResearchResult.source_counts` populated as dict mapping query → source count
- [x] Integration test verifies both `planning_model` and `relevance_model` routing
- [x] All 907 tests pass

## Feed-Forward

- **Hardest decision:** The overlap threshold for `refine_query` validation (0.8 vs 0.6). Refinement should be related to the original — too strict rejects valid refinements, too lenient passes garbage.
- **Rejected alternatives:** Refactoring `_search_sub_queries` return type to include per-query counts. Adds complexity to a static method signature used in 4 places. Building the dict in the caller is simpler.
- **Least confident:** Whether `generate_followups` MCP tool needs its own `query` parameter or should extract it from the report metadata. Starting with explicit `query` param — simpler, no parsing needed.
