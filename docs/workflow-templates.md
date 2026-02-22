# Compound Engineering: Prompt Templates

Standard prompt templates for each phase of the research-agent compound engineering workflow. Use these as the starting point for every cycle. Each template includes the docs commit step to ensure no artifacts are left untracked.

---

## Phase 0: Brainstorm

```
/workflows:brainstorm

## Feature: [Feature Name]

## Summary
[1-2 sentences on what you want to build]

## Pre-research findings
[Paste any confirmed research answers from Claude Projects pre-brainstorm]

## Key questions for brainstorm to address
[List 2-3 open decisions the brainstorm should resolve]

## Scope fences (NOT in this session)
[Explicit list of what is out of scope]

## Stop condition
After saving the brainstorm doc to docs/brainstorms/, run:
git add docs/brainstorms/ && git commit -m "docs: add brainstorm doc for [feature name]" && git push
Then STOP. Do not begin planning. Do not write any code.
```

---

## Phase 1: Plan

```
/workflows:plan

## Feature: [Feature Name]

## Brainstorm doc
docs/brainstorms/[brainstorm-filename].md

## Summary of decisions
[Paste key decisions from brainstorm doc]

## Pre-research findings
[Paste any confirmed technical findings relevant to planning]

## Stop condition
After saving the plan doc to docs/plans/, run:
git add docs/plans/ && git commit -m "docs: add plan doc for [feature name]" && git push
Then STOP. Do not begin work. Do not write any code.
```

---

## Phase 2: Work (per session)

```
/workflows:work [plan doc path]

## Scope for this run
Complete Steps [X] and [Y] only:

**Step X — [Step name]**
[What to do, which files, specific instructions]

**Step Y — [Step name]**
[What to do, which files, specific instructions]

## Relevant files
- research_agent/agent.py (orchestrator — read if changing pipeline flow)
- research_agent/[module].py (the module you're changing)
- research_agent/modes.py (frozen dataclass configs — read if adding parameters)
- research_agent/errors.py (exception hierarchy — read if adding error handling)

## Stop condition
After [X] commits are made and `python3 -m pytest tests/ -v` passes, run: git push
Then STOP. Do not continue to Steps [Z+]. Do not begin review.
```

---

## Phase 3: Review — Batch 1 (Code Quality)

```
/review-batched batch1

Agents: kieran-python-reviewer, pattern-recognition-specialist, code-simplicity-reviewer

## Stop condition
After todos are saved, STOP. Do not begin batch2.
```

## Phase 3: Review — Batch 2 (Architecture & Security)

```
/review-batched batch2

Agents: architecture-strategist, security-sentinel, performance-oracle

## Stop condition
After todos are saved, STOP. Do not begin batch3.
```

## Phase 3: Review — Batch 3 (Data & History)

```
/review-batched batch3

Agents: data-integrity-guardian, git-history-analyzer, agent-native-reviewer

## Stop condition
After todos are saved, STOP. Do not begin synthesize.
```

## Phase 3: Review — Synthesis

```
/review-batched synthesize

Deduplicate all findings from batch1, batch2, batch3 into a consolidated
report with P1/P2/P3 priorities.

## Stop condition
After saving the consolidated report to docs/reviews/, run:
git add docs/reviews/ && git commit -m "docs: add review artifacts for [branch name]" && git push
Then STOP.
```

---

## Phase 3: Fix Session (per batch of fixes)

```
/workflows:work docs/reviews/[branch-name]/REVIEW-SUMMARY.md

## Scope for this run
Fix #[X] and #[Y] only.

**Fix #X — [Finding name]**
File: [filename:line]
[Specific fix instructions]

**Fix #Y — [Finding name]**
File: [filename:line]
[Specific fix instructions]

## After completing both fixes
Answer these three questions before closing the session:
1. What was the hardest decision you made here?
2. What alternatives did you reject, and why?
3. What are you least confident about?

## Before starting the next fix session
Read the three answers above carefully. Ask:
- Does the "hardest decision" reveal a pattern worth applying to the next fixes?
- Does the "least confident" answer identify a risk the next session should guard against?
- Update the next fix session's scope or instructions based on what you learned.

Only then write the next fix session prompt.

## Stop condition
After 1 commit and the three questions are answered, run: git push
Then STOP. Do not continue to the next fix session.
```

---

## Phase 4: Compound

```
/workflows:compound

## Session to document
[branch name] — [Feature Name]

## What was built
[2-3 sentence summary]

## Key fixes applied (post-review)
[Bullet list of fixes]

## Patterns worth capturing
[Bullet list of reusable patterns or gotchas discovered this cycle]

## Stop condition
After saving the compound doc to docs/solutions/, run:
git add docs/solutions/ docs/brainstorms/ docs/plans/ docs/reviews/
git status
git commit -m "docs: add all cycle artifacts for [feature name]" && git push
Then STOP.
```

---

## PR and Merge

```
## Step 1 — Open the PR
gh pr create \
  --title "[feat/fix]: [short description]" \
  --body "[What this does, review summary, commit count]" \
  --base main

## Step 2 — Merge
gh pr merge --squash --delete-branch
```

---

## Quick Reference: Fix Order Principles

When triaging review findings, order fixes by:

1. **1-line correctness bugs first** — highest impact, lowest risk
2. **Security and prompt injection defense** — sanitization, SSRF protection
3. **Performance and async patterns** — token budgets, batching, timeouts
4. **Code quality and abstractions** — DRY, type hints, dead code removal
5. **New features surfaced by review** — always a separate PR
