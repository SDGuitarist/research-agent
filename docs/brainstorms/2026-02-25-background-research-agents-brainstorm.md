# Background Research Agents

**Date:** 2026-02-25
**Status:** Brainstorm complete
**Origin:** Mitchell Hashimoto interview (Pragmatic Engineer) — "always have an agent running in the background"

## What We're Building

A way to queue research queries during Claude Code sessions that run in the background while you work, learn, or switch projects. Results are delivered as brief notifications when each query completes, with an optional digest for batch review.

### The Problem

Today, research is synchronous and single-shot: you run `python3 main.py --standard "query"`, wait 1-3 minutes, read the report. This means:

- Research only happens when you actively decide to do it
- You can't research while working on code, learning from code-explainer, or doing other project work
- Upcoming brainstorms start cold — no pre-gathered material
- Cross-project intelligence doesn't flow (working on gig-lead-responder doesn't feed research-agent roadmap)

### The Solution

A markdown **queue file** (`reports/queue.md`) + a Claude Code **skill** (`/research:queue`) that:

1. Reads queued queries from the file
2. Kicks off each as a background Task agent running the research agent CLI
3. Tracks spend against a configurable daily budget
4. Delivers a 2-3 line summary notification when each query completes
5. An optional `/research:digest` skill summarizes all completed queries for batch review

## Why This Approach

### Chosen: Queue File + Skill (Approach A)

- **Simplest build** — no new Python code in the research agent. The skill orchestrates existing CLI + Claude Code's `run_in_background` Task agents.
- **ADHD-friendly delivery** — notifications find you when queries complete, instead of reports sitting unread in a folder.
- **Queue is just a file** — edit it in any editor, review it between sessions, add queries while thinking about something else.
- **Builds on existing infra** — the research agent CLI, auto-save to `reports/`, and Claude Code background agents all exist today.

### Rejected: Python Queue Runner (Approach B)

- Runs independently of Claude Code, which sounds nice but breaks the notification model.
- Results don't "find you" — ADHD friction. You'd have to remember to check `reports/`.
- More code to build and maintain for a feature that may not get used if the in-session version works.

### Rejected: Hybrid (Approach C)

- Two systems to build and maintain for v1 is over-engineering.
- If in-session background research works well, the offline runner can be added later without changing anything (same queue file format, same CLI).

## Key Decisions

1. **Manual queue, not automatic triggers** — You add queries explicitly. No phase-triggered or watchlist automation. Keeps it predictable and under your control.
2. **Per-query mode choice** — Each query specifies its mode (quick/standard/deep) when added to the queue. More control over cost per query.
3. **Daily budget cap** — A configurable dollar amount per day (e.g. $5/day). The queue pauses when the budget is hit. Requires a small state file tracking today's spend.
4. **Notification + optional digest** — Each completed query triggers a brief summary notification in Claude Code. An optional `/research:digest` command generates a single summary of all completed queries for batch review.
5. **Claude Code background agents as execution model** — No standalone daemon or scheduler. Research runs inside Claude Code sessions via `run_in_background` Task agents. Limitation: only works when Claude Code is open.

## Queue File Format (Sketch)

Location: `reports/queue.md`

```markdown
# Research Queue

## Daily Budget: $5.00

## Queued
- [ ] --standard "gap-aware retry patterns in LLM research agents"
- [ ] --quick "Python asyncio task queue libraries comparison"
- [ ] --deep "claim-level verification approaches in automated fact-checking"

## Completed (2026-02-25)
- [x] --standard "gap-aware retry patterns..." → reports/2026-02-25-gap-aware-retry.md ($0.32)
- [x] --quick "Python asyncio task queue..." → reports/2026-02-25-asyncio-queues.md ($0.11) ✓reviewed

## Spent Today: $0.43
```

- Unchecked `[ ]` = queued
- Checked `[x]` = completed, unreviewed
- Checked `[x]` + `✓reviewed` = completed and reviewed
- Up to 2-3 queries run in parallel

## Use Case Scenarios

1. **Pre-brainstorm research** — Before starting Cycle 21 brainstorm, queue 3-4 queries about iterative research loops, gap detection patterns, retry strategies. Start a work session on something else. When you come back to brainstorm, reports are waiting.
2. **Learning companion** — During a code-explainer session on token budgeting, queue "token budgeting strategies in LLM pipelines" and "priority-based content pruning approaches". Deepens understanding beyond just your codebase.
3. **Cross-project feed** — While working on gig-lead-responder, queue research-agent queries about source diversity enforcement or Opus synthesis benchmarks. Next research-agent session starts informed.

## Constraints for Planning

1. **Concurrent queue file writes** — With 2-3 background agents finishing in parallel, each updating `reports/queue.md` (marking complete, updating spend), race conditions are possible. The research agent has `safe_io.py` for atomic writes, but concurrent read-then-write on the same file needs a strategy (file locking, single-writer design, or letting the skill — not the agents — own all queue file updates).
2. **Budget-hit behavior** — Decide during planning: when daily budget is reached mid-queue, does the skill notify you, silently stop, or hold remaining items for tomorrow?
3. **Report filename uniqueness** — Parallel queries finishing in the same second could collide on filenames. The CLI uses timestamps + query slugs, which is likely safe but should be verified.

## Resolved Questions

1. **Queue file location** — `reports/queue.md`. Next to the output reports — queue goes in, reports come out.
2. **Concurrency** — 2-3 queries in parallel. Faster throughput; will need to handle rate limits gracefully (the research agent already has backoff logic).
3. **Cross-session state** — Daily budget tracker persists as a JSON file (`reports/meta/daily_spend.json`). Small state file, acceptable tradeoff.
4. **Stale results** — Yes, completed items track a "reviewed" flag. The digest command only surfaces unreviewed items. Prevents re-reading and helps ADHD workflow (clear inbox model).

## Feed-Forward

- **Hardest decision:** Choosing Claude Code background agents over a standalone Python runner. The standalone runner is more capable (works offline, could schedule) but doesn't solve the ADHD delivery problem — results need to find you, not wait in a folder.
- **Rejected alternatives:** Phase-triggered automation (too magical, hard to debug), watchlist with TTL-based re-research (builds on staleness system but adds complexity before proving the basic queue works), hybrid approach (over-engineering for v1).
- **Least confident:** Whether Claude Code's `run_in_background` Task agents can reliably run the research agent CLI (which itself makes many API calls over 1-3 minutes). If background agents have timeout or resource limits that conflict with research runs, the whole approach needs rethinking. Should verify this first in planning.
