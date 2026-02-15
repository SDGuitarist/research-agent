---
status: rejected
triage_reason: "Rejected — params will be read when budget enforcement uses config"
priority: p2
issue_id: "007"
tags: [code-review, dead-code]
dependencies: []
---

# Dead CycleConfig parameters

## Problem Statement

`cycle_config.py:15-16` defines `max_tokens_per_prompt` and `reserved_output_tokens` but they are never read by any code. `synthesize.py` hardcodes `max_tokens=100_000` instead.

## Findings

- **Architecture strategist**: Dead parameters mislead future developers.
- **Simplicity reviewer**: Over-validated for 4 fields (28 lines of `__post_init__`).

**File:** `research_agent/cycle_config.py:15-16`

## Proposed Solutions

### Option A: Remove dead params (Recommended)
Remove `max_tokens_per_prompt` and `reserved_output_tokens`. Keep `max_gaps_per_run` and `default_ttl_days`.
- **Effort**: Small | **Risk**: Low

### Option B: Wire them through to synthesize.py
- **Effort**: Medium | **Risk**: Low

## Acceptance Criteria

- [ ] No dead parameters in CycleConfig
- [ ] All tests pass

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | 2/7 agents flagged this |
