# Cycle 17C: State Persistence + Staleness Detection — Implementation Plan

**Date:** 2026-02-15
**Cycle:** 17C (State Persistence + Staleness Detection)
**Scope:** State writer, timestamp management, staleness detection, batch limiter, audit log
**Inputs:** `cycle-17-05-cycle-breakdown.md`, `cycle-17-03-failure-modes.md`, `cycle-17-04-edge-cases.md`, Cycles 17A + 17B implementation
**Estimated total lines:** ~240
**Estimated commits:** 5

---

## Purpose

Make the gap schema layer from 17B persistent and temporal. After a research run, updated gap statuses are written back to disk. Staleness detection compares timestamps against per-gap TTLs to identify what needs re-research. A batch limiter prevents overload, and an audit log makes status flips debuggable. This cycle closes the gap between "read-only schema" (17B) and "stateful research loop" (17D).

---

## 17A/17B Foundation Used

| Component | From | How 17C Uses It |
|-----------|------|-----------------|
| `atomic_write()` | `safe_io.py` (17A) | State writer uses it for every disk write — prevents partial-write corruption (F3.3, F4.4) |
| `StateError` | `errors.py` (17A) | Raised on state write/read failures |
| `SchemaError` | `errors.py` (17A) | Raised if re-validation fails after gap update |
| `CycleConfig` | `cycle_config.py` (17A) | `default_ttl_days` for gaps without their own TTL, `max_gaps_per_run` for batch limiting |
| `Gap` / `GapStatus` | `schema.py` (17B) | The data model that state.py serializes and staleness.py operates on |
| `load_schema()` | `schema.py` (17B) | State writer loads current schema before updating individual gaps |
| `SchemaResult` | `schema.py` (17B) | Return type from `load_schema()`, used in update_gap flow |
| `validate_gaps()` | `schema.py` (17B) | Re-validates after mutations to ensure consistency |

---

## Build Order

```
Session 1: State writer (save_schema + _gap_to_dict helper)
    ↓
Session 2: Timestamp management (mark_checked + mark_verified)
    ↓
Session 3: Staleness detector (detect_stale)
    ↓
Session 4: Batch limiter (select_batch)
    ↓
Session 5: Audit logger (log_flip)
```

Sessions 1-2 go into `state.py`. Sessions 3-5 go into `staleness.py`. Each session depends on the previous: the staleness detector needs timestamps to compare, the batch limiter post-processes staleness results, and the audit logger records the flips that staleness detection triggers.

---

## Deliverable 1: State Writer

**File:** `research_agent/state.py` (new)
**Test file:** `tests/test_state.py` (new)
**Estimated lines:** ~60 in module, ~55 in test file

### What it does

Serializes `Gap` objects back to YAML and writes them to disk via `atomic_write()`. Provides `save_schema()` for full writes and `update_gap()` for single-gap mutations. The update flow is: load → find → replace → validate → save. Since `Gap` is frozen, "replace" means constructing a new `Gap` with updated fields.

### Design

```python
from dataclasses import asdict
from pathlib import Path

import yaml

from .errors import SchemaError, StateError
from .safe_io import atomic_write
from .schema import Gap, GapStatus, SchemaResult, load_schema, validate_gaps


def _gap_to_dict(gap: Gap) -> dict:
    """Convert a Gap to a YAML-serializable dict.

    Converts GapStatus enum to its string value, tuples to lists,
    and omits fields that are at their default values to keep YAML clean.
    """


def save_schema(path: Path | str, gaps: tuple[Gap, ...]) -> None:
    """Write gaps to a YAML schema file atomically.

    Args:
        path: Target file path.
        gaps: Gap objects to serialize.

    Raises:
        StateError: If the write fails (via atomic_write).
    """


def update_gap(
    path: Path | str,
    gap_id: str,
    **changes: object,
) -> Gap:
    """Load schema, update one gap's fields, validate, and save.

    Since Gap is frozen, constructs a new Gap with the updated fields.
    Re-validates the full gap set after mutation to ensure consistency.

    Args:
        path: Path to the YAML schema file.
        gap_id: ID of the gap to update.
        **changes: Field names and new values (e.g., status=GapStatus.VERIFIED).

    Returns:
        The updated Gap object.

    Raises:
        StateError: If the gap_id is not found in the schema.
        SchemaError: If the updated schema fails validation.
    """
```

### Acceptance criteria

1. `save_schema()` produces valid YAML that `load_schema()` can read back
2. Round-trip: `save_schema()` then `load_schema()` returns identical `Gap` objects
3. `save_schema()` calls `atomic_write()` — never uses `Path.write_text()` directly
4. `_gap_to_dict()` converts `GapStatus` enum to string, tuples to lists
5. `_gap_to_dict()` omits default-valued fields to keep YAML clean (e.g., no `findings: ""`)
6. `update_gap()` raises `StateError` if the gap ID is not found
7. `update_gap()` re-validates after mutation — raises `SchemaError` if the update creates inconsistencies
8. `update_gap()` does not modify other gaps in the file

### Test requirements

| Test | Validates |
|------|-----------|
| `test_save_load_roundtrip` | Save gaps to YAML, load them back, get identical `Gap` objects |
| `test_save_uses_atomic_write` | `save_schema` calls `atomic_write`, not `Path.write_text` (mock verification) |
| `test_gap_to_dict_converts_enum` | `GapStatus.VERIFIED` → `"verified"` in output dict |
| `test_gap_to_dict_omits_defaults` | Fields at default values (empty `findings`, empty `blocks`) omitted |
| `test_gap_to_dict_converts_tuples` | `blocks` tuple → list in output dict |
| `test_update_gap_changes_field` | `update_gap(path, "pricing", priority=5)` changes only that gap's priority |
| `test_update_gap_unknown_id_raises` | `update_gap(path, "nonexistent", ...)` raises `StateError` |
| `test_update_gap_invalid_state_raises` | Update that creates `status=verified, last_verified=None` raises `SchemaError` |
| `test_update_gap_preserves_others` | Other gaps in the file are unchanged after update |

### Dependencies

- `atomic_write()` from `safe_io.py` (17A)
- `StateError`, `SchemaError` from `errors.py` (17A)
- `Gap`, `GapStatus`, `load_schema`, `validate_gaps` from `schema.py` (17B)

---

## Deliverable 2: Timestamp Management

**File:** `research_agent/state.py` (append to existing)
**Test file:** `tests/test_state.py` (append to existing)
**Estimated lines:** ~35 in module, ~40 in test file

### What it does

Provides `mark_checked()` and `mark_verified()` — two functions that return new `Gap` instances with updated timestamps. The distinction between "checked" and "verified" prevents the infinite re-research loop (F4.6): a gap that was searched but yielded no results still gets `last_checked` updated, so it won't be re-searched until its TTL expires.

### Design

```python
from dataclasses import replace
from datetime import datetime, timezone


def mark_checked(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with last_checked set to now.

    Updates last_checked only. Does NOT change status or last_verified.
    Use when a gap was researched but no new findings were found.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with updated last_checked.
    """


def mark_verified(gap: Gap, now: datetime | None = None) -> Gap:
    """Return a new Gap with status=VERIFIED and timestamps set to now.

    Updates last_verified, last_checked, and status. Use when a gap
    was researched and new findings were confirmed.

    Args:
        gap: The gap to update.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        New Gap with status=VERIFIED and fresh timestamps.
    """
```

### Acceptance criteria

1. `mark_checked()` sets `last_checked` to an ISO timestamp string
2. `mark_checked()` does NOT change `status`, `last_verified`, or any other field
3. `mark_verified()` sets `status` to `GapStatus.VERIFIED`
4. `mark_verified()` sets both `last_verified` and `last_checked` to the same timestamp
5. Both functions return a NEW `Gap` instance (original is unchanged — Gap is frozen)
6. Both accept an optional `now` parameter for deterministic testing
7. Timestamps are UTC in ISO 8601 format (e.g., `"2026-02-15T12:00:00+00:00"`)

### Test requirements

| Test | Validates |
|------|-----------|
| `test_mark_checked_sets_timestamp` | `last_checked` is updated to the provided `now` value |
| `test_mark_checked_preserves_status` | `status` is unchanged after `mark_checked` |
| `test_mark_checked_preserves_last_verified` | `last_verified` is unchanged |
| `test_mark_checked_returns_new_gap` | Original gap is not mutated; returned gap is a different object |
| `test_mark_verified_sets_status` | `status` becomes `GapStatus.VERIFIED` |
| `test_mark_verified_sets_both_timestamps` | Both `last_verified` and `last_checked` are set to the same value |
| `test_mark_verified_returns_new_gap` | Original gap is not mutated |
| `test_timestamps_are_iso_utc` | Timestamps match ISO 8601 format with UTC timezone |

### Dependencies

- Deliverable 1 (same file, uses `Gap` and `GapStatus`)

---

## Deliverable 3: Staleness Detector

**File:** `research_agent/staleness.py` (new)
**Test file:** `tests/test_staleness.py` (new)
**Estimated lines:** ~60 in module, ~50 in test file

### What it does

Compares each gap's `last_verified` timestamp against its `ttl_days` to identify stale gaps. Only flips the gap's own status — does NOT cascade through the dependency graph (prevents F4.1). Returns a list of gaps that transitioned from `VERIFIED` to `STALE`. Gaps with `status: unknown` are never flipped (they were never verified in the first place).

### Design

```python
from datetime import datetime, timezone

from .cycle_config import CycleConfig
from .schema import Gap, GapStatus


def detect_stale(
    gaps: tuple[Gap, ...],
    default_ttl_days: int = 30,
    now: datetime | None = None,
) -> list[Gap]:
    """Identify gaps whose verified status has expired.

    Compares each VERIFIED gap's last_verified timestamp against its
    ttl_days (or default_ttl_days if the gap has no ttl_days set).

    Only checks gaps with status=VERIFIED. Gaps that are UNKNOWN,
    STALE, or BLOCKED are skipped — staleness is about freshness
    of verified intelligence, not about gaps that were never verified.

    Does NOT cascade through dependencies. If gap A blocks gap B
    and A goes stale, B's status is unchanged. This prevents the
    cascade bomb described in F4.1.

    Args:
        gaps: Gap objects to check.
        default_ttl_days: Fallback TTL for gaps without ttl_days.
        now: Override timestamp for testing. Defaults to UTC now.

    Returns:
        List of Gap objects with status flipped to STALE (new instances).
        Original Gap objects are unchanged.
    """
```

### Acceptance criteria

1. Returns gaps with `status` changed from `VERIFIED` to `STALE` (new instances)
2. Only checks gaps where `status == GapStatus.VERIFIED`
3. Skips `UNKNOWN` gaps — they were never verified, can't go stale
4. Skips `STALE` gaps — already stale, no double-flip
5. Skips `BLOCKED` gaps — their staleness depends on what blocks them (17D concern)
6. Uses the gap's own `ttl_days` when set; falls back to `default_ttl_days` when `ttl_days` is None
7. Does NOT cascade through `blocks`/`blocked_by` — each gap evaluated independently
8. Returns an empty list when no gaps are stale
9. Handles `last_verified` being `None` for a `VERIFIED` gap gracefully (treats as stale — this shouldn't happen if validation passed, but defensive)
10. Accepts an optional `now` parameter for deterministic testing

### Test requirements

| Test | Validates |
|------|-----------|
| `test_detect_stale_by_ttl` | Gap with `last_verified` older than `ttl_days` returned as stale |
| `test_detect_stale_fresh_gap` | Gap within TTL is NOT returned |
| `test_detect_stale_ignores_unknown` | `status: unknown` gaps are skipped |
| `test_detect_stale_ignores_already_stale` | `status: stale` gaps are skipped (no double-flip) |
| `test_detect_stale_ignores_blocked` | `status: blocked` gaps are skipped |
| `test_no_cascade_through_dependencies` | Gap A stale does NOT flip dependent gap B |
| `test_uses_gap_ttl_over_default` | Gap with `ttl_days=14` uses 14, not `default_ttl_days=30` |
| `test_uses_default_ttl_when_none` | Gap with `ttl_days=None` uses `default_ttl_days` |
| `test_stale_gap_has_new_status` | Returned gap has `status=STALE`, original unchanged |
| `test_empty_gaps_returns_empty` | Empty tuple input → empty list output |

### Dependencies

- `Gap`, `GapStatus` from `schema.py` (17B)
- `CycleConfig` from `cycle_config.py` (17A) — used for `default_ttl_days` parameter default

---

## Deliverable 4: Batch Limiter

**File:** `research_agent/staleness.py` (append to existing)
**Test file:** `tests/test_staleness.py` (append to existing)
**Estimated lines:** ~25 in module, ~30 in test file

### What it does

Selects the top N stale or unknown gaps by priority for a single research cycle. Prevents the "20 gaps stale at once" overload (Edge Case 3). Uses `CycleConfig.max_gaps_per_run` as the cap. Among gaps with equal priority, breaks ties by gap ID for deterministic ordering.

### Design

```python
def select_batch(
    gaps: tuple[Gap, ...] | list[Gap],
    max_per_run: int = 5,
) -> tuple[Gap, ...]:
    """Select the highest-priority gaps for a single research cycle.

    Sorts by priority (highest first), then by gap ID (alphabetical)
    for deterministic ordering. Returns at most max_per_run gaps.

    Args:
        gaps: Candidate gaps (typically stale + unknown gaps).
        max_per_run: Maximum gaps to return.

    Returns:
        Tuple of at most max_per_run Gap objects, sorted by priority.
    """
```

### Acceptance criteria

1. Returns at most `max_per_run` gaps
2. Sorts by priority descending (priority 5 before priority 1)
3. Breaks ties by gap ID alphabetically for deterministic results
4. Works with fewer gaps than `max_per_run` (returns all of them)
5. Works with an empty input (returns empty tuple)
6. Does not modify the input — returns a new tuple

### Test requirements

| Test | Validates |
|------|-----------|
| `test_batch_selects_highest_priority` | With 10 gaps and max=3, returns top 3 by priority |
| `test_batch_respects_limit` | Never returns more than `max_per_run` gaps |
| `test_batch_breaks_ties_by_id` | Gaps with same priority ordered alphabetically by ID |
| `test_batch_fewer_than_limit` | 2 gaps with max=5 returns all 2 |
| `test_batch_empty_input` | Empty input → empty tuple |
| `test_batch_returns_tuple` | Return type is tuple, not list |

### Dependencies

- `Gap` from `schema.py` (17B) — operates on `priority` and `id` fields

---

## Deliverable 5: Audit Logger

**File:** `research_agent/staleness.py` (append to existing)
**Test file:** `tests/test_staleness.py` (append to existing)
**Estimated lines:** ~40 in module, ~45 in test file

### What it does

Appends structured entries to an audit log file when a gap's status changes. Each entry records: timestamp, gap ID, old status, new status, and a reason string. The log is append-only — existing entries are never modified. This addresses F4.5 ("no undo / audit trail for automatic flips") and makes staleness behavior debuggable.

### Design

```python
from pathlib import Path
from datetime import datetime, timezone


def log_flip(
    log_path: Path | str,
    gap_id: str,
    old_status: GapStatus,
    new_status: GapStatus,
    reason: str,
    now: datetime | None = None,
) -> None:
    """Append a status flip event to the audit log.

    Each entry is a single line of structured text:
    [ISO_TIMESTAMP] gap_id: old_status -> new_status (reason)

    The log file is append-only. If it doesn't exist, it is created.
    Parent directories are created if needed.

    Args:
        log_path: Path to the audit log file.
        gap_id: ID of the gap that changed.
        old_status: Previous status.
        new_status: New status.
        reason: Human-readable reason for the flip (e.g., "TTL expired: 45 days > 30 day limit").
        now: Override timestamp for testing. Defaults to UTC now.
    """
```

### Acceptance criteria

1. Creates the log file if it doesn't exist
2. Creates parent directories if they don't exist
3. Appends to the file — existing entries are never overwritten
4. Each entry is a single line in the format: `[TIMESTAMP] gap_id: old -> new (reason)`
5. Timestamps are UTC ISO 8601
6. Accepts an optional `now` parameter for deterministic testing
7. Does not use `atomic_write()` — append-only semantics are safe (partial append leaves previous entries intact)
8. Raises `StateError` if the write fails

### Test requirements

| Test | Validates |
|------|-----------|
| `test_log_flip_creates_file` | Log file created when it doesn't exist |
| `test_log_flip_appends` | Second call appends, doesn't overwrite first entry |
| `test_log_flip_format` | Entry matches `[TIMESTAMP] gap_id: old -> new (reason)` format |
| `test_log_flip_creates_parent_dirs` | Non-existent parent directories created |
| `test_log_flip_uses_utc` | Timestamp is UTC ISO 8601 |
| `test_log_flip_custom_timestamp` | Provided `now` parameter used instead of system clock |
| `test_log_flip_records_reason` | Reason string appears in the entry |
| `test_log_flip_write_error_raises` | Write failure raises `StateError` |

### Dependencies

- `GapStatus` from `schema.py` (17B) — for status enum values
- `StateError` from `errors.py` (17A) — for write failure errors

---

## Summary Table

| # | Deliverable | File (module) | File (tests) | Est. Lines (module) | Est. Lines (tests) | Depends On |
|---|-------------|---------------|--------------|--------------------|--------------------|------------|
| 1 | State writer | `research_agent/state.py` (new) | `tests/test_state.py` (new) | ~60 | ~55 | 17A (`atomic_write`, `StateError`, `SchemaError`), 17B (`Gap`, `load_schema`, `validate_gaps`) |
| 2 | Timestamp management | `research_agent/state.py` (append) | `tests/test_state.py` (append) | ~35 | ~40 | #1 (same file) |
| 3 | Staleness detector | `research_agent/staleness.py` (new) | `tests/test_staleness.py` (new) | ~60 | ~50 | 17A (`CycleConfig`), 17B (`Gap`, `GapStatus`) |
| 4 | Batch limiter | `research_agent/staleness.py` (append) | `tests/test_staleness.py` (append) | ~25 | ~30 | 17B (`Gap`) |
| 5 | Audit logger | `research_agent/staleness.py` (append) | `tests/test_staleness.py` (append) | ~40 | ~45 | 17A (`StateError`), 17B (`GapStatus`) |
| | **Totals** | **2 new modules** | **2 new test files** | **~220** | **~220** | |

---

## What This Cycle Does NOT Touch

- **No changes to `agent.py`** — pipeline integration is Cycle 17D
- **No changes to `context.py`** — context refactoring is Cycle 17D
- **No changes to `schema.py`** — 17B's module is read-only for 17C; `state.py` wraps it
- **No changes to existing test files** — all existing tests must pass unchanged
- **No cascade logic** — staleness does NOT propagate through `blocks`/`blocked_by`
- **No delta output** — comparing before/after states is Cycle 23
- **No Google Drive** — deferred to Cycle 22

---

## What This Cycle Unlocks

| Downstream Cycle | What it uses from 17C |
|-----------------|----------------------|
| **17D** (Pipeline Integration) | `save_schema()` + `mark_verified()` + `mark_checked()` for post-research state update. `detect_stale()` + `select_batch()` for pre-research gap selection |
| **23** (Delta Output) | Persistent state enables before/after comparison — the foundation for delta reports |
| **All future cycles** | Audit log provides debugging and traceability for any gap status change |

---

## Risk Mitigations Addressed

| Risk ID | Risk | How 17C addresses it |
|---------|------|---------------------|
| F4.1 | Cascading status flips | `detect_stale()` evaluates each gap independently — no dependency traversal |
| F4.2 | One-size-fits-all TTL | Per-gap `ttl_days` with `default_ttl_days` fallback from `CycleConfig` |
| F4.4 | State file write corruption | `save_schema()` delegates to `atomic_write()` from 17A |
| F4.5 | No undo / audit trail | `log_flip()` records every status change with timestamp and reason |
| F4.6 | Infinite re-research loop | `mark_checked()` vs `mark_verified()` distinction — searched-but-nothing-found still updates `last_checked` |
| F3.3 | Baseline state corruption | All writes go through `atomic_write()` — no partial writes |
| Edge Case 1 | Empty schema (all unknown) | `detect_stale()` skips `UNKNOWN` gaps — they can't go stale |
| Edge Case 3 | 20 gaps stale at once | `select_batch()` caps how many stale gaps are processed per run |

---

## Implementation Sessions

Each session = one commit of ~40-70 lines.

| Session | Commit message | Files touched |
|---------|---------------|---------------|
| 1 | `feat(17C-1): add state writer with atomic YAML persistence` | `research_agent/state.py`, `tests/test_state.py` |
| 2 | `feat(17C-2): add timestamp management (mark_checked, mark_verified)` | `research_agent/state.py`, `tests/test_state.py` |
| 3 | `feat(17C-3): add staleness detector with per-gap TTL` | `research_agent/staleness.py`, `tests/test_staleness.py` |
| 4 | `feat(17C-4): add batch limiter for stale gap selection` | `research_agent/staleness.py`, `tests/test_staleness.py` |
| 5 | `feat(17C-5): add audit logger for status flip tracking` | `research_agent/staleness.py`, `tests/test_staleness.py` |

After all 5 sessions: run full test suite (`python3 -m pytest tests/ -v`) to verify all existing tests + new tests pass.
