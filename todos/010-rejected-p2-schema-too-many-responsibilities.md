---
status: rejected
triage_reason: "Rejected — resolves naturally since 004 (foundation code) is kept"
priority: p2
issue_id: "010"
tags: [code-review, architecture, srp]
dependencies: ["004"]
---

# schema.py has too many responsibilities

## Problem Statement

`schema.py` at 362 lines bundles 4 concerns: data model, YAML parsing, validation, and graph algorithms. This violates Single Responsibility Principle.

## Findings

- **Architecture strategist**: Recommends splitting into `schema.py` (model), `schema_parser.py`, `schema_validator.py`, `gap_graph.py`.
- **Simplicity reviewer**: If dead code (finding 004) is removed first, this shrinks to ~160 lines which may be acceptable.

**File:** `research_agent/schema.py` (362 lines)

## Proposed Solutions

### Option A: Remove dead code first, reassess (Recommended)
After removing `detect_cycles`, `sort_gaps`, `validate_gaps` per finding 004, the file shrinks to ~160 lines (model + parser). This is acceptable for a single file.
- **Effort**: Small (done via 004) | **Risk**: Low

### Option B: Full split into 4 modules
- **Effort**: Large | **Risk**: Medium (import changes across codebase)

## Acceptance Criteria

- [ ] After dead code removal, file is under 200 lines
- [ ] Each remaining function has a single clear responsibility

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-15 | Created from code review | Depends on 004 being done first |
