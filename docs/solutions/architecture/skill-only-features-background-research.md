---
title: "Skill-Only Features: Patterns from Background Research Agents"
date: 2026-02-26
category: architecture
tags:
  - skills
  - background-agents
  - single-writer
  - shell-escaping
  - timestamp-collision
  - path-traversal
  - compound-engineering
  - claude-code
module: .claude/skills/research-queue.md, .claude/skills/research-digest.md
symptoms: |
  10 findings from 6-agent review of background research agent skills.
  Key clusters: shell injection from apostrophes, timestamp collision in
  parallel paths, path traversal via hand-edited queue, stale state detection
  without a real clock.
severity: medium
summary: |
  Two Claude Code skills (/research:queue, /research:digest) enable background
  research while working. No Python code changes — pure skill orchestration of
  existing CLI. Review caught 10 issues (2 P1, 5 P2, 3 P3), all fixed in one
  commit. Documents 5 reusable patterns for skill-only features.
---

# Skill-Only Features: Patterns from Background Research Agents

### Prior Phase Risk

> "Skills are markdown instructions interpreted by Claude at runtime. We
> reviewed the *instructions* but couldn't test edge cases in Claude's
> *interpretation* — e.g., does Claude correctly parse queue sections when items
> are in unexpected order?"

Accepted risk: skill-only features have no unit test harness. Review was extra
thorough on instruction clarity and defensive rules. Real-world testing is the
only way to validate Claude's interpretation of skill prose.

## Risk Resolution

**Flagged:** Three risks tracked through the feed-forward chain:
1. Brainstorm: "Whether `run_in_background` Task agents can reliably run the CLI"
2. Plan: "Stale Running item detection is fragile" (feed_forward.risk)
3. Review: "Can't test Claude's interpretation of skill instructions"

**What actually happened:**
1. Background agents worked reliably — 10-minute timeout is generous for 1-3 minute queries. Risk resolved by testing in plan phase.
2. Stale detection was indeed fragile — review confirmed auto-recovery would cause double-launches. Fixed by replacing with user warning (#058). Risk resolved by simplifying.
3. Interpretation risk remains accepted — no mitigation exists for skill-only features beyond clear prose and defensive validation rules.

**Lesson:** The feed-forward chain caught 2 of 3 risks early enough to resolve them. The third (no test harness for skills) is a fundamental limitation of the medium, not a solvable problem.

## Context

Background research agents let you queue research queries that run as Claude
Code background Task agents while you work. Two skills orchestrate everything:
`/research:queue` reads a markdown queue file, checks a daily budget, and
launches up to 3 parallel agents; `/research:digest` summarizes completed
results for batch review. Zero Python code changes — the skills call the
existing `python3 main.py` CLI via Bash.

Built in 3 commits (+240 lines of skill instructions), reviewed by 6 agents
(10 findings per HANDOFF.md — review outputs were not committed separately,
only todo files), fixed in 1 commit.

## Pattern 1: Claude Has No Clock — Use Deterministic Identifiers

**Problem:** The skill generated output paths with microsecond timestamps for
uniqueness. But Claude generates all paths in a single message — it has no real
clock. Test data confirmed both parallel queries got identical timestamps.
Collision was avoided only because query slugs differed. (#055, P1)

**Fix:** Replaced timestamp microseconds with batch index (1, 2, 3) based on
launch order.

**Rule:** Don't rely on sub-second timestamp precision for uniqueness in
Claude-generated values. Claude produces all values in a single inference
pass — there's no time progression between them. Date and hour-level timestamps
are fine (Claude can read the system clock once), but microsecond or
millisecond suffixes will be identical across parallel items. Use a
deterministic counter (batch index, loop position) as the tiebreaker.

## Pattern 2: Shell Escaping is a Functional Bug, Not Just Security

**Problem:** The skill wrapped queries in single quotes for the Bash command.
Apostrophes — extremely common in English ("What's", "don't") — break
single-quote context. Not just a theoretical injection risk; normal queries
would fail. (#054, P1)

**Fix:** Added explicit escaping instruction: replace `'` with `'\''` before
constructing the command.

**Rule:** When a skill constructs shell commands with user-provided text,
always include escaping instructions. Single quotes need `'\''` escaping.
Apostrophes are the most common case — they appear in ~30% of natural English
queries. Treat this as a functional correctness issue, not just security.

## Pattern 3: Single Writer Eliminates Concurrency, But Stale Detection Needs Care

**Problem:** The plan correctly chose a single-writer pattern (main session
owns all file updates, background agents never touch queue/spend files). But
the plan also included auto-recovery for stale Running items — which would
double-launch active agents if the user ran `/research:queue` while background
agents were still running. (#058, P2)

**Fix:** Replaced auto-recovery with a user warning. Running items require
manual intervention to re-queue.

**Rule:** Single-writer is the right default for skill-orchestrated features.
But "detect and auto-recover stale state" is dangerous when you can't
distinguish dead processes from active ones. Prefer explicit user action over
heuristic recovery in v1. Add smarter detection later if it becomes friction.

## Pattern 4: Validate Paths from Hand-Edited Files

**Problem:** Both skills read report file paths from the queue file, which is
hand-editable. A malformed entry like `../../../.env` would cause the skill to
read arbitrary files. Single-user context limits impact, but violates least
privilege. (#057, P2)

**Fix:** Added path validation to both skills: must start with `reports/`, must
not contain `..`, must end with `.md`.

**Rule:** Any file path read from a user-editable source must be validated
before use, even in single-user tools. The validation is three checks:
1. Starts with the expected directory prefix
2. Contains no `..` segments
3. Ends with the expected extension

This takes 2-3 lines in skill instructions and prevents an entire class of
bugs.

## Pattern 5: Skill-Only Features Need Extra Review Rigor

**Problem:** Skills are markdown instructions — they have no unit tests, no
type checker, no linter. The only validation is reading the prose and
reasoning about how Claude will interpret it. This means bugs that would be
caught by tests in Python code (like the apostrophe issue) can ship undetected.

**Observation:** The review caught all 10 issues through careful reasoning
about edge cases. But it required 6 specialized agents to achieve coverage
that `pytest` gives automatically for Python code.

**Rule:** When reviewing skill-only features:
- **Security agent** catches shell/path issues that have no test safety net
- **Architecture agent** catches state management issues (like stale detection)
- **Simplicity agent** catches over-engineering (the plan's JSON schema was 4x
  more complex than needed)
- Test with real queries before shipping — it's the only integration test

## Positive Patterns (Confirmed by Review)

1. **Single-writer architecture** — Background agents are pure consumers; only
   the main session writes state files. Eliminates all concurrent write concerns.
2. **Forced output paths** — The skill generates `-o <path>` upfront, so it
   knows where reports will be before agents launch. No stdout parsing needed.
3. **Budget-first design** — Cost estimation before launch, not after. Failed
   queries still count against budget (conservative, prevents runaway spend).
4. **Additive integration** — Zero Python code changes. Skills orchestrate the
   existing CLI. The research agent doesn't know background mode exists.
5. **FIFO with cap** — Simple, predictable queue processing. Top-to-bottom,
   max 3 parallel, stop at budget. No priority system or scheduling complexity.

## Over-Engineering Caught in Review

The plan's `daily_spend.json` schema included a per-query tracking array with
7 fields each (query, mode, cost, status, path, timestamp, index). Review
(#060, P2) simplified to 3 fields: `date`, `budget`, `total_spent`. The
per-query history was duplicating information already in the queue file.

**Lesson:** For v1 features, fight the urge to build audit trails. The queue
file already tracks what ran and what it cost. The spend tracker only needs to
answer one question: "how much have I spent today?"

## Metrics

| Metric | Value |
|--------|-------|
| Review agents | 6 |
| Total findings | 10 |
| P1 Critical | 2 (shell injection, timestamp collision) |
| P2 Important | 5 (hardcoded path, path traversal, stale detection, interactive prompt, over-engineered JSON) |
| P3 Nice-to-have | 3 (budget validation, error leakage, redundant sections) |
| Fix commits | 1 (all findings in single commit) |
| Python code changed | 0 lines |
| Skill instructions changed | ~100 lines (net) |

## Three Questions

1. **Hardest pattern to extract from the fixes?** Pattern 1 (Claude has no
   clock). The timestamp collision was non-obvious because the path format
   *looks* correct — `{HHMMSS}_{batch_index}` — and works in most cases. The
   failure only manifests when two queries have similar enough names to
   truncate to the same 50-char slug. The root cause (Claude generates all
   values in one pass) is a property of the medium, not a code bug.

2. **What did I consider documenting but left out, and why?** The specific
   fix details for P3 items (budget validation defaults, error truncation
   length, which sections were removed). These are one-off cleanup items, not
   patterns. They're tracked in the todo files for reference.

3. **What might future sessions miss that this solution doesn't cover?** How
   Claude actually interprets the skill instructions at runtime. All review
   was static analysis of prose. We don't know if Claude reliably applies the
   single-quote escaping, correctly parses all queue states, or handles the
   Edit tool's exact-match requirement when moving items between sections.
   Only real-world usage across many queries will surface interpretation bugs.
