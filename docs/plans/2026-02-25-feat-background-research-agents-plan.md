---
title: "feat: Background Research Agents"
type: feat
status: active
date: 2026-02-25
origin: docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md
feed_forward:
  risk: "Whether Claude Code's run_in_background Task agents can reliably run the research agent CLI (1-3 min, many API calls)"
  verify_first: true
---

# feat: Background Research Agents

## Overview

Two Claude Code skills (`/research:queue` and `/research:digest`) that let you queue research queries in a markdown file, run them as background agents while you work, track daily spend, and review results on your schedule. No changes to the existing research agent Python code.

## Prior Phase Risk

> "Whether Claude Code's run_in_background Task agents can reliably run the research agent CLI (which itself makes many API calls over 1-3 minutes). If background agents have timeout or resource limits that conflict with research runs, the whole approach needs rethinking."

**Resolution:** Verified feasible. Background Task agents can run Bash commands with up to 10-minute timeouts (600,000ms). Standard queries take 1-3 minutes, deep queries up to 5 minutes — well within limits. The skill generates the output path upfront and passes it via `-o`, so report discovery doesn't depend on parsing stdout.

## Problem Statement

Research is synchronous today — you run one query, wait 1-3 minutes, then read the report. This blocks you from working, learning, or researching across projects simultaneously. Background research agents solve this by letting you queue queries that run while you do other things, with results delivered when each completes. (see brainstorm: `docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md`)

## Proposed Solution

### Architecture

```
User edits reports/queue.md (add queries)
        │
        ▼
/research:queue skill (reads queue, checks budget)
        │
        ├── Task agent 1 (run_in_background) ──► python3 main.py --standard "query1" -o reports/path1.md
        ├── Task agent 2 (run_in_background) ──► python3 main.py --quick "query2" -o reports/path2.md
        └── (holds remaining items for next invocation)
        │
        ▼
On each Task completion → main session notified
        │
        ├── Updates reports/queue.md (mark [x], add report path + cost)
        ├── Updates reports/meta/daily_spend.json (increment spend)
        └── Prints 2-3 line summary notification
        │
        ▼
/research:digest skill (reads unreviewed items, generates summary)
```

### Key Design Decision: Skill-Generated Output Paths

The skill generates the report output path *before* launching each background agent, using the same format as `cli.py:get_auto_save_path()`:

```
reports/{sanitized_query}_{YYYY-MM-DD}_{HHMMSS}{microseconds}.md
```

It passes this path via `-o <path>` to the CLI. This means:
- The skill knows exactly where each report will be saved — no stdout parsing needed
- All modes (including quick) save to disk — bypasses the `auto_save=False` issue
- Microsecond timestamps prevent collisions for parallel queries
- The path is recorded in the queue file *before* the agent starts

### Key Design Decision: Single Writer

The main Claude Code session is the **only writer** to `reports/queue.md` and `reports/meta/daily_spend.json`. Background Task agents only run the CLI and return results — they never touch the queue or spend files. When a background agent completes, the main session processes the notification and updates both files. This eliminates all concurrent write concerns.

## Technical Approach

### Component 1: Queue File (`reports/queue.md`)

A hand-editable markdown file. The user adds queries manually; the skill reads and updates it.

```markdown
# Research Queue

budget: $5.00

## Queued
- [ ] --standard "gap-aware retry patterns in LLM research agents"
- [ ] --quick "Python asyncio task queue libraries comparison"
- [ ] --deep "claim-level verification approaches in automated fact-checking"

## Running
- [~] --standard "gap-aware retry patterns..." → reports/gap_aware_retry_2026-02-25_143052123456.md

## Completed
- [x] --standard "source diversity in web search" → reports/source_diversity_2026-02-25_120301654321.md ($0.35)
- [x] --quick "asyncio queue libraries" → reports/asyncio_queue_2026-02-25_121505987654.md ($0.12) reviewed

## Failed
- [!] --deep "quantum computing applications" → insufficient_data ($0.85)
```

**State transitions:**
| State | Syntax | Meaning |
|-------|--------|---------|
| Queued | `- [ ]` | Waiting to be picked up |
| Running | `- [~]` | Background agent active |
| Completed | `- [x]` | Report saved, unreviewed |
| Reviewed | `- [x] ... reviewed` | User has read the report |
| Failed | `- [!]` | Query ran but failed |

**Parsing rules:**
- Lines starting with `- [ ]` in the `## Queued` section are pending queries
- Format: `- [ ] --{mode} "{query text}"`
- If mode is missing, default to `--standard`
- If quotes are missing, treat everything after `--mode ` as the query
- Skip blank lines and unrecognized formats with a warning
- Budget line: `budget: $X.XX` at the top (below the heading)
- FIFO order: top-to-bottom in the Queued section

### Component 2: Daily Spend Tracker (`reports/meta/daily_spend.json`)

**Schema:**
```json
{
  "date": "2026-02-25",
  "budget": 5.00,
  "total_spent": 0.47,
  "queries": [
    {
      "query": "source diversity in web search",
      "mode": "standard",
      "estimated_cost": 0.35,
      "status": "completed",
      "report_path": "reports/source_diversity_2026-02-25_120301654321.md",
      "timestamp": "2026-02-25T12:03:01"
    },
    {
      "query": "asyncio queue libraries",
      "mode": "quick",
      "estimated_cost": 0.12,
      "status": "completed",
      "report_path": "reports/asyncio_queue_2026-02-25_121505987654.md",
      "timestamp": "2026-02-25T12:15:05"
    }
  ]
}
```

**Rules:**
- `daily_spend.json` is the **single source of truth** for spend. The queue file's budget display is convenience only.
- **Date rollover:** When the skill reads the file and `date` is not today (local machine time), reset `total_spent` to `0.00` and clear the `queries` array. Write the reset file before proceeding.
- **Failed queries count against budget.** API calls are made even when the pipeline fails. Conservative approach prevents runaway spending.
- **Cost estimates:** quick=$0.12, standard=$0.35, deep=$0.85 (static, from `modes.py`). Actual cost tracking is a future enhancement.
- **File creation:** If the file doesn't exist, the skill creates it with `date: today`, `budget` from queue file, `total_spent: 0.00`, empty `queries`.

### Component 3: `/research:queue` Skill

Location: `.claude/skills/research-queue.md`

**Flow:**

```
1. Read reports/queue.md
   ├── File missing → create template, inform user, STOP
   └── File exists → parse queued items

2. Read reports/meta/daily_spend.json
   ├── File missing → create with budget from queue, spend=0
   ├── Date is stale → reset spend to 0
   └── Current → use as-is

3. Calculate available budget
   remaining = budget - total_spent

4. Select items to launch (FIFO, up to 3)
   For each item (top to bottom):
   ├── estimated_cost > remaining → skip, notify "budget reached"
   └── estimated_cost <= remaining → add to launch batch
       └── Deduct estimated_cost from remaining (pre-allocate)

5. For each item in launch batch:
   a. Generate output path: reports/{sanitized}_{timestamp}.md
   b. Update queue: move from Queued to Running, add output path
   c. Update daily_spend.json: add entry with status "running"
   d. Launch Task agent (run_in_background):
      - Bash: python3 main.py --{mode} "{query}" -o {output_path}
      - Timeout: 600000ms (10 min)
      - Agent returns: exit code, stdout snippet, whether file exists

6. Report what was launched, what was skipped (budget), what remains

7. On each Task completion notification:
   a. Read Task result (exit code, output)
   b. If success (exit 0, file exists):
      - Move from Running to Completed in queue
      - Update daily_spend.json status to "completed"
      - Print 2-3 line summary:
        "Research complete: {query} → {report_path} ({cost})"
        "{first 100 chars of report}"
   c. If failure (exit 1 or file missing):
      - Move from Running to Failed in queue with reason
      - Update daily_spend.json status to "failed"
      - Print: "Research failed: {query} — {error reason}"
```

**Skill metadata:**
```yaml
name: research-queue
description: Process background research queue
model: sonnet
tools: Read, Edit, Write, Bash, Task, Glob
argument-hint: (no arguments — reads reports/queue.md)
```

### Component 4: `/research:digest` Skill

Location: `.claude/skills/research-digest.md`

**Flow:**

```
1. Read reports/queue.md
   └── Find all Completed items WITHOUT "reviewed" marker

2. If no unreviewed items → "No unreviewed research. Queue is clear." STOP

3. For each unreviewed item (delegate to sub-agent to protect context):
   - Task agent reads the report file
   - Extracts: title, key findings (3-5 bullets), source count, status

4. Generate digest:
   "## Research Digest — {date}
   {N} queries completed since last review.

   ### 1. {query}
   Mode: {mode} | Sources: {N} | Cost: ${X.XX}
   - Finding 1
   - Finding 2
   - Finding 3
   Report: {path}

   ### 2. {query}
   ..."

5. Ask: "Mark all as reviewed?"
   └── Yes → Edit queue file, add "reviewed" to each item
   └── No → leave as-is

6. Display: "Total spend today: ${X.XX} / ${budget}"
```

**Skill metadata:**
```yaml
name: research-digest
description: Summarize unreviewed background research results
model: sonnet
tools: Read, Edit, Task, Glob
argument-hint: (no arguments — reads reports/queue.md)
```

### Implementation Phases

#### Phase 1: Foundation (Session 1, ~50 lines)

**Goal:** Queue file template + spend JSON + file structure.

**Tasks:**
1. Create `.claude/skills/` directory (project-level)
2. Create `reports/queue.md` with template structure (empty Queued/Completed/Failed sections, budget: $5.00)
3. Create `reports/meta/daily_spend.json` with initial schema (today's date, $0.00 spent)
4. Commit checkpoint

**Files:**
- `.claude/skills/` (new directory)
- `reports/queue.md` (new)
- `reports/meta/daily_spend.json` (new)

**Success criteria:** Both files exist and are valid.

#### Phase 2: Queue Skill (Session 2, ~100-150 lines)

**Goal:** The `/research:queue` skill that reads the queue, checks budget, launches background agents.

**Tasks:**
1. Write `.claude/skills/research-queue.md` — full skill instructions covering:
   - Queue file parsing (all state syntaxes)
   - Budget checking (read JSON, date rollover, remaining calculation)
   - Output path generation (match `cli.py:get_auto_save_path` format)
   - Background agent launching (Task with `run_in_background`, Bash with timeout)
   - Completion handling (update queue + spend on notification)
   - Error handling (missing files, malformed entries, failed queries)
2. Test with 1 quick-mode query to verify end-to-end flow
3. Commit checkpoint

**Files:**
- `.claude/skills/research-queue.md` (new)

**Success criteria:** Can add a query to `reports/queue.md`, run `/research:queue`, see it launch in background, get notification when done, queue file updated.

**Verify-first item:** Before writing the full skill, test a minimal background agent:
```
Task(run_in_background=true): "Run: python3 main.py --quick 'test query' -o reports/test_bg.md"
```
Confirm: agent completes, file is saved, notification arrives. If this fails, the approach needs rethinking.

#### Phase 3: Digest Skill (Session 3, ~60-80 lines)

**Goal:** The `/research:digest` skill that summarizes unreviewed research.

**Tasks:**
1. Write `.claude/skills/research-digest.md` — full skill instructions covering:
   - Queue parsing (find unreviewed completed items)
   - Report reading (delegate to sub-agent for context protection)
   - Digest generation (structured summary per query)
   - Review marking (edit queue file)
   - Spend display
2. Test with 2-3 completed queries from Phase 2 testing
3. Commit checkpoint

**Files:**
- `.claude/skills/research-digest.md` (new)

**Success criteria:** Running `/research:digest` generates a readable summary, offers to mark reviewed, updates queue file.

#### Phase 4: Real-World Test (Session 4)

**Goal:** Run 3-5 real queries across modes while doing other work.

**Tasks:**
1. Queue 3-5 queries related to upcoming Cycle 21 (iterative research loops)
2. Run `/research:queue`
3. Work on something else (code-explainer session, other project) while agents run
4. Process notifications as they arrive
5. Run `/research:digest` to review all results
6. Fix any issues found
7. Commit fixes if any

**Success criteria:** Full workflow works end-to-end. Reports are useful. Notifications arrive. Budget tracking is accurate.

## Alternative Approaches Considered

(from brainstorm: `docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md`)

1. **Python Queue Runner** — Standalone `--queue` CLI mode. Rejected: no in-session notifications, ADHD friction (results don't find you), more code to maintain.
2. **Hybrid** — Both skill + Python runner. Rejected: over-engineering for v1. Can add the runner later without changing the skill.
3. **Phase-triggered automation** — Rejected: too magical, hard to debug. Manual queue is predictable.
4. **Watchlist with TTL re-research** — Rejected: adds complexity before proving the basic queue works.

## System-Wide Impact

### Interaction Graph

`/research:queue` → reads `reports/queue.md` → reads `reports/meta/daily_spend.json` → launches Task agents → each Task runs `python3 main.py` (full research pipeline: search → fetch → extract → summarize → synthesize) → writes report to `reports/` → Task completion notifies main session → main session updates queue + spend files.

No callbacks, no middleware, no observers. Purely file-based state with skill orchestration.

### Error Propagation

- **Research agent failure** (exit code 1): Task agent captures exit code + stderr. Main session marks item as Failed in queue. Estimated cost still deducted from budget.
- **Task agent timeout** (>10 min): Task tool returns timeout error. Main session marks as Failed. Item stays in Running state until next `/research:queue` invocation cleans it up.
- **Queue file parse error**: Skill skips malformed lines with a warning. Valid lines still process.
- **Spend file corruption**: Skill recreates with today's date and $0 spent (safe default — may allow over-budget for the day, but won't block research).

### State Lifecycle Risks

- **Session closes mid-run**: Background Task agents die. Items stay in "Running" state in queue file. Next `/research:queue` invocation should detect stale Running items (no corresponding active Task) and move them back to Queued for retry.
- **Orphaned reports**: If a Task completes and writes a report but the session dies before updating the queue, the report exists on disk but isn't tracked. The skill should scan for untracked reports in `reports/` on startup (future enhancement, not v1).

### API Surface Parity

No existing interfaces need updating. These are net-new skills. The research agent CLI and programmatic API remain unchanged.

### Integration Test Scenarios

1. **Happy path**: Queue 2 standard queries → run skill → both complete → queue updated → digest shows both
2. **Budget limit**: Queue 3 standard queries with $0.50 budget → only 1 launches → notification says "budget reached for remaining 2"
3. **Mixed results**: Queue 1 valid + 1 nonsense query → one succeeds, one fails → both tracked correctly
4. **Session resumption**: Queue 3 items → run skill → close session after 1 completes → reopen → run skill → stale Running items re-queued → remaining items launch
5. **Date rollover**: Set spend to yesterday's date → run skill → spend resets to $0 → queries launch

## Acceptance Criteria

### Functional Requirements

- [ ] `reports/queue.md` template exists with documented syntax
- [ ] `reports/meta/daily_spend.json` schema is defined and initialized
- [ ] `/research:queue` reads queue, checks budget, launches up to 3 background agents
- [ ] Background agents run the research CLI with `-o` for forced output path
- [ ] On completion, queue file is updated (Queued → Running → Completed/Failed)
- [ ] On completion, spend JSON is updated with cost and status
- [ ] 2-3 line notification printed when each background agent completes
- [ ] Budget enforcement: queries skipped when remaining budget < estimated cost
- [ ] Failed queries marked with `[!]` and reason, cost deducted from budget
- [ ] `/research:digest` summarizes unreviewed completed items
- [ ] `/research:digest` offers to mark items as reviewed
- [ ] Date rollover resets daily spend automatically
- [ ] Queue items processed in FIFO order (top to bottom)
- [ ] Quick mode works in queue (forced `-o` bypasses `auto_save=False`)

### Non-Functional Requirements

- [ ] No changes to existing research agent Python code
- [ ] Skills work with `model: sonnet` (cost-efficient orchestration)
- [ ] Queue file remains human-readable and hand-editable
- [ ] Skill handles missing/empty/malformed queue files gracefully

### Quality Gates

- [ ] End-to-end test: queue 3 queries, all complete, digest works
- [ ] Budget test: verify queries stop when budget reached
- [ ] Failure test: verify failed queries are tracked correctly

## Success Metrics

- Background research runs while you work — no waiting
- Notifications arrive when queries complete — results find you
- Budget tracking prevents surprise costs
- Digest provides a single review point for batch results

## Dependencies & Prerequisites

- **Claude Code skills directory** — `.claude/skills/` must be created (doesn't exist yet)
- **Existing CLI** — `python3 main.py` must be working (currently at v0.18.0, 694 tests passing)
- **API keys** — `.env` with `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` must be configured
- **reports/ directory** — already exists with `meta/` subdirectory

## Risk Analysis & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Background Task timeout on deep queries | Query lost, needs retry | Low | 10-min timeout is generous; deep mode rarely exceeds 5 min |
| Session closes mid-run | Running items become stale | Medium | Skill detects stale Running items and re-queues on next invocation |
| Rate limits from parallel queries | API errors, failed queries | Low | Research agent has built-in backoff; limit to 2-3 concurrent |
| Queue file edited while skill runs | Parse errors or stale reads | Low | Single writer (main session); external edits only between invocations |
| Budget tracking inaccuracy (static estimates) | Over/under spend by ~20% | Medium | Acceptable for v1; actual cost tracking is a future enhancement |

## Future Considerations

- **Actual cost tracking** — Read `response.usage` from Anthropic API for real costs instead of estimates
- **Offline runner** — Approach B from brainstorm (Python queue runner) for research while Claude Code is closed
- **Watchlist mode** — Periodic re-research of topics with TTL-based staleness (builds on existing `staleness.py`)
- **Cross-project queues** — Single queue file serving multiple projects
- **Smart scheduling** — Queue queries based on compound engineering phase (auto-research for upcoming brainstorms)

## Documentation Plan

- Update `CLAUDE.md` with `/research:queue` and `/research:digest` usage under a new "Background Research" section
- Queue file format documented inline in `reports/queue.md` template (self-documenting)

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md](docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md) — Key decisions carried forward: manual queue (not automatic), per-query mode choice, daily budget cap, Claude Code background agents as execution model, notification + digest delivery.

### Internal References

- CLI entry point: `research_agent/cli.py:70-75` (auto-save path generation)
- Programmatic API: `research_agent/__init__.py` (`run_research`, `run_research_async`)
- Mode configs: `research_agent/modes.py` (cost estimates, auto_save flags)
- Atomic writes: `research_agent/safe_io.py` (reusable for spend file)
- Context result pattern: `research_agent/context_result.py` (model for queue loading states)
- Existing commands: `.claude/commands/review-batched.md`, `.claude/commands/fix-batched.md`

### Related Work

- Inspiration: Mitchell Hashimoto interview (Pragmatic Engineer) — "always have an agent running in the background"
- Research agent roadmap: `docs/research/master-recommendations-future-cycles.md` (Cycle 20+: "scheduled or triggered research")

## Feed-Forward

- **Hardest decision:** How to handle the quick-mode `auto_save=False` problem. Solved by having the skill always pass `-o <path>`, which forces all modes to save to disk without modifying Python code. This is clean but means the skill must generate filenames matching the CLI's format.
- **Rejected alternatives:** Having background agents update the queue file themselves (concurrent write risk), parsing CLI stdout for report paths (fragile), requiring only standard/deep modes in the queue (unnecessarily restrictive).
- **Least confident:** Stale Running item detection. When a session dies mid-run, items stuck in Running state need to be re-queued on next invocation. The skill has no way to check if a Task agent is still alive from a previous session — it can only detect that items are in Running with no active background tasks. This heuristic may be fragile.
