---
status: complete
priority: p3
issue_id: "062"
tags: [code-review, security]
dependencies: []
---

# P3: Error reasons in Failed entries may leak sensitive info

## Problem Statement

When a query fails, stderr output is recorded as a "brief error reason" in the queue file. This could contain API key prefixes, file paths, or internal URLs from stack traces.

**Location:** `.claude/skills/research-queue.md` Step 7 (lines 147-157)

## Findings

- **security-sentinel**: LOW severity. Queue file is local-only, but error sanitization is good practice.

## Proposed Solutions

### Option A: Add error sanitization instruction (Recommended)
"Truncate error reason to 100 chars. Strip strings matching API key patterns (sk-ant-*, tvly-*). Use only the final error message, not full stack traces."
- **Effort:** Small
- **Risk:** Low

## Acceptance Criteria

- [ ] Error reasons are truncated and sanitized before writing to queue file
- [ ] No API keys or full paths appear in Failed entries

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | security-sentinel finding |
