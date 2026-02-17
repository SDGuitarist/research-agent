---
name: review-batched
description: Context-safe batched code review — runs 3 agents at a time, saves findings to files, resumes across sessions
argument-hint: "[batch1|batch2|batch3|synthesize] [PR number, branch, or latest]"
---

# Batched Code Review

<command_purpose>Run code review agents in small batches (3 at a time) to stay within context limits. Each batch writes findings to files so you can resume in a fresh window.</command_purpose>

## Introduction

<role>Senior Code Review Architect running a context-safe, batched review pipeline</role>

This skill replaces `/workflows:review` when context window limits are a concern. Instead of launching 13+ agents simultaneously (which floods the context), it runs **3 agents per batch** and persists all findings to disk.

## How It Works

```
Session 1:  /review-batched batch1 latest    → runs 3 agents, saves to docs/reviews/<branch>/
Session 2:  /review-batched batch2            → runs 3 more agents, appends findings
Session 3:  /review-batched batch3            → runs 3 more agents, appends findings
Session 4:  /review-batched synthesize        → reads all findings, produces P1/P2/P3 summary
```

## Arguments

<review_target> #$ARGUMENTS </review_target>

Parse the arguments:
- **First word** = batch identifier: `batch1`, `batch2`, `batch3`, or `synthesize`
- **Remaining words** = PR target (number, branch name, `latest`, or empty for current branch)
- If no batch specified, default to `batch1`
- If no target specified, use current branch

## Step 1: Setup (Every Batch)

<task_list>

- [ ] Determine review target (PR number, branch, or current branch)
- [ ] If this is `batch1`: fetch PR metadata with `gh pr view --json title,body,files,headRefName` and save to `docs/reviews/<branch>/pr-metadata.md`
- [ ] If this is NOT `batch1`: read `docs/reviews/<branch>/pr-metadata.md` to restore context
- [ ] Ensure we are on the correct branch (`gh pr checkout` or `git checkout`)
- [ ] Create output directory: `docs/reviews/<branch>/`
- [ ] Get the diff: `git diff main...HEAD` (or appropriate base branch)

</task_list>

## Step 2: Run the Batch

### Batch Definitions

**batch1 — Code Quality (3 agents)**

<parallel_tasks>

Run these 3 agents at the same time:

1. Task kieran-python-reviewer(PR diff + metadata) — Python code quality, naming, Pythonic patterns
2. Task pattern-recognition-specialist(PR diff + metadata) — Code patterns, anti-patterns, duplication
3. Task code-simplicity-reviewer(PR diff + metadata) — YAGNI, unnecessary complexity, simplification

</parallel_tasks>

After all 3 complete, write each agent's findings to:
- `docs/reviews/<branch>/batch1-kieran-python.md`
- `docs/reviews/<branch>/batch1-pattern-recognition.md`
- `docs/reviews/<branch>/batch1-code-simplicity.md`

**batch2 — Architecture & Security (3 agents)**

<parallel_tasks>

Run these 3 agents at the same time:

1. Task architecture-strategist(PR diff + metadata) — System design, component boundaries, architectural compliance
2. Task security-sentinel(PR diff + metadata) — OWASP, injection, secrets, input validation
3. Task performance-oracle(PR diff + metadata) — Bottlenecks, scaling, memory, algorithmic complexity

</parallel_tasks>

After all 3 complete, write each agent's findings to:
- `docs/reviews/<branch>/batch2-architecture.md`
- `docs/reviews/<branch>/batch2-security.md`
- `docs/reviews/<branch>/batch2-performance.md`

**batch3 — Data, History & Agent-Native (3 agents)**

<parallel_tasks>

Run these 3 agents at the same time:

1. Task data-integrity-guardian(PR diff + metadata) — Data consistency, transaction boundaries, referential integrity
2. Task git-history-analyzer(PR diff + metadata) — Historical context, evolution patterns, contributor expertise
3. Task agent-native-reviewer(PR diff + metadata) — Can agents do everything users can?

</parallel_tasks>

After all 3 complete, write each agent's findings to:
- `docs/reviews/<branch>/batch3-data-integrity.md`
- `docs/reviews/<branch>/batch3-git-history.md`
- `docs/reviews/<branch>/batch3-agent-native.md`

### Writing Findings Files

Each findings file MUST follow this format:

```markdown
# [Agent Name] — Review Findings

**PR:** [title]
**Branch:** [branch name]
**Date:** [today]
**Agent:** [agent name]

## Findings

### [Finding Title]
- **Severity:** P1 / P2 / P3
- **File:** [file path]:[line number]
- **Issue:** [description]
- **Suggestion:** [what to do]

### [Next Finding]
...

## Summary
- P1 (Critical): [count]
- P2 (Important): [count]
- P3 (Nice-to-have): [count]
```

## Step 3: Report Batch Status

After writing findings files, print:

```markdown
## Batch [N] Complete

**Findings saved to:** docs/reviews/<branch>/

| Agent | P1 | P2 | P3 |
|-------|----|----|-----|
| [agent 1] | X | X | X |
| [agent 2] | X | X | X |
| [agent 3] | X | X | X |

### Batches Remaining:
- [ ] batch1 — Code Quality (kieran-python, pattern-recognition, code-simplicity)
- [ ] batch2 — Architecture & Security (architecture, security, performance)
- [ ] batch3 — Data & History (data-integrity, git-history, agent-native)
- [ ] synthesize — Read all findings, produce final report

**Next step:** Start a fresh conversation and run:
`/review-batched [next-batch]`
```

Mark completed batches with [x] by checking which files exist in `docs/reviews/<branch>/`.

## Step 4: Synthesize (Final Batch)

When the argument is `synthesize`:

<task_list>

- [ ] Read ALL findings files from `docs/reviews/<branch>/batch*.md`
- [ ] Read PR metadata from `docs/reviews/<branch>/pr-metadata.md`
- [ ] Deduplicate findings that overlap across agents
- [ ] Categorize all findings by severity: P1 (critical), P2 (important), P3 (nice-to-have)
- [ ] Write final report to `docs/reviews/<branch>/REVIEW-SUMMARY.md`
- [ ] Create todo files in `todos/` using the file-todos convention (if todos/ dir exists)
- [ ] Present the summary to the user

</task_list>

### Final Report Format

Write `docs/reviews/<branch>/REVIEW-SUMMARY.md`:

```markdown
# Code Review Summary

**PR:** [title]
**Branch:** [branch name]
**Date:** [today]
**Agents Used:** [list all 9]

## P1 — Critical (Blocks Merge)

### [Finding Title]
- **Source Agent:** [which agent found this]
- **File:** [path]:[line]
- **Issue:** [description]
- **Fix:** [suggestion]

## P2 — Important (Should Fix)

### [Finding Title]
...

## P3 — Nice-to-Have

### [Finding Title]
...

## Statistics

| Severity | Count |
|----------|-------|
| P1 Critical | X |
| P2 Important | X |
| P3 Nice-to-have | X |
| **Total** | **X** |

## Agents & Batches

| Batch | Agents | Findings |
|-------|--------|----------|
| batch1 | kieran-python, pattern-recognition, code-simplicity | X |
| batch2 | architecture, security, performance | X |
| batch3 | data-integrity, git-history, agent-native | X |
```

## Important Rules

1. **Never run more than 3 agents per batch** — this is the whole point of this skill
2. **Always write findings to files before finishing** — files are the handoff mechanism
3. **Do NOT attempt synthesis in the same session as a batch** — save context for the next session
4. **Skip irrelevant agents** — if an agent returns no findings, write a file noting "No findings"
5. **Each session = one batch** — print the "next step" instructions and stop

## Quick Reference

```
/review-batched batch1 latest     # First: code quality
/review-batched batch2            # Second: architecture & security
/review-batched batch3            # Third: data & history
/review-batched synthesize        # Final: read all, produce report
```
