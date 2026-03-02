---
status: complete
priority: p3
issue_id: "111"
tags: [code-review, quality, naming]
dependencies: []
unblocks: []
sub_priority: 3
---

# Inconsistent `_skip_iteration` vs `skip_critique` attribute naming

## Problem Statement

`skip_critique` is stored as `self.skip_critique` (no underscore — public), but `skip_iteration` is stored as `self._skip_iteration` (underscore — private). Both are the same kind of opt-out flag. The inconsistency is confusing.

## Findings

- **pattern-recognition-specialist**: P3 — naming convention inconsistency

**Location:** `research_agent/agent.py:77-78`

## Proposed Solutions

### Option A: Make both private (Recommended)
Change `self.skip_critique` to `self._skip_critique` and update the one reference in `_run_critique()`.

- **Effort:** Small
- **Risk:** Low — internal attribute, not part of public API

### Option B: Make both public
Change `self._skip_iteration` to `self.skip_iteration`.

## Acceptance Criteria

- [ ] Both opt-out flags use consistent naming convention
