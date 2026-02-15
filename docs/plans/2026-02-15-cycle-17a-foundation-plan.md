# Cycle 17A: Foundation Infrastructure — Implementation Plan

**Date:** 2026-02-15
**Cycle:** 17A (Foundation Infrastructure)
**Scope:** Error hierarchy, ContextResult type, token budgeting, atomic writes, CycleConfig dataclass
**Inputs:** `cycle-17-01` through `cycle-17-05`, `master-recommendations-future-cycles.md`
**Estimated total lines:** ~220
**Estimated commits:** 5

---

## Purpose

Build the shared utilities that every subsequent cycle (17B, 17C, 17D) depends on. Zero feature code — only error types, result types, token math, safe I/O, and cycle configuration. Each component is a standalone, testable module with no external dependencies.

---

## Build Order

```
Session 1: errors.py (expand exception hierarchy)
    ↓
Session 2: context_result.py (new — three-way result type)
    ↓
Session 3: token_budget.py (new — token counting + budget allocation)
    ↓
Session 4: safe_io.py (new — atomic file writes)
    ↓
Session 5: cycle_config.py (new — CycleConfig dataclass)
```

Each session depends on the one above it only for exception types (Session 1). Sessions 2-5 are otherwise independent but are ordered by downstream urgency.

---

## Deliverable 1: Exception Hierarchy Expansion

**File:** `research_agent/errors.py` (modify existing)
**Test file:** `tests/test_errors.py` (new)
**Estimated lines:** ~30 added to errors.py, ~40 in test file

### What it does

Adds new exception classes for context loading, schema parsing, and state persistence failures. Every subsequent module raises specific errors instead of generic `ValueError` or `Exception`.

### Current state

```python
ResearchError (base)
├── SearchError
├── SynthesisError
└── SkepticError
```

### Target state

```python
ResearchError (base)
├── SearchError
├── SynthesisError
├── SkepticError
├── ContextError                # Base for all context loading failures
│   ├── ContextLoadError        # Transient failure (network, file I/O) — retryable
│   └── ContextAuthError        # Auth expired — user action required
├── SchemaError                 # YAML parse or validation failure
└── StateError                  # State file read/write/corruption failure
```

### Acceptance criteria

1. All six new exceptions are subclasses of `ResearchError`
2. `ContextLoadError` and `ContextAuthError` are subclasses of `ContextError`
3. Each exception can carry a message string
4. `SchemaError` can carry a list of validation errors (not just the first one) via `errors: list[str]` attribute
5. Existing exceptions (`SearchError`, `SynthesisError`, `SkepticError`) are unchanged
6. All existing 385 tests still pass

### Test requirements

| Test | Validates |
|------|-----------|
| `test_all_exceptions_subclass_research_error` | `ContextError`, `SchemaError`, `StateError` all subclass `ResearchError` |
| `test_context_error_hierarchy` | `ContextLoadError` and `ContextAuthError` subclass `ContextError` |
| `test_schema_error_carries_multiple_errors` | `SchemaError(errors=["err1", "err2"])` stores both errors, accessible via `.errors` |
| `test_exceptions_carry_message` | All new exceptions accept and store a message string |
| `test_existing_exceptions_unchanged` | `SearchError`, `SynthesisError`, `SkepticError` still exist and subclass `ResearchError` |

### Dependencies

None. First deliverable.

---

## Deliverable 2: ContextResult Type

**File:** `research_agent/context_result.py` (new)
**Test file:** `tests/test_context_result.py` (new)
**Estimated lines:** ~50 in module, ~60 in test file

### What it does

Replaces the current `str | None` return from context loaders with a typed result object that distinguishes four states: loaded, not_configured, empty, and failed. This is the cross-cutting pattern identified in Edge Cases 1, 2, 4, and 7 — the current `None` return conflates "no file exists" with "file exists but couldn't be read."

### Design

```python
from dataclasses import dataclass
from enum import Enum

class ContextStatus(Enum):
    LOADED = "loaded"               # Content available
    NOT_CONFIGURED = "not_configured"  # No context source set up
    EMPTY = "empty"                 # Source exists but has no content
    FAILED = "failed"              # Source exists but loading failed

@dataclass(frozen=True)
class ContextResult:
    content: str | None        # The actual content (only set when LOADED)
    status: ContextStatus      # Which of the four states
    source: str = ""           # Where it came from (file path, "google_drive", etc.)
    error: str = ""            # Error details when status is FAILED

    def __bool__(self) -> bool:
        """True only when content was successfully loaded."""
        return self.status == ContextStatus.LOADED and self.content is not None

    @classmethod
    def loaded(cls, content: str, source: str = "") -> "ContextResult": ...

    @classmethod
    def not_configured(cls, source: str = "") -> "ContextResult": ...

    @classmethod
    def empty(cls, source: str = "") -> "ContextResult": ...

    @classmethod
    def failed(cls, error: str, source: str = "") -> "ContextResult": ...
```

### Acceptance criteria

1. `ContextResult` is a frozen dataclass with four factory classmethods
2. `bool(result)` returns `True` only for `LOADED` status with non-None content
3. Factory methods enforce correct field combinations (e.g., `loaded()` requires non-empty content)
4. `failed()` factory requires a non-empty error string
5. `ContextStatus` enum has exactly four values
6. `source` field tracks where the content came from (for debugging)

### Test requirements

| Test | Validates |
|------|-----------|
| `test_loaded_result_is_truthy` | `bool(ContextResult.loaded("text"))` is `True` |
| `test_not_configured_is_falsy` | `bool(ContextResult.not_configured())` is `False` |
| `test_empty_is_falsy` | `bool(ContextResult.empty())` is `False` |
| `test_failed_is_falsy` | `bool(ContextResult.failed("timeout"))` is `False` |
| `test_loaded_carries_content` | `.content` returns the provided string |
| `test_failed_carries_error` | `.error` returns the error description |
| `test_source_tracks_origin` | `.source` returns the file path or identifier |
| `test_loaded_requires_content` | `ContextResult.loaded("")` raises `ValueError` — empty string is not valid content |
| `test_failed_requires_error` | `ContextResult.failed("")` raises `ValueError` — empty error is not informative |
| `test_result_is_frozen` | Attempting to set attributes raises `FrozenInstanceError` |

### Dependencies

- Deliverable 1 (errors.py) — `ContextResult.failed()` references `ContextLoadError` in docstring but does not import it. The two are connected conceptually but decoupled in code.

---

## Deliverable 3: Token Budget Utilities

**File:** `research_agent/token_budget.py` (new)
**Test file:** `tests/test_token_budget.py` (new)
**Estimated lines:** ~80 in module, ~70 in test file

### What it does

Provides token counting and budget allocation. This addresses the #1 risk from the failure mode analysis (F5.2: context window budget war). Before building any synthesis prompt, the pipeline will call `allocate_budget()` to ensure all components fit within the model's context limit.

### Design

```python
def count_tokens(text: str, model: str = "claude-sonnet-4-20250514") -> int:
    """Count tokens in text using anthropic's token counting.

    Falls back to a conservative character-based estimate (1 token ≈ 4 chars)
    if the anthropic tokenizer is unavailable.
    """

# Priority order for pruning (lowest priority pruned first)
COMPONENT_PRIORITY = {
    "staleness_metadata": 1,   # Cut first
    "previous_baseline": 2,
    "gap_schema": 3,
    "business_context": 4,
    "sources": 5,              # Cut last — sources are the research
    "instructions": 6,         # Never cut — these control output quality
}

@dataclass(frozen=True)
class BudgetAllocation:
    allocations: dict[str, int]   # component -> allowed tokens
    pruned: list[str]             # components that were pruned
    total: int                    # total tokens allocated

def allocate_budget(
    components: dict[str, str],     # component_name -> content
    max_tokens: int,                # model context limit
    reserved_output: int = 4096,    # tokens reserved for model output
    priorities: dict[str, int] | None = None,  # override default priorities
) -> BudgetAllocation:
    """Allocate token budget across prompt components.

    If total tokens exceed (max_tokens - reserved_output), prunes
    lowest-priority components first by truncating them.
    Each component keeps at least a minimum allocation (100 tokens)
    unless fully pruned.
    """
```

### Acceptance criteria

1. `count_tokens()` returns a positive integer for non-empty strings, 0 for empty strings
2. `count_tokens()` falls back to character-based estimate if anthropic tokenizer fails
3. `allocate_budget()` returns allocations that sum to at most `max_tokens - reserved_output`
4. When over budget, lowest-priority components (by `COMPONENT_PRIORITY`) are truncated first
5. Components with priority 6 (instructions) are never pruned
6. Each component gets at least 100 tokens minimum unless fully removed
7. `BudgetAllocation.pruned` lists components that were truncated
8. Works with an empty components dict (returns empty allocations)

### Test requirements

| Test | Validates |
|------|-----------|
| `test_count_tokens_returns_int` | Returns positive int for non-empty string, 0 for empty |
| `test_count_tokens_fallback` | With anthropic unavailable, falls back to char-based estimate |
| `test_allocate_within_limit` | Sum of allocations <= `max_tokens - reserved_output` |
| `test_allocate_prunes_lowest_priority` | Staleness metadata pruned before sources |
| `test_allocate_preserves_instructions` | Instructions component is never pruned |
| `test_allocate_preserves_minimum` | Non-pruned components get at least 100 tokens |
| `test_allocate_reports_pruned` | `.pruned` contains names of truncated components |
| `test_allocate_under_budget_no_pruning` | When under budget, all components get full allocation |
| `test_allocate_empty_components` | Empty dict returns empty allocations |
| `test_allocate_single_oversized_component` | One component larger than budget gets truncated |

### Dependencies

None. Standalone utility. (Uses `anthropic` library optionally for token counting, but falls back gracefully.)

---

## Deliverable 4: Atomic File Writer

**File:** `research_agent/safe_io.py` (new)
**Test file:** `tests/test_safe_io.py` (new)
**Estimated lines:** ~35 in module, ~45 in test file

### What it does

Provides `atomic_write(path, content)` — writes content to a temporary file in the same directory, then atomically renames it to the target path. This prevents the state file corruption failures F3.3 and F4.4 identified in the failure mode analysis. If the write fails mid-content (process killed, disk full), the original file is untouched.

### Design

```python
import os
import tempfile
from pathlib import Path

def atomic_write(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically.

    Writes to a temporary file in the same directory, then renames.
    If the write fails for any reason, the original file is unchanged.

    Args:
        path: Target file path
        content: Content to write
        encoding: File encoding (default utf-8)

    Raises:
        StateError: If the write fails (wraps underlying OSError)
    """
```

### Acceptance criteria

1. After `atomic_write(path, content)`, `path.read_text()` returns `content`
2. If the write raises mid-content, the original file at `path` is unchanged
3. Creates parent directories if they don't exist
4. Uses `os.rename()` (atomic on POSIX) not `shutil.move()`
5. Temp file is created in the same directory as target (ensures same filesystem for atomic rename)
6. Wraps underlying `OSError` in `StateError` from Deliverable 1
7. Cleans up temp file on failure (no orphaned temp files)

### Test requirements

| Test | Validates |
|------|-----------|
| `test_atomic_write_creates_file` | New file created with correct content |
| `test_atomic_write_overwrites_existing` | Existing file replaced with new content |
| `test_atomic_write_no_partial_on_error` | Simulated write failure leaves original file unchanged |
| `test_atomic_write_creates_parent_dirs` | Non-existent parent directories created automatically |
| `test_atomic_write_cleans_temp_on_failure` | No orphaned temp files after failure |
| `test_atomic_write_raises_state_error` | `OSError` wrapped in `StateError` |
| `test_atomic_write_preserves_encoding` | UTF-8 content with special characters survives round-trip |

### Dependencies

- Deliverable 1 (errors.py) — raises `StateError` on failure.

---

## Deliverable 5: CycleConfig Dataclass

**File:** `research_agent/cycle_config.py` (new)
**Test file:** `tests/test_cycle_config.py` (new)
**Estimated lines:** ~45 in module, ~40 in test file

### What it does

Centralizes batch-size limits and budget caps that control how much work a single research cycle does. Identified as a cross-cutting need in Edge Cases 1, 3, and 8 and recommended by the master recommendations document. Follows the same frozen dataclass pattern as `ResearchMode`.

### Design

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CycleConfig:
    """Configuration for a single research cycle's resource limits.

    Controls batch sizes and token budgets to prevent overload.
    Follows the frozen dataclass pattern from ResearchMode.
    """
    max_gaps_per_run: int = 5          # Max stale/unknown gaps to research per cycle
    max_tokens_per_prompt: int = 100000  # Context window budget for synthesis prompts
    reserved_output_tokens: int = 4096   # Tokens reserved for model output
    default_ttl_days: int = 30          # Default staleness TTL when gap has no ttl_days

    def __post_init__(self) -> None:
        """Validate configuration."""
        errors = []
        if self.max_gaps_per_run < 1:
            errors.append(f"max_gaps_per_run must be >= 1, got {self.max_gaps_per_run}")
        if self.max_tokens_per_prompt < 1000:
            errors.append(f"max_tokens_per_prompt must be >= 1000, got {self.max_tokens_per_prompt}")
        if self.reserved_output_tokens < 256:
            errors.append(f"reserved_output_tokens must be >= 256, got {self.reserved_output_tokens}")
        if self.default_ttl_days < 1:
            errors.append(f"default_ttl_days must be >= 1, got {self.default_ttl_days}")
        if self.reserved_output_tokens >= self.max_tokens_per_prompt:
            errors.append(
                f"reserved_output_tokens ({self.reserved_output_tokens}) must be < "
                f"max_tokens_per_prompt ({self.max_tokens_per_prompt})"
            )
        if errors:
            raise ValueError(f"Invalid CycleConfig: {'; '.join(errors)}")
```

### Acceptance criteria

1. `CycleConfig` is a frozen dataclass with sensible defaults
2. All defaults are usable without any arguments: `CycleConfig()` succeeds
3. `__post_init__` validates all fields and reports ALL errors (not just the first)
4. Invalid values raise `ValueError` with descriptive message
5. `reserved_output_tokens` must be less than `max_tokens_per_prompt`
6. Follows the same validation pattern as `ResearchMode.__post_init__`

### Test requirements

| Test | Validates |
|------|-----------|
| `test_default_config_valid` | `CycleConfig()` creates successfully with sensible defaults |
| `test_custom_config` | Custom values accepted: `CycleConfig(max_gaps_per_run=10)` |
| `test_invalid_gaps_per_run` | `max_gaps_per_run=0` raises `ValueError` |
| `test_invalid_tokens_per_prompt` | `max_tokens_per_prompt=500` raises `ValueError` |
| `test_reserved_exceeds_max` | `reserved_output_tokens >= max_tokens_per_prompt` raises `ValueError` |
| `test_reports_all_errors` | Multiple invalid fields reports all errors in one message |
| `test_config_is_frozen` | Attempting to set attributes raises `FrozenInstanceError` |

### Dependencies

None. Standalone dataclass.

---

## Summary Table

| # | Deliverable | File (module) | File (tests) | Est. Lines (module) | Est. Lines (tests) | Depends On |
|---|-------------|---------------|--------------|--------------------|--------------------|------------|
| 1 | Exception hierarchy | `research_agent/errors.py` (modify) | `tests/test_errors.py` (new) | ~30 | ~40 | — |
| 2 | ContextResult type | `research_agent/context_result.py` (new) | `tests/test_context_result.py` (new) | ~50 | ~60 | #1 (conceptual) |
| 3 | Token budget | `research_agent/token_budget.py` (new) | `tests/test_token_budget.py` (new) | ~80 | ~70 | — |
| 4 | Atomic file writer | `research_agent/safe_io.py` (new) | `tests/test_safe_io.py` (new) | ~35 | ~45 | #1 (`StateError`) |
| 5 | CycleConfig | `research_agent/cycle_config.py` (new) | `tests/test_cycle_config.py` (new) | ~45 | ~40 | — |
| | **Totals** | **4 new + 1 modified** | **5 new** | **~240** | **~255** | |

---

## What This Cycle Does NOT Touch

- **No changes to `agent.py`** — pipeline integration is Cycle 17D
- **No changes to `context.py`** — refactoring to use `ContextResult` is Cycle 17D
- **No changes to `synthesize.py`** — token budget enforcement is Cycle 17D
- **No changes to existing test files** — all 385 existing tests must pass unchanged
- **No YAML parsing** — that's Cycle 17B
- **No state persistence** — that's Cycle 17C
- **No Google Drive** — deferred to Cycle 22

---

## What This Cycle Unlocks

| Downstream Cycle | What it uses from 17A |
|-----------------|----------------------|
| **17B** (Gap Schema) | `SchemaError` for parse/validation failures |
| **17C** (State Persistence) | `atomic_write()` for safe file writes, `StateError` for failures |
| **17D** (Pipeline Integration) | `ContextResult` in context.py, `allocate_budget()` in synthesize.py, `CycleConfig` for batch limits |
| **All future cycles** | Consistent error hierarchy, token-aware prompt building |

---

## Risk Mitigations Addressed

| Risk ID | Risk | How 17A addresses it |
|---------|------|---------------------|
| F5.2 | Context window budget war (#1 risk) | `token_budget.py` with priority-based pruning |
| F5.3 | Exception hierarchy gaps (#8 risk) | Six new exception types before any feature code |
| F3.3 | Baseline state corruption (#7 risk) | `atomic_write()` prevents partial writes |
| F4.4 | State file write corruption (#9 risk) | Same — `atomic_write()` |
| F5.1 | Error cascade across features (#3 risk) | Distinct error types prevent catch-all swallowing |

---

## Implementation Sessions

Each session = one commit of ~40-80 lines.

| Session | Commit message | Files touched |
|---------|---------------|---------------|
| 1 | `feat: expand error hierarchy for context, schema, state` | `research_agent/errors.py`, `tests/test_errors.py` |
| 2 | `feat: add ContextResult type for three-way state distinction` | `research_agent/context_result.py`, `tests/test_context_result.py` |
| 3 | `feat: add token budget utilities with priority-based pruning` | `research_agent/token_budget.py`, `tests/test_token_budget.py` |
| 4 | `feat: add atomic file writer for safe state persistence` | `research_agent/safe_io.py`, `tests/test_safe_io.py` |
| 5 | `feat: add CycleConfig dataclass for batch limits` | `research_agent/cycle_config.py`, `tests/test_cycle_config.py` |

After all 5 sessions: run full test suite (`python3 -m pytest tests/ -v`) to verify all 385 existing tests + new tests pass.
