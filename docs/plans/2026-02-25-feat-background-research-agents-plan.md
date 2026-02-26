---
title: "feat: Background Research Agents"
type: feat
status: active
date: 2026-02-25
deepened: 2026-02-26
origin: docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md
feed_forward:
  risk: "Whether Claude Code's run_in_background Task agents can reliably run the research agent CLI (1-3 min, many API calls)"
  verify_first: true
---

# feat: Background Research Agents

## Enhancement Summary

**Deepened on:** 2026-02-26
**Agents used:** 10 (7 review + 3 research)
**Sections enhanced:** All major sections

### Key Improvements from Deepening

1. **Eliminate the Running state** — Items stay Queued until completion. Removes the plan's own identified weakest point (stale detection) and simplifies from 5 states to 3.
2. **Fix output path format** — `_{batch_index}` must be zero-padded to 6 digits (`_000001`) to match `cli.py`'s `--list` regex `\d{6,}`. Without this, background reports are invisible to `--list`.
3. **Add mode validation** — The skill must validate `--{mode}` is one of quick/standard/deep before constructing the Bash command. Without this, a hand-edited queue entry could inject arbitrary CLI flags.
4. **Reduce concurrency from 3 to 2** — Three parallel queries generate 45-135 Anthropic API calls/minute, pushing past typical Tier 1 rate limits (50 req/min). Two keeps throughput high with minimal 429 risk.
5. **Background notification reliability warning** — GitHub issues document that `run_in_background` Task completion notifications are not 100% reliable (Issue #21048). Plan must include a fallback detection strategy.
6. **Delegate report reading in digest to sub-agents** — Loading 5 deep reports (17,500 words) directly into the main session consumes significant context. Use Task agents that return only the 3-5 key findings.
7. **Align plan JSON schema with implemented skill** — The skill already uses 3 fields (`date`, `budget`, `total_spent`). The plan's 7-field `queries` array was already simplified by prior review but the plan text was stale.
8. **Add correlation key** — Use the output path (unique per item) to match Task completions back to queue entries. Makes the system resilient to manual text edits on running items.
9. **Budget sync contract** — Read budget from `queue.md` on every invocation, read spend from `daily_spend.json`. This makes the queue file the source of truth for budget configuration.
10. **Include failed items in digest** — Without this, users may not realize queries failed unless they manually check the queue file.

### New Risks Discovered

| Risk | Source | Severity | Mitigation |
|------|--------|----------|------------|
| Background notifications unreliable | Skills research (Issue #21048) | Medium | Pull-based fallback: check result files if notification doesn't arrive |
| Mode injection via queue file | Security review | High | Mode allowlist validation before Bash command construction |
| Output paths invisible to `--list` | Architecture + Agent-native reviews | Medium | Zero-pad batch index to 6 digits |
| API rate limit amplification | Performance review | Medium | Reduce concurrency to 2, add retry jitter |
| Edit tool fragility with hand-edits | Architecture review | Medium | Re-read queue file before retrying failed edits |
| Queue file grows unboundedly | Architecture review | Medium | Archive completed items after 20 entries |

---

## Overview

Two Claude Code skills (`/research:queue` and `/research:digest`) that let you queue research queries in a markdown file, run them as background agents while you work, track daily spend, and review results on your schedule. No changes to the existing research agent Python code.

## Prior Phase Risk

> "Whether Claude Code's run_in_background Task agents can reliably run the research agent CLI (which itself makes many API calls over 1-3 minutes). If background agents have timeout or resource limits that conflict with research runs, the whole approach needs rethinking."

**Resolution:** Verified feasible. Background Task agents can run Bash commands with up to 10-minute timeouts (600,000ms). Standard queries take 1-3 minutes, deep queries up to 5 minutes — well within limits. The skill generates the output path upfront and passes it via `-o`, so report discovery doesn't depend on parsing stdout.

### Research Insight: Background Agent Reliability

Multiple GitHub issues document limitations with `run_in_background` Task agents:
- **Completion notifications not 100% reliable** (Issue #21048): Notifications may not reliably appear or activate Claude from idle state.
- **Long-running background tasks can crash terminal** (Issue #24004): Tasks over ~5 minutes may cause "Nesting..." state.
- **The 2-minute default timeout** (Issue #3505): Must explicitly set `timeout: 600000` on Bash commands.

**Mitigation for v1:** The skill should not depend solely on push notifications. After launching agents, include a pull-based fallback: if no notification arrives within 5 minutes, check the output file paths directly (`ls reports/{expected_path}`). If the file exists, process it as a completion.

**Alternative considered but deferred:** `context: fork` for synchronous processing. This is more reliable but defeats the "work while research runs" goal. Keep background agents for v1 but design the skill to tolerate missed notifications.

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
        ├── Updates reports/queue.md (move from Queued → Completed/Failed)
        ├── Updates reports/meta/daily_spend.json (increment spend)
        └── Prints 2-3 line summary notification
        │
        ▼
/research:digest skill (reads completed items, generates summary)
```

### Key Design Decision: Skill-Generated Output Paths

The skill generates the report output path *before* launching each background agent, using a format compatible with `cli.py:get_auto_save_path()`:

```
reports/{sanitized_query}_{YYYY-MM-DD}_{HHMMSS}_{batch_index:06d}.md
```

**The batch index MUST be zero-padded to 6 digits** (e.g., `_000001`, `_000002`). The `--list` command's regex at `cli.py:82` expects `\d{6,}` after the time component. Without 6-digit padding, background reports are silently invisible to `python3 main.py --list`.

It passes this path via `-o <path>` to the CLI. This means:
- The skill knows exactly where each report will be saved — no stdout parsing needed
- All modes (including quick) save to disk — bypasses the `auto_save=False` issue
- The output path serves as the **correlation key** for matching Task completions back to queue entries
- The path is recorded in the queue file *before* the agent starts

### Research Insight: Why Not Microsecond Timestamps

The prior review (Pattern 1 in `docs/solutions/architecture/skill-only-features-background-research.md`) discovered that Claude generates all paths in a single inference pass — there is no time progression between them. Microsecond timestamps for parallel items would be identical. The batch index is deterministic and collision-proof.

### Key Design Decision: Single Writer

The main Claude Code session is the **only writer** to `reports/queue.md` and `reports/meta/daily_spend.json`. Background Task agents only run the CLI and return results — they never touch the queue or spend files. When a background agent completes, the main session processes the notification and updates both files. This eliminates all concurrent write concerns.

### Research Insight: Edit Tool Fragility

The Edit tool requires exact string matching. Since the queue file is hand-editable, users may introduce trailing whitespace, smart quotes, or extra spaces that break Edit matches. **Defensive pattern:** If an Edit fails to match, re-read the queue file with the Read tool, find the actual line text, and retry with the exact text as it appears in the file.

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

## Completed
- [x] --standard "source diversity in web search" → reports/source_diversity_2026-02-25_120301_000001.md ($0.35)
- [x] --quick "asyncio queue libraries" → reports/asyncio_queue_2026-02-25_121505_000001.md ($0.12)

## Failed
- [!] --deep "quantum computing applications" → insufficient_data ($0.85)
```

**State transitions (simplified — 3 states, not 5):**
| State | Syntax | Section | Meaning |
|-------|--------|---------|---------|
| Queued | `- [ ]` | `## Queued` | Waiting to be picked up |
| Completed | `- [x]` | `## Completed` | Report saved |
| Failed | `- [!]` | `## Failed` | Query ran but failed |

### Research Insight: Eliminate the Running State

The simplicity review identified the Running state (`[~]` / `## Running`) as the source of the plan's weakest point — stale detection. Items stay in `## Queued` until the skill moves them directly to `## Completed` or `## Failed` on Task completion. If the session dies mid-run, items remain Queued and get picked up on next invocation. No stale detection, no orphan recovery, no manual intervention needed.

The skill tracks which items it launched in the current invocation via their output paths (in-memory only). This is sufficient to match completions to queue entries.

### Research Insight: Drop the "Reviewed" Marker for v1

The digest shows all completed items. After review, offer to clear the `## Completed` section (move to `## Archive` at bottom of file, or delete). This is simpler than per-line marker management. The `reviewed` text suffix was a fifth state that added parsing complexity for a single consumer.

**Parsing rules:**
- Lines starting with `- [ ]` in the `## Queued` section are pending queries
- Format: `- [ ] --{mode} "{query text}"`
- **Mode validation:** Must be exactly `quick`, `standard`, or `deep`. Skip entries with invalid modes and warn: "Skipping entry with invalid mode '{mode}' — use --quick, --standard, or --deep"
- If quotes are missing, treat everything after `--mode ` as the query
- Skip blank lines and unrecognized formats with a warning showing which line was skipped
- **State/section mismatch:** If a line's checkbox doesn't match its section (e.g., `[x]` in `## Queued`), skip with warning
- **Parse sections by name, not position** — users may reorder sections. Match `## Queued`, `## Completed`, `## Failed` by header text (case-insensitive)
- Budget line: `budget: $X.XX` at the top (first match only). Must be between $0.01 and $50.00. If missing, malformed, or out of range: warn and STOP (do not silently default)
- FIFO order: top-to-bottom in the Queued section

### Research Insight: Normalize on Read

Hand-edited files may contain encoding issues. Before parsing, normalize:
- Strip UTF-8 BOM (`\ufeff`)
- Normalize line endings (`\r\n` → `\n`)
- Normalize smart quotes (`\u201c` and `\u201d` → `"`)
- Trim trailing whitespace per line

This follows the "strict on write, lenient on read" pattern from the todo.txt ecosystem.

### Queue File as Programmatic API

Other skills or agents may want to add items to the queue programmatically. Document the contract:

```markdown
<!-- Queue API (for other skills/agents):
  To add items: append `- [ ] --{mode} "{query}"` to the ## Queued section.
  To check status: read ## Completed and ## Failed sections.
  Budget file: reports/meta/daily_spend.json
  Valid modes: quick, standard, deep -->
```

This comment block goes in the queue template. Consider a future `/research:add` skill that takes `--mode "query"` as an argument for even simpler programmatic access.

### Component 2: Daily Spend Tracker (`reports/meta/daily_spend.json`)

**Schema (simplified — 3 fields only):**
```json
{
  "date": "2026-02-25",
  "budget": 5.00,
  "total_spent": 0.47
}
```

### Research Insight: No Per-Query Array

The prior review already simplified this from a 7-field per-query array. The queue file tracks which queries ran, their mode, report path, and cost. The spend tracker only needs to answer one question: "how much have I spent today?"

**Rules:**
- **Budget source:** The skill reads the budget from `reports/queue.md` on every invocation and updates `daily_spend.json` to match. This makes the queue file the source of truth for budget configuration and the JSON the source of truth for spend tracking.
- **Date rollover:** When the skill reads the file and `date` is not today (local machine time), reset `total_spent` to `0.00` and update `budget` from the queue file. Write the reset file before proceeding.
- **Failed queries count against budget.** API calls are made even when the pipeline fails. Conservative approach prevents runaway spending.
- **Cost estimates:** quick=$0.12, standard=$0.35, deep=$0.85 (static, from `modes.py`). Actual cost tracking is a future enhancement.
- **File creation:** If the file doesn't exist or is corrupted, the skill creates it with `date: today`, `budget` from queue file, `total_spent: 0.00`.
- **Corruption note:** If the spend file is corrupted and reset, previously tracked spend for today is lost. This may allow up to one extra daily budget of spend. Acceptable for v1.

### Research Insight: JSON Schema Validation

Validate after reading:
- `date` must match `YYYY-MM-DD` format
- `budget` must be a positive number (> 0)
- `total_spent` must be a non-negative number (>= 0)
- If any field fails, treat as corrupt and recreate

### Research Insight: Budget Safety Margin

Reserve 15% of daily budget as headroom for estimation error. If budget is $5.00, treat $4.25 as the effective budget. This absorbs the 10-30% variance between estimated and actual costs without blocking the user unexpectedly.

### Component 3: `/research:queue` Skill

Location: `.claude/skills/research-queue.md`

**Flow:**

```
1. Read reports/queue.md
   ├── File missing → create template (with API comment block), inform user
   │   with: file path, syntax example, "run /research:queue again after adding items." STOP
   └── File exists → parse queued items (normalize on read first)

2. Read reports/meta/daily_spend.json
   ├── File missing or corrupt → create with budget from queue, spend=0
   ├── Date is stale → reset spend to 0, sync budget from queue file
   └── Current → use as-is, sync budget from queue file if different

3. Calculate available budget
   effective_budget = budget * 0.85  (15% safety margin)
   remaining = effective_budget - total_spent

4. Select items to launch (FIFO, up to 2)
   For each item (top to bottom):
   ├── Validate mode is quick/standard/deep — skip invalid with warning
   ├── estimated_cost > remaining → skip, notify "budget reached" with:
   │   how much remains, how much more is needed, that budget resets tomorrow
   └── estimated_cost <= remaining → add to launch batch
       └── Deduct estimated_cost from remaining (pre-allocate)

5. For each item in launch batch:
   a. Generate output path: reports/{sanitized}_{YYYY-MM-DD}_{HHMMSS}_{index:06d}.md
   b. Update daily_spend.json: add estimated cost to total_spent
   c. Launch Task agent (run_in_background):
      - Escape single quotes in query: replace ' with '\''
      - Bash: python3 main.py --{validated_mode} '{escaped_query}' -o {output_path}
      - Timeout: 600000ms (10 min)
      - Agent returns: exit code, whether file exists, error message if failed
   d. Record output_path as correlation key (in-memory) for this invocation

6. Report launch status:
   "Launched N background research queries:
    1. [mode] "query" → path ($cost)
    2. [mode] "query" → path ($cost)
    Budget: $X.XX / $Y.YY spent today. N items remaining in queue.
    Note: background agents will stop if this session closes."

7. On each Task completion notification:
   a. Match completion to queue item by output path (correlation key)
   b. If Edit tool fails to match the queue line, re-read queue file and retry
   c. If success (exit 0, file exists):
      - Move item from ## Queued to ## Completed:
        - [x] --mode "query" → reports/path.md ($cost)
      - Print: "Research complete: "query" → reports/path.md ($cost)"
   d. If failure (exit 1 or file missing):
      - Move item from ## Queued to ## Failed:
        - [!] --mode "query" → {error reason, truncated to 100 chars} ($cost)
      - Print: "Research failed: "query" — {error reason} ($cost still counted)"
```

**Skill metadata:**
```yaml
name: research-queue
description: Process background research queue — launches queries as background agents while you work. Use when asked to "queue research", "run background research", or "process the queue".
model: sonnet
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Bash, Task, Glob
argument-hint: (no arguments — reads reports/queue.md)
```

### Research Insight: Concurrency Limit

| Concurrent | Peak API calls/min | 429 risk | Throughput |
|------------|-------------------|----------|------------|
| 1 | 15-45 | Low | Baseline |
| **2** | **30-90** | **Medium** | **~2x** |
| 3 | 45-135 | High | ~2.5x (contention) |

**Default to 2 concurrent.** Three parallel standard queries could generate 45-135 Anthropic API calls competing in a 1-3 minute window. At 2 concurrent, you get close to 2x throughput with minimal 429 interference. Users on Anthropic Tier 2+ (higher rate limits) can increase to 3 by editing the skill.

### Research Insight: Staggered Launches

Launch the first Task agent immediately. Wait 15-20 seconds before launching the second. This spreads the API-heavy summarize and scoring bursts across time, reducing peak concurrent calls from ~10 to ~5-8.

### Component 4: `/research:digest` Skill

Location: `.claude/skills/research-digest.md`

**Flow:**

```
1. Read reports/queue.md
   ├── File missing → "No research queue found. Run /research:queue first." STOP
   └── File exists → parse Completed and Failed sections

2. If no completed items → "No completed research to review. Queue is clear." STOP

3. For each completed item (delegate to Task sub-agent to protect context):
   a. Validate report path: starts with reports/, no .., ends with .md
   b. Task agent reads the report file and returns ONLY:
      - Title, key findings (3-5 bullets), source count
   c. This keeps full report content out of the main session's context

4. If there are failed items, include a failures summary:
   "N queries failed:
    - "query" — error reason ($cost)
    - ..."

5. Generate digest:
   "## Research Digest — {date}
   {N} queries completed, {M} failed since last review.

   ### 1. {query}
   Mode: {mode} | Sources: {N} | Cost: ${X.XX}
   - Finding 1
   - Finding 2
   - Finding 3
   Report: {path}

   ### 2. {query}
   ..."

6. Ask: "Clear completed items? (moves to ## Archive)"
   └── Yes → Move all completed items to ## Archive section at bottom
   └── No → Leave as-is (they'll appear again on next digest)

7. Display: "Total spend today: ${X.XX} / ${budget}"
```

**Skill metadata:**
```yaml
name: research-digest
description: Summarize completed background research results for batch review. Use when asked to "digest research", "review research results", or "what research is done".
model: sonnet
disable-model-invocation: true
allowed-tools: Read, Edit, Task, Glob
argument-hint: [auto] — pass "auto" to skip the archive prompt
```

### Research Insight: Context Protection

A standard report is ~2,000 words. A deep report is ~3,500 words. With 5 unreviewed reports, loading them directly consumes 10,000-17,500 words of context. Delegating to Task sub-agents that return only key findings keeps the main session lean.

### Research Insight: Queue Archival

Over weeks of use, the Completed and Failed sections accumulate hundreds of entries, consuming context tokens and risking Edit ambiguity. The digest's "Clear completed items" option moves them to `## Archive` at the bottom. If Archive exceeds 50 items, offer to move to a separate `reports/queue-archive.md`.

### Implementation Phases

#### Phase 1: Foundation (Session 1, ~50 lines)

**Goal:** Queue file template + spend JSON + file structure.

**Tasks:**
1. Create `.claude/skills/` directory (project-level, if not already present)
2. Create `reports/queue.md` with template structure:
   - All three sections: `## Queued`, `## Completed`, `## Failed`
   - Budget line: `budget: $5.00`
   - API comment block documenting the programmatic format
   - Self-documenting syntax examples as comments
3. Create `reports/meta/daily_spend.json` with 3-field schema (today's date, $0.00 spent, budget from queue)
4. Ensure `reports/meta/` directory exists (create if not)
5. Commit checkpoint

**Files:**
- `.claude/skills/` (new directory, if needed)
- `reports/queue.md` (new)
- `reports/meta/daily_spend.json` (new)

**Success criteria:** Both files exist and are valid. Queue file includes all sections and API comment block.

#### Phase 2: Queue Skill (Session 2, ~100-150 lines)

**Goal:** The `/research:queue` skill that reads the queue, checks budget, launches background agents.

**Verify-first item:** Before writing the full skill, test a minimal background agent:
```
Task(run_in_background=true): "Run: python3 main.py --quick 'test query' -o reports/test_bg.md"
```
Confirm: agent completes, file is saved, notification arrives. Also verify `--list` shows the report. **If this fails, fall back to synchronous processing with `context: fork`.**

**Tasks:**
1. Write `.claude/skills/research-queue.md` — full skill instructions covering:
   - Queue file parsing with normalization (BOM, smart quotes, CRLF)
   - **Mode validation** (allowlist: quick, standard, deep)
   - Budget checking (read JSON, date rollover, budget sync from queue file, 15% safety margin)
   - Output path generation (**6-digit zero-padded batch index**)
   - Background agent launching (Task with `run_in_background`, Bash with explicit `timeout: 600000`)
   - Shell escaping for single quotes (`'\''` pattern)
   - Completion handling with **output path as correlation key**
   - Edit tool retry-after-reread pattern
   - Error handling (missing files, malformed entries, failed queries)
   - Session continuity warning in launch status
   - **Concurrency limit: 2** (not 3)
2. Test with 1 quick-mode query to verify end-to-end flow
3. Verify report appears in `python3 main.py --list` output
4. Commit checkpoint

**Files:**
- `.claude/skills/research-queue.md` (new)

**Success criteria:** Can add a query to `reports/queue.md`, run `/research:queue`, see it launch in background, get notification when done, queue file updated, report visible in `--list`.

#### Phase 3: Digest Skill (Session 3, ~60-80 lines)

**Goal:** The `/research:digest` skill that summarizes completed research.

**Tasks:**
1. Write `.claude/skills/research-digest.md` — full skill instructions covering:
   - Queue parsing (find completed items + failed items)
   - **Report reading delegated to Task sub-agents** (returns key findings only)
   - Path validation before reading (starts with `reports/`, no `..`, ends with `.md`)
   - Failed items summary section
   - Digest generation (structured summary per query)
   - Archive prompt (move completed to `## Archive`)
   - "auto" argument to skip archive prompt
   - Spend display
2. Test with 2-3 completed queries from Phase 2 testing
3. Commit checkpoint

**Files:**
- `.claude/skills/research-digest.md` (new)

**Success criteria:** Running `/research:digest` generates a readable summary including any failures, offers to archive, updates queue file.

#### Phase 4: Real-World Test (Session 4)

**Goal:** Run 3-5 real queries across modes while doing other work.

**Tasks:**
1. Queue 3-5 queries related to upcoming Cycle 21 (iterative research loops)
2. Run `/research:queue`
3. Work on something else while agents run
4. Process notifications as they arrive
5. If any notification is missed, verify via `ls reports/` (pull-based fallback)
6. Run `/research:digest` to review all results
7. Verify all reports appear in `python3 main.py --list`
8. Fix any issues found
9. Commit fixes if any

**Success criteria:** Full workflow works end-to-end. Reports are useful. Budget tracking is accurate. All reports visible in `--list`. Failed queries (if any) appear in digest.

## Alternative Approaches Considered

(from brainstorm: `docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md`)

1. **Python Queue Runner** — Standalone `--queue` CLI mode. Rejected: no in-session notifications, ADHD friction (results don't find you), more code to maintain.
2. **Hybrid** — Both skill + Python runner. Rejected: over-engineering for v1. Can add the runner later without changing the skill.
3. **Phase-triggered automation** — Rejected: too magical, hard to debug. Manual queue is predictable.
4. **Watchlist with TTL re-research** — Rejected: adds complexity before proving the basic queue works.
5. **Synchronous processing with `context: fork`** — More reliable (no background agent risks) but defeats the "work while research runs" goal. Keep as fallback if background agents prove unreliable in Phase 2 verify-first test.

## System-Wide Impact

### Interaction Graph

`/research:queue` → reads `reports/queue.md` → reads `reports/meta/daily_spend.json` → launches Task agents → each Task runs `python3 main.py` (full research pipeline: search → fetch → extract → summarize → synthesize) → writes report to `reports/` → Task completion notifies main session → main session updates queue + spend files.

No callbacks, no middleware, no observers. Purely file-based state with skill orchestration.

### Error Propagation

- **Research agent failure** (exit code 1): Task agent captures exit code + stderr. Main session marks item as Failed in queue. Estimated cost still deducted from budget.
- **Task agent timeout** (>10 min): Task tool returns timeout error. Main session marks as Failed. Query can be re-added to Queued manually to retry.
- **Queue file parse error**: Skill skips malformed lines with a warning showing the offending line. Valid lines still process.
- **Spend file corruption**: Skill recreates with today's date, budget from queue file, and $0 spent (safe default — may allow over-budget for the day, but won't block research).
- **Edit tool match failure**: Skill re-reads the queue file and retries with exact text as found on disk.
- **Notification not received**: After launching, if no notification arrives within 5 minutes, check output file paths. If file exists, process as completion.

### Research Insight: Retry Workflow for Failed Items

The plan should document how users retry failed queries. Add to the queue template comments:

```markdown
<!-- To retry a failed query: copy the line from ## Failed to ## Queued,
     change [!] back to [ ], and run /research:queue again. -->
```

### State Lifecycle Risks

- **Session closes mid-run**: Background Task agents die. Items remain in `## Queued` (no Running state to get stuck in). Next `/research:queue` invocation picks them up naturally. No stale detection needed.
- **Orphaned reports**: If a Task completes and writes a report but the session dies before updating the queue, the report exists on disk but isn't tracked. Future enhancement: scan `reports/` for untracked files.
- **Double-counting spend on retried items**: When an item is re-launched (because the session died before completion), its cost was already pre-allocated in the spend JSON. When it re-launches on the next invocation, cost is deducted again. Acceptable for v1 — worst case is double-charging one batch ($0.24 - $1.70 depending on modes).

### API Surface Parity

No existing interfaces need updating. These are net-new skills. The research agent CLI and programmatic API remain unchanged.

### Research Insight: Rate Limit Impact

Each research query makes 8-65 Anthropic API calls depending on mode:

| Stage | Quick | Standard | Deep |
|-------|-------|----------|------|
| Decompose + context | 1 | 2 | 2 |
| Search + refine | 3 | 3 | 3 |
| Summarize chunks | 3-12 | 6-24 | 10-36 |
| Relevance scoring | 3-4 | 6-10 | 10-12 |
| Skeptic + synthesis | 1 | 3-4 | 5-7 |
| **Total** | **~8-18** | **~15-45** | **~25-65** |

With 2 concurrent queries: 16-90 API calls competing in a 1-3 minute window. The existing `retry_api_call()` in `api_helpers.py` handles 429s but with only 1 retry and no jitter. Consider adding jitter (`retry_delay + random.uniform(0, 1.5)`) as a low-effort improvement.

### Integration Test Scenarios

1. **Happy path**: Queue 2 standard queries → run skill → both complete → queue updated → digest shows both
2. **Budget limit**: Queue 3 standard queries with $0.50 budget → only 1 launches → notification says "budget reached" with remaining amount
3. **Mixed results**: Queue 1 valid + 1 nonsense query → one succeeds, one fails → both tracked correctly → digest shows both
4. **Session crash recovery**: Queue 2 items → run skill → close session before completion → reopen → items still in Queued → run skill again → items launch
5. **Date rollover**: Set spend to yesterday's date → run skill → spend resets to $0 → queries launch
6. **`--list` compatibility**: After background queries complete → `python3 main.py --list` shows all reports
7. **Mode validation**: Add entry with `--verbose` mode → skill skips with warning
8. **Missed notification**: Launch query → if no notification, check file after 5 min

## Acceptance Criteria

### Functional Requirements

- [ ] `reports/queue.md` template exists with documented syntax and API comment block
- [ ] `reports/meta/daily_spend.json` uses simplified 3-field schema
- [ ] `/research:queue` reads queue, validates modes, checks budget, launches up to 2 background agents
- [ ] Background agents run the research CLI with `-o` for forced output path (6-digit padded index)
- [ ] On completion, queue file is updated (Queued → Completed/Failed, no Running state)
- [ ] On completion, spend JSON is updated with cost
- [ ] 2-3 line notification printed when each background agent completes
- [ ] Budget enforcement with 15% safety margin: queries skipped when remaining budget < estimated cost
- [ ] Failed queries marked with `[!]` and reason, cost deducted from budget
- [ ] `/research:digest` summarizes completed items AND mentions failed items
- [ ] `/research:digest` offers to archive completed items (move to `## Archive`)
- [ ] Date rollover resets daily spend and syncs budget from queue file
- [ ] Queue items processed in FIFO order (top to bottom)
- [ ] Quick mode works in queue (forced `-o` bypasses `auto_save=False`)
- [ ] Reports created by the skill are visible in `python3 main.py --list`
- [ ] Mode allowlist validation prevents arbitrary CLI flag injection

### Non-Functional Requirements

- [ ] No changes to existing research agent Python code
- [ ] Skills work with `model: sonnet` (cost-efficient orchestration)
- [ ] Skills include `disable-model-invocation: true` (manual control only)
- [ ] Queue file remains human-readable and hand-editable
- [ ] Skill handles missing/empty/malformed queue files gracefully
- [ ] Sections parsed by name (case-insensitive), not by position

### Quality Gates

- [ ] End-to-end test: queue 2 queries, both complete, digest works
- [ ] Budget test: verify queries stop when budget reached
- [ ] Failure test: verify failed queries tracked correctly and shown in digest
- [ ] `--list` test: verify background reports appear in CLI listing

## Success Metrics

- Background research runs while you work — no waiting
- Notifications arrive when queries complete — results find you
- Budget tracking prevents surprise costs
- Digest provides a single review point for batch results (including failures)
- Reports are discoverable via `--list`

## Dependencies & Prerequisites

- **Claude Code skills directory** — `.claude/skills/` must be created (already exists from prior work)
- **Existing CLI** — `python3 main.py` must be working (currently 695 tests passing)
- **API keys** — `.env` with `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` must be configured
- **reports/ directory** — already exists with `meta/` subdirectory

## Risk Analysis & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Background Task timeout on deep queries | Query lost, needs retry | Low | 10-min timeout; deep mode rarely exceeds 5 min |
| Background notifications unreliable | Completions not processed | Medium | Pull-based fallback: check output files after 5 min |
| Long-running background tasks crash terminal | Session instability | Low | Keep to 2 concurrent; standard/quick queries preferred |
| Session closes mid-run | Items need re-launch | Medium | No Running state — items stay Queued, picked up next invocation |
| Rate limits from parallel queries | 429 errors, degraded results | Medium | Limit to 2 concurrent; stagger launches by 15-20s |
| Queue file edited while skill runs | Edit match failures | Low | Re-read + retry pattern for Edit tool |
| Budget tracking inaccuracy (static estimates) | Over/under spend by ~20% | Medium | 15% safety margin; actual tracking is future enhancement |
| Mode injection via hand-edited queue | Unintended CLI behavior | Medium | Mode allowlist validation (quick/standard/deep only) |
| Budget bypass via JSON tampering | Runaway API spending | Low | Schema validation on read; recreate if invalid |
| Queue file grows unboundedly | Context bloat, edit ambiguity | Medium | Digest offers archival; cap at 20 items before suggesting archive |

## Future Considerations

- **Actual cost tracking** — Read `response.usage` from Anthropic API for real costs instead of estimates. Track both estimated and actual, compute rolling correction factor after 20+ queries.
- **Add retry jitter** — `api_helpers.py:68`: add `random.uniform(0, 1.5)` to `retry_delay` to prevent thundering herd when parallel processes all hit 429 simultaneously.
- **`/research:add` skill** — A 10-line skill that takes `--mode "query"` as an argument and appends to the queue. Makes the system composable for other skills/agents.
- **Offline runner** — Approach B from brainstorm (Python queue runner) for research while Claude Code is closed
- **Watchlist mode** — Periodic re-research of topics with TTL-based staleness (builds on existing `staleness.py`)
- **Cross-project queues** — Single queue file serving multiple projects
- **Smart scheduling** — Queue queries based on compound engineering phase (auto-research for upcoming brainstorms)
- **Mode-aware slot counting** — Deep queries count as "2 slots" in the concurrency limit to prevent worst-case API load
- **CLI output path validation** — Defense-in-depth: validate `-o` path is within project directory in `cli.py` before writing

## Documentation Plan

- Update `CLAUDE.md` with `/research:queue` and `/research:digest` usage under a new "Background Research" section
- Queue file format documented inline in `reports/queue.md` template (self-documenting, including API comment block)

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md](docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md) — Key decisions carried forward: manual queue (not automatic), per-query mode choice, daily budget cap, Claude Code background agents as execution model, notification + digest delivery.

### Internal References

- CLI entry point: `research_agent/cli.py:70-75` (auto-save path generation)
- `--list` regex: `research_agent/cli.py:82` (`_NEW_FORMAT = re.compile(r"^(.+)_(\d{4}-\d{2}-\d{2})_\d{6,}\.md$")`)
- Programmatic API: `research_agent/__init__.py` (`run_research`, `run_research_async`)
- Mode configs: `research_agent/modes.py` (cost estimates, auto_save flags)
- Atomic writes: `research_agent/safe_io.py` (reusable for spend file)
- API retry logic: `research_agent/api_helpers.py:26-79` (retry_api_call, DEFAULT_MAX_RETRIES=1)
- Context result pattern: `research_agent/context_result.py` (model for queue loading states)
- Existing skills: `.claude/skills/research-queue.md`, `.claude/skills/research-digest.md`
- Solutions doc: `docs/solutions/architecture/skill-only-features-background-research.md`

### External References (from research agents)

- Background notification bug: [GitHub Issue #21048](https://github.com/anthropics/claude-code/issues/21048)
- Background task crash: [GitHub Issue #24004](https://github.com/anthropics/claude-code/issues/24004)
- Timeout configuration: [GitHub Issue #5615](https://github.com/anthropics/claude-code/issues/5615)
- Claude Code skills docs: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- planning-with-files skill: [github.com/OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files)
- todo.txt format: [todotxt.org](http://todotxt.org/)
- LiteLLM budget controls: [docs.litellm.ai/docs/proxy/budget_reset_and_tz](https://docs.litellm.ai/docs/proxy/budget_reset_and_tz)

### Related Work

- Inspiration: Mitchell Hashimoto interview (Pragmatic Engineer) — "always have an agent running in the background"
- Research agent roadmap: `docs/research/master-recommendations-future-cycles.md` (Cycle 20+: "scheduled or triggered research")

## Feed-Forward

- **Hardest decision:** How to handle the quick-mode `auto_save=False` problem. Solved by having the skill always pass `-o <path>`, which forces all modes to save to disk without modifying Python code. This is clean but means the skill must generate filenames matching the CLI's format.
- **Rejected alternatives:** Having background agents update the queue file themselves (concurrent write risk), parsing CLI stdout for report paths (fragile), requiring only standard/deep modes in the queue (unnecessarily restrictive). Also rejected the Running state (adds stale detection complexity for no benefit when items can simply stay Queued).
- **Least confident:** Background notification reliability. GitHub issues document that `run_in_background` completion notifications are not 100% reliable. The pull-based fallback (check output files) mitigates this, but if notifications fail frequently, the UX degrades from "results find you" to "check periodically." Phase 2's verify-first test should stress this — run 2 concurrent queries and verify both notifications arrive.
