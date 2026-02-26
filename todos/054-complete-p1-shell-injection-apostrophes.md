---
status: complete
priority: p1
issue_id: "054"
tags: [code-review, security]
dependencies: []
---

# P1: Shell command injection via apostrophes in query text

## Problem Statement

The `/research:queue` skill constructs a shell command by interpolating user-provided query text in single quotes:
```
python3 main.py --{mode} '{query}' -o {output_path}
```

Single quotes do NOT protect against queries containing literal apostrophes (extremely common in English: "What's", "don't", "it's"). A query like `"What's the best async library?"` breaks out of single-quote context. A crafted query could execute arbitrary shell commands.

**Location:** `.claude/skills/research-queue.md` lines 98-99 (Step 5, item 4)

## Findings

- **security-sentinel**: HIGH severity. Apostrophes are common in English — this will break real queries, not just theoretical attacks.
- Threat model is single-user (user attacks themselves), so malicious exploitation is low risk. But accidental breakage from normal queries is high likelihood.
- The query text comes from a hand-edited markdown file, so the user controls the input, but they shouldn't need to worry about shell escaping.

## Proposed Solutions

### Option A: Escape single quotes in skill instructions (Recommended)
Add instruction to Step 5: "Before constructing the command, escape single quotes in the query text: replace every `'` with `'\''`"
- **Pros:** Simple, standard shell idiom, handles all cases
- **Cons:** Relies on Claude correctly applying the escaping
- **Effort:** Small
- **Risk:** Low

### Option B: Use double quotes with escaping
Switch to double quotes and escape `"`, `$`, `` ` ``, `\` in the query.
- **Pros:** Handles apostrophes naturally
- **Cons:** More characters to escape, dollar signs in queries would need escaping
- **Effort:** Small
- **Risk:** Medium (more escape rules to get right)

## Recommended Action

Option A — add single-quote escaping instruction.

## Technical Details

- **Affected files:** `.claude/skills/research-queue.md`
- **Components:** Step 5 (Launch Background Agents)

## Acceptance Criteria

- [ ] Queries containing apostrophes (e.g., "What's the best...") work correctly
- [ ] No shell metacharacter injection possible from query text
- [ ] Escaping instruction is clear enough for Claude to follow consistently

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2026-02-26 | Created from code review | security-sentinel finding |

## Resources

- PR: feat/background-research-agents
- Shell quoting reference: `'\''` idiom closes quote, adds escaped literal, reopens
