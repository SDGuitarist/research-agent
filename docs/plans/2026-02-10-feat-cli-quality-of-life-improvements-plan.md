---
title: "feat: CLI Quality-of-Life Improvements"
type: feat
date: 2026-02-10
---

# CLI Quality-of-Life Improvements

## Overview

Add 5 small CLI features to improve the day-to-day experience of using the research agent. All changes are in `main.py` with no modifications to the core pipeline modules, following the project's additive pattern.

## Features

1. **`--list`** — Show saved reports in a clean table
2. **Progress timing** — Add elapsed time to existing step indicators
3. **`--open`** — Auto-open saved report after generation
4. **Filename format swap** — Query-first instead of timestamp-first
5. **`--cost`** — Show estimated costs for all modes and exit

## Key Design Decisions

### Flag precedence order
When multiple flags are combined, this priority applies:
```
--list  >  --cost  >  research (normal query)
```
- `python main.py --list --cost "query"` → lists reports, ignores the rest
- `python main.py --cost --deep "query"` → shows costs, ignores query
- `python main.py` (no args, no flags) → prints help and exits

### Query becomes optional
The `query` positional argument changes from required to `nargs="?"`. Validation ensures a query is provided when actually running research (not `--list` or `--cost`).

### Microseconds kept in filenames
New format: `graphql_vs_rest_2026-02-03_183703056652.md`. Microseconds prevent collisions and cost nothing.

---

## Feature 1: `--list` flag

**What it does:** Scans `reports/` for `.md` files and prints a clean table sorted newest-first.

**File:** `main.py`

**Changes:**
- Add `--list` flag: `parser.add_argument("--list", action="store_true", help="List saved reports")`
- Make `query` optional: change to `nargs="?", default=None`
- Add `list_reports()` function that:
  1. Checks if `reports/` exists → "No reports directory found." if missing
  2. Globs `*.md` files → "No saved reports." if empty
  3. For each file, extracts date and query name from filename (handles both old timestamp-first and new query-first formats)
  4. Falls back to file modification time for non-standard filenames (e.g., `codebase_review.md`)
  5. Sorts by date descending (newest first)
  6. Prints count header + table

**Example output:**
```
Saved reports (65):
  2026-02-09  liv_entertainment_san_diego_wedding_entertainment
  2026-02-08  mike_hogan_productions_san_diego_wedding
  2026-02-03  graphql_vs_rest_api_design
  ...
  -- 8 reports with non-standard names --
  codebase_review.md
  cycle10_comparison_bonnie_foster.md
```

**Validation:** If `--list` is not set and `query` is None and `--cost` is not set → `parser.print_help()` + `sys.exit(2)`

**Edge cases:**
- Non-`.md` files (`.DS_Store`) → ignored
- Mixed old/new filename formats → both parsed with separate regex patterns

### Acceptance Criteria
- [x] `python main.py --list` prints report table and exits
- [x] Works with empty `reports/` directory
- [x] Works when `reports/` doesn't exist
- [x] Handles both old (timestamp-first) and new (query-first) filename formats
- [x] `python main.py` with no args prints help

---

## Feature 2: Progress Timing

**What it does:** Adds cumulative elapsed time to the existing `[N/M]` step headers in `agent.py`.

**File:** `research_agent/agent.py`

**Changes:**
- Add `self._start_time: float` to `__slots__` and initialize with `time.monotonic()` at the start of `_research_async()`
- Create a small helper method `_step(self, step, total, message)` that prints:
  ```
  [3/7] Extracting content... (12.4s)
  ```
- Replace the existing `print(f"\n[{step}/{step_count}] ...")` calls (step headers only, ~10 calls) with `self._step(step, total, message)`
- Leave sub-step detail lines (like "Pass 1 found 8 results") as plain `print()` — no timing on those

**Why cumulative time:** Simpler to implement (one `time.monotonic()` call at start), and tells the user "how long have I been waiting" which is what matters most.

**Test compatibility:** Tests already `patch("builtins.print")`. The `_step()` method uses `print()` internally, so existing patches still work. No test changes needed.

### Acceptance Criteria
- [x] Step headers show cumulative elapsed time in seconds
- [x] Sub-step detail lines remain unchanged
- [x] All 313+ existing tests still pass
- [x] `--verbose` mode still works

---

## Feature 3: `--open` flag

**What it does:** After saving a report, opens it with the system default application.

**File:** `main.py`

**Changes:**
- Add `import subprocess` at top
- Add `--open` flag: `parser.add_argument("--open", action="store_true", help="Open saved report after generation")`
- After `output_path.write_text(report)` and the "Report saved to:" message, add:
  ```python
  if args.open and output_path:
      subprocess.run(["open", str(output_path)])
  ```
- If `args.open` and no `output_path` (quick mode without `-o`): print warning to stderr and continue
  ```python
  if args.open and not output_path:
      print("Warning: --open ignored — no file saved. Use -o to specify output path.",
            file=sys.stderr)
  ```
- Silently ignore `--open` when combined with `--list` or `--cost` (they exit before reaching the open logic)

**Platform:** Uses macOS `open` command. The project is macOS-only (Python 3.14, darwin platform).

### Acceptance Criteria
- [x] `python main.py --standard "query" --open` saves and opens the report
- [x] `python main.py --quick "query" --open` prints warning, runs normally
- [x] `python main.py --standard "query" --open -o custom.md` opens `custom.md`
- [x] Research errors don't trigger a broken `open` call

---

## Feature 4: Filename Format Swap

**What it does:** Changes auto-saved report filenames from timestamp-first to query-first.

**File:** `main.py` (line 70)

**Changes:**
- In `get_auto_save_path()`, change:
  ```python
  # Before
  filename = f"{timestamp}_{safe_query}.md"
  # After
  filename = f"{safe_query}_{timestamp}.md"
  ```
- Update the README example at line 73:
  ```
  # -> reports/graphql_vs_rest_2026-02-03_183703056652.md
  ```
- Update the epilog example in `main.py` if applicable

**Existing reports:** The `reports/` directory is gitignored. Old files keep their old names. The `--list` feature (Feature 1) handles both formats.

### Acceptance Criteria
- [x] New reports saved as `{query}_{timestamp}.md`
- [x] Microseconds included in timestamp
- [x] README examples updated
- [x] `--list` handles both old and new filename formats

---

## Feature 5: `--cost` flag

**What it does:** Prints estimated costs for all three modes in a table and exits.

**File:** `main.py` + `research_agent/modes.py`

**Changes in `modes.py`:**
- Add `cost_estimate: str` field to the `ResearchMode` frozen dataclass
- Set values: `"~$0.12"` for quick, `"~$0.20"` for standard, `"~$0.50"` for deep
- This is the single source of truth — eliminates duplication between epilog and `--cost`

**Changes in `main.py`:**
- Add `--cost` flag: `parser.add_argument("--cost", action="store_true", help="Show estimated costs and exit")`
- Add `show_costs()` function that prints:
  ```
  Estimated costs per query:
    quick:    ~$0.12  (4 sources, ~300 words)
    standard: ~$0.20  (10 sources, ~2000 words)  [default]
    deep:     ~$0.50  (12 sources, ~3500 words)
  ```
- Reads source count and word target from each `ResearchMode` instance
- Placed after argparse but before `ResearchAgent()` creation — no API keys needed
- Update the epilog to read cost values from `ResearchMode` instead of hardcoding

### Acceptance Criteria
- [x] `python main.py --cost` shows all three modes with costs
- [x] Works without API keys configured
- [x] Cost values come from `ResearchMode` (single source of truth)
- [x] Epilog help text also reads from `ResearchMode`

---

## Implementation Order

Build in this order to minimize conflicts between features:

1. **Feature 5: `--cost`** — Pure addition, no interaction with other features. Also adds `cost_estimate` to `ResearchMode` which the epilog can use.
2. **Feature 4: Filename swap** — One-line change in `get_auto_save_path()`. Do this before `--list` so we know the final format.
3. **Feature 1: `--list`** — Depends on knowing both filename formats (old + new from Feature 4). Also makes `query` optional, which `--cost` already needs.
4. **Feature 2: Progress timing** — Touches `agent.py`, independent of other features.
5. **Feature 3: `--open`** — Depends on the final save path logic being stable.

Each feature = one commit (~50-100 lines each).

## Testing Strategy

- **Features 1, 3, 4, 5** modify `main.py` which has no test file. Add `tests/test_main.py` with unit tests for the new functions (`list_reports()`, `show_costs()`, `sanitize_filename()`, `get_auto_save_path()`).
- **Feature 2** modifies `agent.py` which has extensive tests. The `_step()` helper uses `print()` so existing `patch("builtins.print")` mocks still work.
- Run `python3 -m pytest tests/ -v` after each feature to verify all 313+ tests pass.

## References

- `main.py` — CLI entry point (lines 74-195)
- `research_agent/modes.py` — Mode configurations (lines 1-161)
- `research_agent/agent.py` — Orchestrator with print statements (lines 1-579)
- `CLAUDE.md` — Project conventions (additive pattern, frozen dataclasses)
- `LESSONS_LEARNED.md` — Past development cycle insights
