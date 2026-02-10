---
title: "CLI Quality-of-Life Improvements: --cost, --list, --open, filename swap, progress timing"
date: 2026-02-10
category: feature-implementation
tags:
  - CLI
  - argparse
  - user-experience
  - frozen-dataclass
  - filename-format
  - progress-tracking
module: main.py, research_agent/modes.py, research_agent/agent.py
symptoms: |
  No way to see past reports, check costs, or open reports without manual filesystem navigation.
  No elapsed time during pipeline execution. Filenames sorted by timestamp, not by topic.
severity: low
summary: |
  Added 5 CLI features in Cycle 14: --cost, --list, --open, filename swap, progress timing.
  Key patterns: single source of truth for costs in frozen dataclass, dual regex for backward-compatible
  filename parsing, _step() helper for test-compatible progress output, nargs="?" with validation guard.
---

# CLI Quality-of-Life Improvements (Cycle 14)

## What Was Built

5 additive CLI features, each in its own commit (~50-100 lines):

1. **`--cost`** — Shows estimated costs for all modes in a table, exits without API keys
2. **Filename swap** — Reports saved as `{query}_{timestamp}.md` instead of `{timestamp}_{query}.md`
3. **`--list`** — Scans `reports/` and prints a clean table sorted newest-first
4. **Progress timing** — Step headers show cumulative elapsed time: `[3/7] Extracting... (12.4s)`
5. **`--open`** — Auto-opens saved report with macOS `open` command

## Key Patterns

### 1. Single Source of Truth for Costs

**Problem:** Cost estimates were hardcoded in the argparse epilog string AND would need to be duplicated in `--cost` output. Values drift when mode parameters change.

**Solution:** Added `cost_estimate: str` field to the `ResearchMode` frozen dataclass. Both the epilog and `--cost` read from it.

```python
# modes.py — cost lives with the mode config
@dataclass(frozen=True)
class ResearchMode:
    cost_estimate: str = ""  # e.g., "~$0.20"

# main.py — epilog reads from mode objects
_standard = ResearchMode.standard()
epilog = f"--standard  ...({_standard.cost_estimate}) [default]"

# main.py — --cost also reads from mode objects
def show_costs():
    for m in [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]:
        print(f"  {m.name:<10} {m.cost_estimate}  ({m.max_sources} sources)")
```

**Lesson:** Configuration values belong in dataclasses, not string literals.

### 2. Dual Regex for Backward-Compatible Filename Parsing

**Problem:** Changing filename format orphans existing reports in `--list` output.

**Solution:** Two regex patterns, one per format. Try old first, then new, then fall back to "non-standard."

```python
_OLD_FORMAT = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{6,}_(.+)\.md$")  # date first
_NEW_FORMAT = re.compile(r"^(.+)_(\d{4}-\d{2}-\d{2})_\d{6,}\.md$")  # query first
```

**Gotcha:** Groups are in different order between patterns. `group(1)` is date in old format but query in new format.

### 3. `_step()` Helper for Test-Compatible Progress

**Problem:** Adding elapsed time to 13 scattered `print(f"\n[{step}/{total}]...")` calls is error-prone and hard to maintain.

**Solution:** Extract a `_step()` method that wraps `print()`. Tests that `patch("builtins.print")` still work because `_step()` calls `print()` internally.

```python
def _step(self, step: int | str, total: int | str, message: str) -> None:
    elapsed = time.monotonic() - self._start_time
    print(f"\n[{step}/{total}] {message} ({elapsed:.1f}s)")
```

**Lesson:** When adding metadata to existing output, wrap — don't rewrite. Preserves test compatibility.

### 4. `nargs="?"` with Validation Guard

**Problem:** `--list` and `--cost` don't need a query, but the `query` arg was required. Making it optional with `nargs="?"` means `python main.py` with no args silently passes parsing with `query=None`.

**Solution:** Check flags in priority order, then validate query is present for research:

```python
if args.list:       # Priority 1
    list_reports(); sys.exit(0)
if args.cost:       # Priority 2
    show_costs(); sys.exit(0)
if args.query is None:  # Priority 3: guard
    parser.print_help(); sys.exit(2)
```

**Lesson:** `nargs="?"` always needs an explicit validation guard. The order of checks defines flag precedence.

## Prevention Checklist for Future CLI Features

- [ ] New config values go in `ResearchMode` dataclass, not hardcoded strings
- [ ] New flags that don't need a query go BEFORE the `args.query is None` guard
- [ ] New progress prints use `self._step()`, not raw `print(f"\n[...")`
- [ ] If changing file formats, add regex pattern for old format in `list_reports()`
- [ ] Run full test suite after each change (`python3 -m pytest tests/ -v`)
- [ ] Keep `__slots__` updated when adding instance attributes to `ResearchAgent`

## Files Changed

| File | Change |
|------|--------|
| `research_agent/modes.py` | Added `cost_estimate` field + values to all 3 modes |
| `main.py` | Added `show_costs()`, `list_reports()`, `--open`/`--cost`/`--list` flags, `REPORTS_DIR`, dual regex, query validation |
| `research_agent/agent.py` | Added `_step()` helper, `_start_time` to `__slots__`, replaced 13 step headers |
| `tests/test_main.py` | 28 new tests covering all new functions |
| `README.md` | Updated filename example |

## Related

- `docs/plans/2026-02-10-feat-cli-quality-of-life-improvements-plan.md` — Full plan with SpecFlow analysis
- `LESSONS_LEARNED.md` lines 191-230 — CLI argument philosophy (env vars vs flags)
- `LESSONS_LEARNED.md` line 1809 — Previously noted gap: no `test_main.py` (now fixed)
