---
name: research-queue
description: Process background research queue — launches queries as background agents while you work
model: sonnet
---

# Background Research Queue

<command_purpose>Read the research queue, check the daily budget, and launch queued queries as background agents. Results are delivered as notifications when each completes.</command_purpose>

## How It Works

```
1. You add queries to reports/queue.md (manually, any editor)
2. Run /research:queue
3. Skill checks budget, launches up to 3 queries as background agents
4. You keep working — notifications arrive as each finishes
5. Run /research:digest to review all results at once
```

## Step 1: Read Queue File

Read `reports/queue.md`. If the file does not exist, create it from the template below and tell the user "Queue created at reports/queue.md — add queries and run /research:queue again." then STOP.

```markdown
# Research Queue

budget: $5.00

## Queued

## Running

## Completed

## Failed
```

Parse the file:
- Extract `budget: $X.XX` from the line near the top (default $5.00 if missing)
- Find all lines in the `## Queued` section matching `- [ ] --{mode} "{query}"`
- Find all lines in the `## Running` section (stale items from crashed sessions)
- If mode is missing from a queued line, default to `--standard`
- Skip blank lines and lines that don't match the format (warn about skipped lines)

If no queued items AND no stale running items, say "Queue is empty. Add queries to reports/queue.md" and STOP.

## Step 2: Handle Stale Running Items

If there are items in the `## Running` section, these are from a previous session that closed before they completed. Move them back to `## Queued` (at the top, so they run first). Edit the queue file to reflect this.

Say: "Recovered N stale items from previous session — re-queued for retry."

## Step 3: Check Daily Budget

Read `reports/meta/daily_spend.json`. Handle these cases:

- **File missing**: Create it with today's date, budget from queue file, $0.00 spent, empty queries array.
- **Date is not today**: Reset — write new file with today's date, $0.00 spent, empty queries array. Budget from queue file.
- **Date is today**: Use as-is.

Calculate: `remaining = budget - total_spent`

Cost estimates per mode:
- `--quick`: $0.12
- `--standard`: $0.35
- `--deep`: $0.85

## Step 4: Select Items to Launch

Walk the queued items top-to-bottom (FIFO). For each item:
- If `estimated_cost > remaining`: skip it and all remaining items. Say "Budget reached ($X.XX / $Y.YY spent). Skipping N remaining queries."
- If `estimated_cost <= remaining`: add to launch batch, deduct from remaining.
- Stop adding after 3 items (max parallel).

If nothing can launch (budget exhausted), say "Daily budget of $X.XX reached. Reset tomorrow or increase budget in reports/queue.md." and STOP.

## Step 5: Launch Background Agents

For each item in the launch batch:

1. **Generate output path**: Use this format exactly:
   ```
   reports/{sanitized_query}_{YYYY-MM-DD}_{HHMMSS}{microseconds}.md
   ```
   Where sanitized_query = lowercase, spaces to underscores, strip non-alphanumeric (keep underscores), collapse multiple underscores, truncate to 50 chars at word boundary.

2. **Update queue file**: Move the item from `## Queued` to `## Running`, adding the output path:
   ```
   - [~] --standard "query text" → reports/output_path.md
   ```

3. **Update daily_spend.json**: Add an entry with status "running" and the estimated cost.

4. **Launch background Task agent**:
   ```
   Task(run_in_background=true, subagent_type="general-purpose"):
     "Run this exact command and report the result:
      cd /Users/alejandroguillen/Projects/research-agent && python3 main.py --{mode} '{query}' -o {output_path}
      Use a 600000ms timeout for the Bash command.
      After the command finishes, report:
      - Exit code (0=success, 1=failure)
      - Whether the output file exists (check with ls)
      - The first 3 lines of the output file if it exists
      - Any error message from stderr if it failed"
   ```

5. Repeat for each item (launch all background agents in parallel — multiple Task calls in one message).

## Step 6: Report Launch Status

After launching, tell the user:

```
Launched N background research queries:
1. [mode] "query text" → path ($cost)
2. [mode] "query text" → path ($cost)

Budget: $X.XX / $Y.YY spent today. N items remaining in queue.

Keep working — you'll be notified as each completes.
```

## Step 7: Handle Completion Notifications

When a background Task agent completes and you receive its result:

### If successful (exit code 0, file exists):

1. **Update queue file**: Move item from `## Running` to `## Completed`:
   ```
   - [x] --standard "query text" → reports/output_path.md ($0.35)
   ```

2. **Update daily_spend.json**: Change status from "running" to "completed".

3. **Read the first 200 characters of the report file** for the notification.

4. **Notify the user**:
   ```
   Research complete: "query text" → reports/output_path.md ($0.35)
   {first ~150 chars of report as preview}
   ```

### If failed (exit code 1 or file missing):

1. **Update queue file**: Move item from `## Running` to `## Failed`:
   ```
   - [!] --standard "query text" → {brief error reason} ($0.35)
   ```

2. **Update daily_spend.json**: Change status from "running" to "failed". Cost still counts.

3. **Notify the user**:
   ```
   Research failed: "query text" — {error reason} ($0.35 still counted toward budget)
   ```

## Important Rules

- **You are the ONLY writer** to `reports/queue.md` and `reports/meta/daily_spend.json`. Background agents NEVER touch these files.
- **Always use the Edit tool** to update the queue file (not Write) — preserves sections you're not modifying.
- **Failed queries count against budget** — API calls are made even when the pipeline fails.
- **Quick mode queries work** — the `-o` flag forces output to disk even though quick mode normally doesn't auto-save.
- **If the user asks to add queries**, help them add lines to the `## Queued` section in the correct format, then offer to process the queue.
