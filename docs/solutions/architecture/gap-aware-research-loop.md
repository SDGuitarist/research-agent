---
title: "Gap-Aware Research Loop: Schema, Staleness, and State Persistence"
date: 2026-02-15
category: architecture
tags: [gap-schema, staleness, state-persistence, token-budget, context-result, atomic-writes, frozen-dataclass]
module: research_agent (schema, staleness, state, token_budget, context_result, safe_io, cycle_config, errors)
symptoms:
  - Research agent re-investigates topics it already knows about
  - Context window overflow on large research runs
  - No way to distinguish "missing config file" from "config load failed"
  - State file corruption on interrupted writes
  - No audit trail for gap status changes
severity: high
summary: >
  Cycle 17 added a complete gap-aware research loop across four sub-cycles (17A-17D).
  The agent can now track knowledge gaps in a YAML schema, detect staleness via per-gap TTLs,
  skip redundant research, enforce token budgets, and persist state atomically. Eight new modules,
  ~910 lines of production code, 23 commits including 21 review findings resolved.
---

# Gap-Aware Research Loop

## Problem

Before Cycle 17, the research agent treated every query as a fresh investigation. It had no memory of what it already knew, no way to detect when information became stale, and no mechanism to prevent context window overflow on large runs. Specific symptoms:

1. **Redundant research** — re-investigating verified topics wastes API calls and time
2. **Context window overflow** — large synthesis prompts silently failed when they exceeded model limits
3. **Silent degradation** — `load_full_context()` returned `None` for both "no config file" and "config file failed to read," making debugging impossible
4. **State corruption risk** — interrupted writes could produce partial YAML files
5. **No audit trail** — gap status changes were invisible, making debugging stale data impossible

## Root Cause

The agent lacked three capabilities: (1) a structured representation of what it knows and doesn't know (gap schema), (2) temporal awareness of when knowledge expires (staleness), and (3) safe persistence to survive across runs (atomic state writes).

## Solution

Built across four sub-cycles with strict dependency ordering:

### 17A: Foundation Infrastructure (5 modules)

| Module | Purpose |
|--------|---------|
| `errors.py` | Exception hierarchy: `ContextError`, `SchemaError`, `StateError` — specific catches instead of bare `except Exception` |
| `context_result.py` | Four-state result type (`loaded`, `not_configured`, `empty`, `failed`) replacing `str \| None` |
| `token_budget.py` | Priority-based budget allocation — prunes lowest-priority components first (metadata before sources, never prune instructions) |
| `safe_io.py` | Atomic file writes via tempfile + rename, with symlink protection |
| `cycle_config.py` | Frozen dataclass for batch limits: `max_gaps_per_run`, `max_tokens_per_prompt`, `default_ttl_days` |

### 17B: Gap Schema Layer (1 module, 5 capabilities)

`schema.py` provides:
- **Gap data model** — frozen dataclass with `id`, `category`, `status` (enum), `priority`, `ttl_days`, `blocks`/`blocked_by` (tuples)
- **YAML parser** — `load_schema()` returns three-way result: loaded, empty, not_configured
- **Validator** — reports ALL errors (not just first), checks status/timestamp consistency, reference integrity
- **Cycle detector** — DFS on the `blocks`/`blocked_by` DAG, returns specific cycle nodes
- **Priority sorter** — topological sort (Kahn's algorithm) with priority tiebreaking

### 17C: State Persistence + Staleness (2 modules)

`state.py`:
- `save_schema()` — serializes gaps to YAML via `atomic_write()`
- `mark_verified(gap)` — sets `last_verified` to now, status to `VERIFIED`
- `mark_checked(gap)` — sets `last_checked` to now (searched but found nothing new)

`staleness.py`:
- `detect_stale()` — compares `last_verified` against per-gap `ttl_days` (no cascade through dependencies)
- `select_batch()` — caps stale gaps per run to prevent overload
- `log_flip()` — append-only audit log of status transitions

### 17D: Pipeline Integration (modifications to existing modules)

- `context.py` — all loaders return `ContextResult` instead of `str | None`
- `synthesize.py` — `allocate_budget()` called before prompt construction; components pruned by priority
- `relevance.py` — new `no_new_findings` decision (searched, scored, all below cutoff)
- `agent.py` — pre-research gap check (skip if all verified+fresh), post-research state update (close the loop)

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No cascade on staleness | If gap A blocks gap B and A goes stale, B stays verified. Prevents one stale gap flipping 80% of the graph (F4.1). |
| Per-gap TTL, not global | Founding dates age differently than pricing data. `ttl_days` per gap. |
| Char-based token counting | `1 token ~ 4 chars` avoids 8-16 API calls per run. Budget allocation is approximate anyway. |
| Priority-based pruning order | `staleness_metadata(1) < previous_baseline(2) < gap_schema(3) < business_context(4) < sources(5) < instructions(6, never prune)` |
| `mark_checked` vs `mark_verified` | Prevents infinite re-research: "we looked and found nothing" is a valid state (Edge Case 7). |
| Frozen dataclasses + tuples | Immutability ensures state changes are intentional. `tuple[Gap, ...]` not `list[Gap]`. |

## Review Findings (21 items)

The multi-agent review caught 3 P1, 9 P2, and 9 P3 issues. Notable fixes:

- **P1: Bare `except Exception`** in `token_budget.py` — narrowed to specific exceptions
- **P1: New Anthropic client per `count_tokens` call** — switched to char-based estimate entirely
- **P1: NoneType crash** in `_update_gap_states` — added None guard on `_current_research_batch`
- **P2: Mutable dict on frozen Gap** — removed unused `metadata` field
- **P2: Duplicated budget pruning** — extracted `_apply_budget_pruning()` helper
- **P2: Symlink race in `atomic_write`** — added `resolve()` + symlink check before write

3 findings were **rejected** as foundation code for future cycles (dead code that will be used by Cycles 18+).

## Prevention

1. **Run failure mode analysis before building multi-module features** — Cycle 17's research docs (17-01 through 17-05) directly informed every design decision
2. **Foundation modules first, integration last** — 17A/17B/17C were independently testable before 17D wired them together
3. **Use frozen dataclasses for configuration** — catches invalid config at construction time, not at runtime
4. **Atomic writes for any persistent state** — `safe_io.atomic_write()` should be the default for all file writes, not just gap state
5. **Four-state result types over None** — `ContextResult` pattern should be reused anywhere `None` conflates multiple failure modes

## Cross-References

- [Source-Level Relevance Aggregation](../logic-errors/source-level-relevance-aggregation.md) — Cycle 15's per-source scoring is the foundation for the `no_new_findings` gate decision
- [Adversarial Verification Pipeline](../logic-errors/adversarial-verification-pipeline.md) — Cycle 16's draft-skeptic-final pipeline runs inside the token budget envelope
- [Model String Unification](../architecture/model-string-unification.md) — frozen dataclass pattern reused for `CycleConfig`
- [Agent-Native Return Structured Data](../architecture/agent-native-return-structured-data.md) — future integration point: gap state should be part of the structured return
- [Adaptive Batch Backoff](../performance-issues/adaptive-batch-backoff.md) — eliminates fixed delays in the gap research loop

## Stats

- **Commits:** 23 (20 implementation + 3 review fix batches)
- **New modules:** 8 (~910 lines production code)
- **Modified modules:** 5 (agent, context, synthesize, relevance, errors)
- **New tests:** ~160 (total suite grew from 385 to 542)
- **Review findings:** 21 found, 18 resolved, 3 rejected as intentional
- **Research docs:** 5 pre-implementation analyses + integration assessment
