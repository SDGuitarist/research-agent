# Cycle 18 Handoff: Pip-Installable Package

## Status
Plan deepened and reviewed. 4 minor fixes needed before implementation.

## Plan file
`docs/plans/2026-02-15-feat-pip-installable-package-plan.md`

## Fixes needed (from /plan_review)

### Fix 1: httpcore version bound
**File:** plan line ~534 (pyproject.toml code block in Session 4a)
**Change:** `"httpcore>=1.0.0"` → `"httpcore>=1.0.5"`
**Why:** httpx 0.27.0 requires httpcore >=1.0.5. Using 1.0.0 could cause version conflicts.

### Fix 2: Remove readme from pyproject.toml
**File:** plan line ~528 (pyproject.toml code block in Session 4a)
**Change:** Delete `readme = "README.md"` line
**Why:** README.md may not be in the expected format for setuptools. Not needed for local install. Add back when publishing to PyPI.

### Fix 3: Version sync test Python 3.10 compat
**File:** plan Session 2b test list (around line 435)
**Change:** Add note that version sync test needs `@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires 3.11+")` since `tomllib` is stdlib 3.11+.
**Why:** `requires-python = ">=3.10"` means the test must not break on 3.10.

### Fix 4: Add event loop collision test
**File:** plan Session 2b test list (around line 430)
**Change:** Add this test to the list:
```
- `run_research()` from inside async context raises `ResearchError` with "async context" message
```
**Why:** Listed in acceptance criteria (line 142) but missing from Session 2b test plan.

## After fixes
Plan is ready for `/workflows:work` starting with Session 1.
