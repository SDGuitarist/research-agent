---
title: Auto-Compact Mid-Cycle Risks and Mitigations
date: 2026-02-11
category: workflow
tags: [context-window, auto-compact, claude-code, session-management, compound-engineering]
module: general
symptoms: [lost-plan-details, inconsistent-multi-file-edits, repeated-investigation, stale-task-state]
severity: medium
summary: Auto-compact during multi-step work can lose nuanced context. Mitigate by writing plans to disk, committing frequently, compacting proactively between phases, and using CLAUDE.md for critical context.
---

# Auto-Compact Mid-Cycle Risks and Mitigations

## Problem

Claude Code's auto-compact fires when the context window is full. There is no hook to warn at a custom threshold (e.g., 7% remaining). If it triggers mid-cycle — during a multi-step plan, debugging session, or multi-file refactor — it can silently degrade work quality.

## Risks

### 1. Plan details get flattened
Compaction summarizes earlier messages. Nuanced decisions, edge cases, and user preferences from earlier in the session can get lost or oversimplified.

### 2. Multi-file edit coherence breaks
Editing files A, B, and C that need to stay in sync — if compaction happens after A and B but before C, the summary may not preserve the exact changes, leading to inconsistencies.

### 3. Reasoning chain breaks
Mid-debugging or mid-refactor, the "why" behind earlier decisions can vanish. This leads to re-investigating resolved issues or contradicting earlier fixes.

### 4. Task state becomes stale
Todo lists, dependency chains, and in-progress tracking get compressed into vague summaries.

### 5. Tool output loss
Detailed grep results, test output, or error messages from earlier get summarized away. If those details matter for a later step, they're gone.

## Mitigations

### Proactive compaction
Run `/compact` between phases (after brainstorm, after plan, etc.) with a custom prompt so *you* control what gets preserved — not the auto-compactor.

### Write everything to disk
- Plans go in `docs/plans/`, not just conversation
- Brainstorms go in `docs/brainstorms/`
- Solutions go in `docs/solutions/`
- Task tracking in `todos/`

Anything on disk compounds; anything only in context is ephemeral.

### Commit frequently
Code on disk is never lost to compaction. Incremental commits (~50-100 lines) act as checkpoints.

### Use CLAUDE.md for critical context
CLAUDE.md is re-injected into every message. Put architecture decisions, conventions, and key constraints there so they survive any compaction.

### Small, focused sessions
One feature per session reduces the blast radius of a mid-cycle compact.

### PreCompact hook (partial)
You can get notified *when* auto-compact fires (but not before):
```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Auto-compacting now...\" with title \"Claude Code\"'"
          }
        ]
      }
    ]
  }
}
```

## Current Limitation

As of Feb 2026, Claude Code hooks do not expose context window usage metrics. There is no way to trigger a warning at a specific percentage threshold. The `PreCompact` hook fires only when the window is already full.

A feature request for a `ContextThreshold` hook event (configurable percentage triggers) would solve this: [github.com/anthropics/claude-code/issues](https://github.com/anthropics/claude-code/issues)

## Key Lesson

The compound engineering principle "write it down" is the strongest defense against context loss. Disk is permanent; context is ephemeral.
