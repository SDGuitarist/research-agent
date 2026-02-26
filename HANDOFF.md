# Handoff: Background Research Agents — Review + Fix Complete

## Current State

**Project:** Research Agent — Background Research Agents
**Phase:** REVIEW + FIX COMPLETE
**Branch:** `feat/background-research-agents`
**Date:** February 26, 2026

---

## What Was Done This Session

1. **Ran multi-agent code review** (`/workflows:review`) with 6 agents: security-sentinel, architecture-strategist, agent-native-reviewer, code-simplicity-reviewer, performance-oracle, learnings-researcher.
2. **Synthesized 10 findings** (2 P1, 5 P2, 3 P3) — created todo files for all.
3. **Fixed all 10 findings** in the same session:

### P1 Fixes (Critical)
- **#054 Shell injection**: Added single-quote escaping instruction before command construction
- **#055 Timestamp collision**: Replaced microsecond timestamps with batch index suffix (1, 2, 3)

### P2 Fixes (Important)
- **#056 Hardcoded path**: Removed `cd /Users/.../` — agents inherit working directory
- **#057 Path traversal**: Added path validation (must start with `reports/`, no `..`, must end `.md`) to both skills
- **#058 Stale recovery**: Replaced automatic re-queuing with user warning (prevents double-launches)
- **#059 Interactive digest**: Added auto-review mode (`/research:digest auto` skips prompt)
- **#060 Over-engineered JSON**: Flattened daily_spend.json to 3 fields (`date`, `budget`, `total_spent`), removed per-query tracking array

### P3 Fixes (Nice-to-Have)
- **#061 Budget validation**: Added positive-number validation with $5.00 default
- **#062 Error leakage**: Added error sanitization (truncate, strip API keys)
- **#063 Redundant sections**: Removed "How It Works" overview, report preview in notifications, Step 5 spend summary in digest, sub-agent conditional

### Commits

| Commit | Description |
|--------|-------------|
| `a550e6f` | docs: brainstorm + plan for background research agents |
| `52e32bf` | feat: add /research:queue and /research:digest skills |
| `f321431` | fix(review): address all review findings for background research skills |

## Three Questions

1. **Hardest judgment call in this review?** Whether shell injection (#054) warranted P1. In a single-user system the user "attacks themselves," but apostrophes are so common in English that normal queries would break — making it a functional bug, not just a theoretical security issue.

2. **What did you consider flagging but chose not to, and why?** Filename sanitization duplication between skill prose and `cli.py:sanitize_filename()`. Since the skill controls the `-o` flag and the CLI respects whatever path it receives, the duplication doesn't cause bugs today. Noted in architecture review but no todo created.

3. **What might this review have missed?** Skills are markdown instructions interpreted by Claude at runtime. We reviewed the *instructions* but couldn't test edge cases in Claude's *interpretation* — e.g., does Claude correctly parse queue sections when items are in unexpected order? Does it handle the Edit tool's exact-match requirement when moving items? Only real-world testing validates these.

## Next Phase

**COMPOUND** — Document learnings in `docs/solutions/`.

### Prompt for Next Session

```
Read HANDOFF.md. Run /workflows:compound for the background research agents feature. Key learnings: (1) skill-only features have no unit tests — review must be extra thorough on instruction clarity, (2) single-writer pattern eliminates concurrent write concerns but stale-detection needs care, (3) Claude has no real clock so timestamp-based uniqueness fails for parallel operations. Relevant files: .claude/skills/research-queue.md, .claude/skills/research-digest.md, todos/054-063.
```
