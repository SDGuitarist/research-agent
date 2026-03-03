---
status: done
priority: p2
issue_id: "115"
tags: [code-review, testing, coverage]
dependencies: []
unblocks: []
sub_priority: 3
---

# 115: Add integration test for planning_model kwarg routing

## Problem Statement

The 3 new test assertions in `test_modes.py` confirm that the `planning_model` field exists and has the correct default on each factory. But no test in `test_agent.py` asserts that the 7 planning function calls actually receive `model=AUTO_DETECT_MODEL` rather than `model=DEFAULT_MODEL`. If someone accidentally reverts a call site from `planning_model` back to `model`, no test catches it.

**Why it matters:** The entire value of this feature depends on 7 kwarg substitutions being correct. Without regression tests, a refactor could silently undo the routing.

## Findings

- **Source:** Python reviewer (O1)
- **Evidence:** Existing agent tests inspect `call_args` for snippets and query strings but none assert on the `model` kwarg
- **Pattern:** Other kwarg routing (like `skip_critique`, `max_sources`) is tested at the integration level in test_agent.py

## Proposed Solutions

### Option A: Parametrized test for all 7 sites (Recommended)
Add a single parametrized test that mocks each of the 7 planning functions and asserts the `model` kwarg equals `AUTO_DETECT_MODEL`:

```python
@pytest.mark.parametrize("func_path,expected_kwarg", [
    ("research_agent.agent.decompose_query", "model"),
    ("research_agent.agent.refine_query", "model"),
    # ... etc for all 7
])
async def test_planning_calls_use_planning_model(self, func_path, expected_kwarg):
    # mock the function, run a minimal agent flow, check call_args
    call_kwargs = mock_func.call_args[1]
    assert call_kwargs[expected_kwarg] == AUTO_DETECT_MODEL
```

- **Pros:** Catches any regression on any of the 7 sites; single test covers all
- **Cons:** Requires mocking 7 different functions; test setup may be complex
- **Effort:** Medium (30-45 min)
- **Risk:** Low

### Option B: Spot-check 2-3 critical sites only
Test only `decompose_query` and `identify_coverage_gaps` (highest-risk planning calls).

- **Pros:** Simpler, covers the most important sites
- **Cons:** Leaves 5 sites uncovered
- **Effort:** Small (20 min)
- **Risk:** Low

## Recommended Action

_To be filled during triage_

## Technical Details

**Affected files:**
- `tests/test_agent.py` — new test class or method

**Key mock targets:**
- `research_agent.agent.decompose_query`
- `research_agent.agent.refine_query` (called in 2 places)
- `research_agent.agent.identify_coverage_gaps`
- `research_agent.agent.generate_refined_queries`
- `research_agent.agent.generate_followup_questions`
- `research_agent.agent.evaluate_report`

## Acceptance Criteria

- [ ] At least the 2 highest-risk sites (decompose, coverage gaps) have model kwarg assertions
- [ ] Tests fail if `planning_model` is reverted to `model` at any tested site
- [ ] All tests pass on current code

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-03-03 | Created from Cycle 21 review | Factory tests cover field existence but not routing |

## Resources

- Commit: 435dd2e
- Python reviewer finding O1
