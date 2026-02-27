---
name: research-queue
description: Process background research queue — launches queries as background agents while you work. Use when asked to "queue research", "run background research", or "process the queue".
model: sonnet
---

# Background Research Queue

<command_purpose>Read the research queue, check the daily budget, and launch queued queries as background agents. Results are delivered as notifications when each completes.</command_purpose>

## Step 1: Read and Normalize Queue File

Read `reports/queue.md`. If the file does not exist, create it from the template below, tell the user "Queue created at reports/queue.md — add queries and run /research:queue again." then STOP.

```markdown
# Research Queue

budget: $5.00

<!-- Queue API (for other skills/agents):
  To add items: append `- [ ] --{mode} "{query}"` to the ## Queued section.
  To check status: read ## Completed and ## Failed sections.
  Budget file: reports/meta/daily_spend.json
  Valid modes: quick, standard, deep

  States:
  - [ ] --mode "query text"                    → Queued (waiting to run)
  - [x] --mode "query" → path ($cost)         → Completed
  - [!] --mode "query" → reason ($cost)       → Failed

  Cost estimates: --quick ($0.12), --standard ($0.35), --deep ($0.85)
  Items run top-to-bottom, up to 2 in parallel.
  Daily budget resets at midnight (local time). -->

## Queued

## Completed

## Failed
```

**Normalize before parsing** (hand-edited files may have encoding issues):
- Strip UTF-8 BOM (`\ufeff`) from the start of the file
- Normalize line endings: `\r\n` → `\n`
- Normalize smart quotes: `\u201c` and `\u201d` → `"`
- Replace tabs with spaces
- Strip trailing whitespace per line
- Strip HTML comments (`<!-- ... -->`) before parsing entries (but NOT the API comment block at the top — it's harmless)
- Strip invisible Unicode from structural elements (NOT from query content — emoji/special chars are valid in queries):
  U+200B zero-width space, U+200C ZWNJ, U+200D ZWJ, U+200E LTR mark, U+200F RTL mark, U+2060 word joiner, U+FEFF BOM, U+00A0 non-breaking space

**File safety checks:**
- If file is larger than 1 MB, STOP with error: "Queue file exceeds 1 MB — archive old entries first."
- If the first 8 KB contains null bytes, STOP with error: "Queue file appears to contain binary data."

## Step 2: Parse Queue Sections

**Parse sections by header name, not position** (users may reorder):
- Match `## Queued`, `## Completed`, `## Failed` by header text (case-insensitive)
- Accept headers with trailing content: `## Queued (3 items)` matches as Queued
- Accept heading level 3 (`### Queued`) with a warning
- If duplicate `## Queued` headers exist, use the first and warn
- A section ends at the next header of the same or higher level (`##`)
- Empty sections are valid (nothing to process)

**Parse budget line:** Find `budget: $X.XX` (first match only, outside of sections).
- Accept without `$` symbol: `budget: 5.00` → 5.00
- Accept without decimals: `budget: $5` → 5.00
- Strip commas: `budget: $1,000.00` → 1000.00
- Reject non-`$` currency symbols (e.g., `€`): warn "unrecognized currency, use $"
- Must be between $0.01 and $50.00. If missing, zero, negative, or out of range: warn and STOP (do not default)
- If multiple budget lines found, use first and warn about duplicates

**Parse queued items** — lines in the `## Queued` section matching:
```
- [ ] --{mode} "{query text}"
```

**Validation rules (skip-and-warn for each):**

| Input | Behavior |
|-------|----------|
| `- [ ] --standard "query"` | **Accept** (standard format) |
| `- [ ]  --standard   "query"` | **Accept** (normalize whitespace) |
| `- [ ] --standard query without quotes` | **Accept** (treat everything after `--mode ` as query) |
| `- --standard "query"` (no checkbox) | Skip — "missing checkbox `[ ]`" |
| `- [X] ...` or `- [x] ...` in Queued | Skip — "checked item in Queued section" |
| `- [*]` or `- [v]` or `- [!]` | Skip — "invalid checkbox marker for Queued" |
| `[ ] --standard "query"` (no dash) | Skip — "missing list dash `-`" |
| `  - [ ] ...` (indented) | Skip — "indented entry — move to column 1" |
| `- [ ] --standard ""` | Skip — "empty query" |
| `- [ ] --standard "   "` | Skip — "whitespace-only query" |
| Empty or blank lines | Skip silently |

**Mode validation (defense-in-depth):**
1. Lowercase the mode string
2. Check ASCII-only: reject if mode contains any character outside `[a-z]` — this eliminates Unicode homoglyph attacks (Cyrillic `а` vs ASCII `a`)
3. Check allowlist: must be exactly `quick`, `standard`, or `deep`
4. If invalid: skip with warning "Skipping entry with invalid mode '{mode}' — use --quick, --standard, or --deep"

If no valid queued items, say "Queue is empty. Add queries to the ## Queued section in reports/queue.md" and STOP.

## Step 3: Check Daily Budget

Read `reports/meta/daily_spend.json`. The schema is:
```json
{"date": "2026-02-25", "budget": 5.00, "total_spent": 0.47}
```

Handle these cases:
- **File missing or corrupt**: Create with today's date, budget from queue file, $0.00 spent. Warn: "Budget tracker was reset — previous spend data lost."
- **Date is not today**: Reset — write with today's date, budget from queue file, $0.00 spent. Say: "New day — daily spend reset to $0.00."
- **Date is today**: Use as-is. If the budget in JSON differs from queue file, sync it from the queue file (queue file is the source of truth for budget).

**JSON validation:** `date` must be YYYY-MM-DD, `budget` must be $0.01-$50.00, `total_spent` must be >= 0. If any field fails, treat as corrupt and recreate.

**Mode-specific safety margins** (reserves headroom for estimation error):

| Mode | Estimate | Safety Margin | Effective Cost |
|------|----------|---------------|----------------|
| quick | $0.12 | 15% | $0.14 |
| standard | $0.35 | 25% | $0.44 |
| deep | $0.85 | 40% | $1.19 |

Calculate: `remaining = budget - total_spent`

## Step 4: Select Items to Launch

Walk the queued items top-to-bottom (FIFO). For each item:
- Calculate effective cost: `estimated_cost / (1 - safety_margin[mode])` — this is the budget reservation
  - quick: $0.12 / 0.85 = $0.14
  - standard: $0.35 / 0.75 = $0.47
  - deep: $0.85 / 0.60 = $1.42
- If `effective_cost > remaining`: skip it. Say "Budget insufficient for [mode] query ($X.XX remaining, needs $Y.YY with safety margin). Budget resets tomorrow."
- If `effective_cost <= remaining`: add to launch batch, deduct estimated_cost (not effective_cost) from remaining and from total_spent in the JSON.
- **Stop adding after 2 items** (max parallel). If more items remain, say "N more items queued — run /research:queue again after these complete."

If nothing can launch (budget exhausted), say "Daily budget of $X.XX reached ($Y.YY spent). Resets tomorrow or increase budget in reports/queue.md." and STOP.

## Step 5: Launch Background Agents

For each item in the launch batch:

### 5a. Generate output path

Format: `reports/{sanitized_query}_{YYYY-MM-DD}_{HHMMSS}_{batch_index:06d}.md`

Where:
- `sanitized_query` = lowercase, spaces/non-alphanumeric to underscores, collapse multiple underscores, strip leading/trailing underscores, max 50 chars
- Date and time from current local time
- `batch_index` = **6-digit zero-padded** position in launch batch (000001, 000002). This MUST be 6 digits — the `--list` command regex expects `\d{6,}`.

### 5b. Sanitize query for shell (defense-in-depth pipeline)

Apply ALL steps in order before constructing the Bash command:
1. Strip leading/trailing whitespace
2. Replace `\n`, `\r`, `\x00` with space
3. If query exceeds 500 characters, skip this item with warning: "Query too long (N chars, max 500) — shorten it"
4. Escape single quotes: replace every `'` with `'\''`
5. Place the result inside single quotes in the Bash command

Inside single quotes, `$()`, backticks, `|`, `&`, `;`, `>`, `<` are ALL literal — no shell injection is possible.

### 5c. Update daily_spend.json

Add the estimated cost (not effective cost) to `total_spent`. Write the file.

### 5d. Launch background Task agent

**Stagger launches:** Launch the first agent immediately. Wait 15-20 seconds before launching the second (use `sleep 15` in Bash). This spreads API-heavy bursts.

```
Task(run_in_background=true, subagent_type="general-purpose"):
  "Run this exact command in /Users/alejandroguillen/Projects/research-agent and report the result:

   python3 main.py --{validated_mode} '{escaped_query}' -o {output_path}

   Use a 600000ms timeout for the Bash command.
   After the command finishes, report:
   - Exit code (0=success, 1=failure)
   - Whether the output file exists at {output_path} (check with ls)
   - If it failed, the last 5 lines of stderr
   - The approximate duration in seconds"
```

### 5e. Record correlation key

Store the output_path for each launched item in-memory. This is how you match Task completion notifications back to queue entries.

## Step 6: Report Launch Status

After launching, tell the user:

```
Launched N background research queries:
1. [mode] "query text" → path ($estimated_cost)
2. [mode] "query text" → path ($estimated_cost)

Budget: $X.XX / $Y.YY spent today. N items remaining in queue.

Note: Background agents will stop if this session closes. Keep the session open until they complete.
```

## Step 7: Handle Completion Notifications

When a background Task agent completes and you receive its result:

### If successful (exit code 0, file exists):

1. **Match to queue item** by output path (correlation key).

2. **Update queue file** — move item from `## Queued` to `## Completed`:
   ```
   - [x] --mode "query text" → reports/output_path.md ($0.35)
   ```
   Use the Edit tool. **If the Edit fails** (exact string not found — user may have hand-edited the file), re-read the queue file with Read, find the actual line text for this item, and retry with the exact text as it appears.

3. **Notify the user:**
   ```
   Research complete: "query text" → reports/output_path.md ($0.35)
   ```

### If failed (exit code 1 or file missing):

1. **Sanitize error reason**: Take only the final error message line. Truncate to 100 chars. Strip any strings matching API key patterns (`sk-ant-*`, `tvly-*`).

2. **Update queue file** — move item from `## Queued` to `## Failed`:
   ```
   - [!] --mode "query text" → {sanitized error reason} ($0.35)
   ```
   Same Edit-retry pattern as success case.

3. **Notify the user:**
   ```
   Research failed: "query text" — {sanitized error reason} ($0.35 still counted toward budget)
   ```

### Fallback: If no notification arrives within 5 minutes

Check the output file paths directly (`ls reports/{expected_path}`). If the file exists, treat as successful completion and process it. Background notifications are not 100% reliable.

## Important Rules

- **You are the ONLY writer** to `reports/queue.md` and `reports/meta/daily_spend.json`. Background agents NEVER touch these files.
- **Always use the Edit tool** to update the queue file (not Write) — preserves sections you're not modifying.
- **Failed queries count against budget** — API calls are made even when the pipeline fails.
- **Quick mode queries work** — the `-o` flag forces output to disk even though quick mode normally doesn't auto-save.
- **No Running state** — items stay in `## Queued` until moved directly to `## Completed` or `## Failed`. If the session dies mid-run, items remain Queued and get picked up on next invocation.
- **Max 2 concurrent agents** — more than 2 causes notification reliability issues and API rate limit pressure.
- **If the user asks to add queries**, help them add lines to the `## Queued` section in the correct format, then offer to process the queue.
