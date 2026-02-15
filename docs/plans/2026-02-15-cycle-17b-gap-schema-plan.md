# Cycle 17B: Gap Schema Layer — Implementation Plan

**Date:** 2026-02-15
**Cycle:** 17B (Gap Schema Layer)
**Scope:** Gap data model, YAML parser, schema validator, cycle detector, priority sorter
**Inputs:** `cycle-17-05-cycle-breakdown.md`, `cycle-17-03-failure-modes.md`, `cycle-17-04-edge-cases.md`, `master-recommendations-future-cycles.md`, Cycle 17A implementation
**Estimated total lines:** ~290
**Estimated commits:** 5
**New dependency:** `PyYAML>=6.0` (add to `requirements.txt`)

---

## Purpose

Build a standalone module that reads a YAML gap schema file, validates it for structural and logical correctness, detects circular dependencies, and returns a priority-sorted list of gaps ready for the research pipeline. This module has no knowledge of the research pipeline — it operates purely on YAML files and returns data structures. Pipeline integration happens in Cycle 17D.

---

## 17A Foundation Used

| 17A Component | How 17B Uses It |
|---------------|-----------------|
| `SchemaError` (`errors.py`) | Raised on YAML parse failures and validation errors. Uses the `errors: list[str]` attribute to report ALL validation problems at once |
| `CycleConfig` (`cycle_config.py`) | `default_ttl_days` used when a gap has no `ttl_days` field |
| `ContextResult` pattern (`context_result.py`) | `load_schema()` follows the same three-way result pattern: not_configured / empty / loaded (via a `SchemaResult` dataclass) |
| `safe_io` (`safe_io.py`) | Not used directly in 17B (no writes). Used in 17C when writing gap state back |

---

## Build Order

```
Session 1: Gap data model (GapStatus enum + Gap frozen dataclass)
    ↓
Session 2: YAML parser (load_schema → SchemaResult)
    ↓
Session 3: Schema validator (validate_gaps → list of error strings)
    ↓
Session 4: Cycle detector (detect_cycles → list of cycle paths)
    ↓
Session 5: Priority sorter (sort_gaps → ordered list of Gap objects)
```

Each session depends on the previous one. The parser produces `Gap` objects. The validator checks `Gap` objects. The cycle detector checks the dependency graph between `Gap` objects. The sorter orders validated `Gap` objects.

---

## Deliverable 1: Gap Data Model

**File:** `research_agent/schema.py` (new)
**Test file:** `tests/test_schema.py` (new)
**Estimated lines:** ~55 in module, ~45 in test file

### What it does

Defines the `GapStatus` enum and the `Gap` frozen dataclass — the core data types that the parser, validator, and sorter all operate on. Follows the frozen dataclass pattern established by `ResearchMode` and `CycleConfig`.

### Design

```python
from dataclasses import dataclass, field
from enum import Enum


class GapStatus(Enum):
    UNKNOWN = "unknown"       # Never researched
    VERIFIED = "verified"     # Researched and confirmed
    STALE = "stale"           # Was verified but TTL expired
    BLOCKED = "blocked"       # Waiting on another gap


@dataclass(frozen=True)
class Gap:
    """A single gap in the research schema.

    Represents one piece of intelligence that may need research.
    """
    id: str                                    # Unique identifier (e.g., "pricing")
    category: str                              # Grouping label (e.g., "competitor-a")
    status: GapStatus = GapStatus.UNKNOWN
    priority: int = 3                          # 1 (lowest) to 5 (highest)
    last_verified: str | None = None           # ISO timestamp or None
    last_checked: str | None = None            # ISO timestamp or None
    ttl_days: int | None = None                # Per-gap freshness window; None = use default
    blocks: tuple[str, ...] = ()               # Gap IDs this gap blocks
    blocked_by: tuple[str, ...] = ()           # Gap IDs that must complete first
    findings: str = ""                         # Summary of what was found
    metadata: dict[str, str] = field(default_factory=dict)
```

### Acceptance criteria

1. `GapStatus` enum has exactly four values: `UNKNOWN`, `VERIFIED`, `STALE`, `BLOCKED`
2. `Gap` is a frozen dataclass — attribute assignment raises `FrozenInstanceError`
3. `Gap` has sensible defaults: `status=UNKNOWN`, `priority=3`, empty `blocks`/`blocked_by`
4. `blocks` and `blocked_by` are tuples (not lists) to maintain immutability
5. `metadata` is a dict for future extensibility (schema evolution, per 17-02 best practice)
6. A `Gap` with only `id` and `category` is valid: `Gap(id="pricing", category="competitor-a")`

### Test requirements

| Test | Validates |
|------|-----------|
| `test_gap_status_has_four_values` | `GapStatus` has exactly `UNKNOWN`, `VERIFIED`, `STALE`, `BLOCKED` |
| `test_gap_minimal_construction` | `Gap(id="x", category="y")` succeeds with defaults |
| `test_gap_is_frozen` | Attempting `gap.status = GapStatus.STALE` raises `FrozenInstanceError` |
| `test_gap_defaults` | Default `status` is `UNKNOWN`, `priority` is 3, `blocks` is empty tuple |
| `test_gap_full_construction` | All fields populated explicitly |
| `test_gap_blocks_is_tuple` | `blocks` is a tuple, not a list |
| `test_gap_equality` | Two `Gap` objects with same fields are equal |

### Dependencies

None. First deliverable.

---

## Deliverable 2: YAML Parser

**File:** `research_agent/schema.py` (append to existing)
**Test file:** `tests/test_schema.py` (append to existing)
**Estimated lines:** ~60 in module, ~55 in test file

### What it does

Reads a YAML file from disk and converts it into a list of `Gap` objects. Follows the three-way result pattern from `ContextResult`: the return type distinguishes "file not found" (not configured), "file exists but is empty" (empty), and "file parsed successfully" (loaded). YAML parse errors raise `SchemaError`.

### Design

```python
from dataclasses import dataclass
from pathlib import Path
import yaml

from .errors import SchemaError


@dataclass(frozen=True)
class SchemaResult:
    """Result of loading a gap schema file.

    Follows the three-way pattern from ContextResult:
    - gaps is non-empty and is_loaded is True: schema loaded successfully
    - gaps is empty and is_empty is True: file exists but has no gaps
    - gaps is empty and is_not_configured is True: file does not exist
    """
    gaps: tuple[Gap, ...]
    source: str = ""

    @property
    def is_loaded(self) -> bool:
        return len(self.gaps) > 0

    @property
    def is_empty(self) -> bool:
        return len(self.gaps) == 0 and self.source != ""

    @property
    def is_not_configured(self) -> bool:
        return len(self.gaps) == 0 and self.source == ""

    def __bool__(self) -> bool:
        return self.is_loaded


def load_schema(path: Path | str) -> SchemaResult:
    """Load a gap schema from a YAML file.

    Args:
        path: Path to the YAML schema file.

    Returns:
        SchemaResult with parsed Gap objects.

    Raises:
        SchemaError: If the file exists but contains invalid YAML or
            the YAML structure doesn't match the expected schema format.
    """
```

**Expected YAML format:**

```yaml
gaps:
  - id: "pricing"
    category: "competitor-a"
    status: "unknown"
    priority: 4
    ttl_days: 14
    blocks: ["market-position"]
  - id: "team"
    category: "competitor-a"
    status: "verified"
    priority: 2
    last_verified: "2026-01-15"
    ttl_days: 90
```

### Acceptance criteria

1. `load_schema()` returns `SchemaResult` with `source=""` when the file does not exist (not configured)
2. `load_schema()` returns `SchemaResult` with `source=<path>` and empty `gaps` when the file is empty or has an empty `gaps` list
3. `load_schema()` returns `SchemaResult` with populated `gaps` tuple when the file is valid
4. Malformed YAML (bad indentation, missing colons) raises `SchemaError` with a descriptive message
5. Valid YAML but wrong structure (e.g., `gaps` is a string instead of a list) raises `SchemaError`
6. Unknown `status` values (e.g., `status: "foobar"`) raise `SchemaError`
7. `blocks` and `blocked_by` lists in YAML are converted to tuples in the `Gap` object
8. Missing optional fields use `Gap` defaults (not errors)
9. Missing required fields (`id`, `category`) raise `SchemaError`
10. `bool(SchemaResult)` is `True` only when gaps are present

### Test requirements

| Test | Validates |
|------|-----------|
| `test_parse_valid_schema` | Well-formed YAML parsed into correct `Gap` objects |
| `test_parse_missing_file` | Non-existent path returns `SchemaResult` with `is_not_configured=True` |
| `test_parse_empty_file` | Empty file returns `SchemaResult` with `is_empty=True` |
| `test_parse_empty_gaps_list` | File with `gaps: []` returns `SchemaResult` with `is_empty=True` |
| `test_parse_malformed_yaml` | Broken YAML raises `SchemaError` |
| `test_parse_wrong_structure` | `gaps: "not a list"` raises `SchemaError` |
| `test_parse_unknown_status` | `status: "foobar"` raises `SchemaError` |
| `test_parse_missing_required_id` | Gap without `id` raises `SchemaError` |
| `test_parse_missing_required_category` | Gap without `category` raises `SchemaError` |
| `test_parse_defaults_applied` | Gap with only `id` and `category` gets default `status`, `priority`, etc. |
| `test_schema_result_bool_true_when_loaded` | `bool(result)` is `True` when gaps exist |
| `test_schema_result_bool_false_when_empty` | `bool(result)` is `False` when no gaps |

### Dependencies

- Deliverable 1 (`GapStatus`, `Gap` dataclass)
- `PyYAML` library (new dependency)
- `SchemaError` from Cycle 17A `errors.py`

---

## Deliverable 3: Schema Validator

**File:** `research_agent/schema.py` (append to existing)
**Test file:** `tests/test_schema.py` (append to existing)
**Estimated lines:** ~75 in module, ~70 in test file

### What it does

Checks a list of `Gap` objects for logical consistency. Reports ALL errors found (not just the first one), matching the `SchemaError(errors=[...])` pattern from Cycle 17A. The validator catches the CRITICAL failure modes F2.1 (malformed schema) and the consistency issues from Edge Case 6.

### Design

```python
def validate_gaps(gaps: tuple[Gap, ...]) -> list[str]:
    """Validate a collection of gaps for logical consistency.

    Returns a list of error strings. Empty list means all valid.
    Does NOT raise — caller decides whether errors are fatal.

    Checks:
    1. Unique IDs — no duplicate gap IDs
    2. Status/timestamp coherence:
       - verified → last_verified must be non-None
       - unknown → last_verified must be None
    3. Reference integrity — all IDs in blocks/blocked_by exist in the schema
    4. No self-references — a gap cannot block itself
    5. Priority range — must be 1-5
    6. TTL range — if set, must be >= 1
    """
```

### Acceptance criteria

1. Returns an empty list for a valid gap set
2. Detects duplicate gap IDs
3. Detects `status: verified` with `last_verified: None` (Edge Case 6)
4. Detects `status: unknown` with non-None `last_verified` (Edge Case 6)
5. Detects references to non-existent gap IDs in `blocks`/`blocked_by`
6. Detects self-references (a gap ID in its own `blocks` or `blocked_by`)
7. Detects `priority` outside the 1-5 range
8. Detects `ttl_days` less than 1 (when set)
9. Reports ALL errors found, not just the first one
10. Does not raise exceptions — returns a list of error strings. Callers decide severity.

### Test requirements

| Test | Validates |
|------|-----------|
| `test_validate_valid_gaps` | Valid gap set returns empty error list |
| `test_validate_duplicate_ids` | Two gaps with same `id` detected |
| `test_validate_verified_needs_timestamp` | `status: verified` + `last_verified: None` → error |
| `test_validate_unknown_has_no_timestamp` | `status: unknown` + `last_verified: "2026-01-01"` → error |
| `test_validate_reference_integrity` | `blocked_by: ["nonexistent"]` → error naming the bad reference |
| `test_validate_self_reference_blocks` | Gap with own ID in `blocks` → error |
| `test_validate_self_reference_blocked_by` | Gap with own ID in `blocked_by` → error |
| `test_validate_priority_too_low` | `priority: 0` → error |
| `test_validate_priority_too_high` | `priority: 6` → error |
| `test_validate_ttl_days_invalid` | `ttl_days: 0` → error |
| `test_validate_reports_all_errors` | Schema with 3 errors reports all 3 |
| `test_validate_empty_gaps` | Empty tuple returns empty error list |

### Dependencies

- Deliverable 1 (`GapStatus`, `Gap` dataclass)

---

## Deliverable 4: Cycle Detector

**File:** `research_agent/schema.py` (append to existing)
**Test file:** `tests/test_schema.py` (append to existing)
**Estimated lines:** ~40 in module, ~45 in test file

### What it does

Uses DFS-based cycle detection on the `blocks`/`blocked_by` dependency graph. Returns the specific nodes forming each cycle (not just "cycle exists"). This addresses failure mode F2.2 — Kahn's algorithm silently drops cycled nodes without reporting them.

### Design

```python
def detect_cycles(gaps: tuple[Gap, ...]) -> list[tuple[str, ...]]:
    """Detect circular dependencies in the gap dependency graph.

    Uses DFS to find all cycles in the directed graph formed by
    blocks/blocked_by relationships.

    Args:
        gaps: Validated gap objects (call validate_gaps first).

    Returns:
        List of cycles, where each cycle is a tuple of gap IDs
        forming the cycle (e.g., ("a", "b", "a")).
        Empty list means no cycles.
    """
```

### Acceptance criteria

1. Returns an empty list for an acyclic graph
2. Detects a simple two-node cycle: A blocks B, B blocks A → `[("a", "b", "a")]`
3. Detects a deep cycle: A→B→C→A → `[("a", "b", "c", "a")]`
4. Detects multiple independent cycles in the same graph
5. Does not report false cycles on a linear chain (A→B→C→D)
6. Does not report false cycles on a diamond (A→B, A→C, B→D, C→D)
7. Uses only the `blocks` field for graph edges (builds adjacency list from `blocks`; `blocked_by` is the reverse view and is not traversed separately to avoid double-counting)
8. Returns empty list for gaps with no dependencies

### Test requirements

| Test | Validates |
|------|-----------|
| `test_no_cycles_empty` | No gaps → empty list |
| `test_no_cycles_linear` | A→B→C→D → empty list |
| `test_no_cycles_diamond` | A→B, A→C, B→D, C→D → empty list |
| `test_simple_cycle` | A→B→A detected |
| `test_deep_cycle` | A→B→C→A detected |
| `test_multiple_cycles` | Two independent cycles both detected |
| `test_no_dependencies` | Gaps with empty `blocks` → empty list |
| `test_cycle_includes_path` | Returned cycle includes all nodes in order |

### Dependencies

- Deliverable 1 (`Gap` dataclass — uses `id` and `blocks` fields)

---

## Deliverable 5: Priority Sorter

**File:** `research_agent/schema.py` (append to existing)
**Test file:** `tests/test_schema.py` (append to existing)
**Estimated lines:** ~60 in module, ~55 in test file

### What it does

Performs topological sort (Kahn's algorithm) on the dependency graph, using priority as a tiebreaker among gaps with the same dependency depth. Cycled nodes are not silently dropped — they are appended to the output sorted by priority, with a `has_cycle` flag. This addresses the silent-drop failure from F2.2.

### Design

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SortedGaps:
    """Result of priority sorting.

    ordered: Gaps in dependency-respecting, priority-weighted order.
    cycled: Gap IDs that are part of cycles (sorted by priority as fallback).
    """
    ordered: tuple[Gap, ...]
    cycled: tuple[str, ...] = ()

    @property
    def has_cycles(self) -> bool:
        return len(self.cycled) > 0


def sort_gaps(gaps: tuple[Gap, ...], cycles: list[tuple[str, ...]] | None = None) -> SortedGaps:
    """Sort gaps by dependency order with priority-based tiebreaking.

    Uses Kahn's algorithm for topological sort. Among gaps at the
    same dependency level (same in-degree), higher priority comes first.

    Args:
        gaps: Gap objects to sort.
        cycles: Pre-detected cycles from detect_cycles(). If None,
            detect_cycles() is called internally.

    Returns:
        SortedGaps with ordered gaps and any cycled node IDs.
    """
```

### Acceptance criteria

1. Gaps with dependencies appear after the gaps they depend on
2. Among gaps at the same dependency level, higher `priority` (5) comes before lower (1)
3. Cycled nodes are NOT silently dropped — they appear in `SortedGaps.cycled`
4. Cycled nodes are also included in `ordered`, appended after acyclic gaps, sorted by priority
5. `has_cycles` property returns `True` when any cycled nodes exist
6. When all gaps are `UNKNOWN` with no dependencies, sort is purely by priority (Edge Case 1)
7. When all gaps are `VERIFIED` and fresh, all gaps still appear in output (Edge Case 2 — the pipeline decides what to do, not the sorter)
8. Works with an empty gap tuple (returns empty `SortedGaps`)

### Test requirements

| Test | Validates |
|------|-----------|
| `test_sort_empty` | Empty tuple → empty `SortedGaps` |
| `test_sort_respects_dependencies` | If A blocks B, A appears before B in output |
| `test_sort_breaks_ties_by_priority` | Among independent gaps, priority 5 before priority 1 |
| `test_sort_handles_all_unknown` | All `UNKNOWN` gaps sorted by priority only (Edge Case 1) |
| `test_sort_cycled_nodes_not_dropped` | Cycled nodes appear in both `ordered` and `cycled` |
| `test_sort_cycled_nodes_after_acyclic` | Cycled nodes appended after all acyclic gaps |
| `test_sort_cycled_nodes_by_priority` | Cycled nodes sorted by priority among themselves |
| `test_sort_has_cycles_property` | `has_cycles` is `True` when cycles exist, `False` otherwise |
| `test_sort_fully_populated_schema` | All `VERIFIED` gaps still appear in output (Edge Case 2) |
| `test_sort_complex_dag` | Multi-level DAG with branches sorts correctly |

### Dependencies

- Deliverable 1 (`Gap` dataclass)
- Deliverable 4 (`detect_cycles` — called internally if cycles not provided)

---

## Summary Table

| # | Deliverable | What it does | Est. Lines (module) | Est. Lines (tests) | Depends On |
|---|-------------|--------------|--------------------|--------------------|------------|
| 1 | Gap data model | `GapStatus` enum + `Gap` frozen dataclass | ~55 | ~45 | — |
| 2 | YAML parser | `load_schema()` → `SchemaResult` | ~60 | ~55 | #1, PyYAML, `SchemaError` |
| 3 | Schema validator | `validate_gaps()` → error list | ~75 | ~70 | #1 |
| 4 | Cycle detector | `detect_cycles()` → cycle paths | ~40 | ~45 | #1 |
| 5 | Priority sorter | `sort_gaps()` → `SortedGaps` | ~60 | ~55 | #1, #4 |
| | **Totals** | **1 new module + 1 new test file** | **~290** | **~270** | |

---

## What This Cycle Does NOT Touch

- **No changes to `agent.py`** — pipeline integration is Cycle 17D
- **No changes to `context.py`** — context refactoring is Cycle 17D
- **No changes to existing modules** — schema.py is entirely new
- **No state writes** — writing updated gaps back to disk is Cycle 17C
- **No staleness detection** — that's Cycle 17C
- **No existing test files modified** — all 385+ existing tests must pass unchanged

---

## What This Cycle Unlocks

| Downstream Cycle | What it uses from 17B |
|-----------------|----------------------|
| **17C** (State Persistence) | `Gap` data model for state serialization. `load_schema()` to read current state before updates |
| **17D** (Pipeline Integration) | `load_schema()` for pre-research gap check. `sort_gaps()` for selecting which gaps to research. `validate_gaps()` for early error detection |
| **All future cycles** | `Gap` becomes the standard unit of research intelligence |

---

## Risk Mitigations Addressed

| Risk ID | Risk | How 17B addresses it |
|---------|------|---------------------|
| F2.1 | Malformed schema crashes pipeline | `load_schema()` catches YAML parse errors, wraps in `SchemaError` with descriptive message |
| F2.2 | Circular dependencies silently drop gaps | `detect_cycles()` reports exact cycle paths; `sort_gaps()` includes cycled nodes with warning |
| F2.3 | Priority calculation edge cases | `validate_gaps()` enforces priority range 1-5; sorter handles all-unknown case |
| F2.5 | Schema version mismatch | Parser handles missing optional fields with defaults (forward-compatible) |
| Edge Case 1 | Empty schema (all unknown) | Parser returns `is_empty`; sorter falls back to priority-only ordering |
| Edge Case 2 | Fully populated schema | Sorter returns all gaps; pipeline decides whether to research (not sorter's job) |
| Edge Case 6 | Circular deps + conflicting status | Validator catches status/timestamp contradictions; cycle detector catches circular deps |

---

## New Dependency

**Add `PyYAML>=6.0` to `requirements.txt`.** PyYAML is the standard YAML parser for Python. `yaml.safe_load()` is used (never `yaml.load()`) to prevent arbitrary code execution from YAML files.

---

## Implementation Sessions

Each session = one commit of ~50-80 lines.

| Session | Commit message | Files touched |
|---------|---------------|---------------|
| 1 | `feat(17B-1): add Gap data model with GapStatus enum` | `research_agent/schema.py`, `tests/test_schema.py` |
| 2 | `feat(17B-2): add YAML schema parser with SchemaResult` | `research_agent/schema.py`, `tests/test_schema.py`, `requirements.txt` |
| 3 | `feat(17B-3): add schema validator with multi-error reporting` | `research_agent/schema.py`, `tests/test_schema.py` |
| 4 | `feat(17B-4): add DFS-based cycle detector for gap dependencies` | `research_agent/schema.py`, `tests/test_schema.py` |
| 5 | `feat(17B-5): add priority sorter with topological ordering` | `research_agent/schema.py`, `tests/test_schema.py` |

After all 5 sessions: run full test suite (`python3 -m pytest tests/ -v`) to verify all existing tests + new tests pass.
