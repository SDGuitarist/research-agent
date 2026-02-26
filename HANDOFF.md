# Handoff: Background Research Agents — Brainstorm

## Current State

**Project:** Research Agent — Background Research Agents
**Phase:** BRAINSTORM COMPLETE
**Branch:** `main`
**Date:** February 25, 2026

---

## What Was Done This Session

1. **Brainstormed** background research agents feature — inspired by Mitchell Hashimoto's "always have an agent running" approach.
2. **Explored** three approaches: Queue File + Skill (chosen), Python Queue Runner (rejected — ADHD friction), Hybrid (rejected — over-engineering for v1).
3. **Resolved** all open questions: queue at `reports/queue.md`, 2-3 parallel queries, daily budget with JSON state file, reviewed flag on completed items.
4. **Document-reviewed** the brainstorm — fixed naming inconsistency, surfaced concurrent write race condition as critical planning constraint.
5. **Captured** brainstorm at `docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md`.

## Feed-Forward

- **Hardest decision:** Choosing Claude Code background agents over a standalone Python runner. The standalone runner is more capable but doesn't solve the ADHD delivery problem.
- **Rejected alternatives:** Phase-triggered automation, watchlist with TTL re-research, hybrid approach.
- **Least confident:** Whether Claude Code's `run_in_background` Task agents can reliably run the research agent CLI (which makes many API calls over 1-3 minutes). If background agents have timeout or resource limits, the approach needs rethinking. Verify this first in planning.

## Next Phase

**PLAN** — Design the implementation for the queue file + skill approach. Must address the concurrent queue file write constraint and verify background agent feasibility.

### Prompt for Next Session

```
Read docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md. Run /workflows:plan to design the implementation for background research agents. Key constraint: concurrent queue file writes when parallel agents finish. Verify first: can run_in_background Task agents reliably execute the research agent CLI? Relevant files: research_agent/cli.py, research_agent/agent.py, research_agent/modes.py, research_agent/safe_io.py.
```
