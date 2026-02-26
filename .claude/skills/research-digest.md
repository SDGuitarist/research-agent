---
name: research-digest
description: Summarize unreviewed background research results for batch review
model: sonnet
---

# Research Digest

<command_purpose>Read all completed-but-unreviewed research queries, generate a summary digest, and offer to mark them as reviewed.</command_purpose>

## Step 1: Read Queue File

Read `reports/queue.md`. If it doesn't exist, say "No research queue found. Run /research:queue first." and STOP.

Find all lines in the `## Completed` section that do NOT end with `reviewed`:
```
- [x] --standard "query text" → reports/path.md ($0.35)        ← unreviewed
- [x] --standard "query text" → reports/path.md ($0.35) reviewed  ← skip
```

If no unreviewed items, say "No unreviewed research. Queue is clear." and STOP.

## Step 2: Read Reports

For each unreviewed item, extract the report file path and read the report.

**To protect context**, delegate reading to a background sub-agent if there are more than 3 unreviewed reports:

```
Task(subagent_type="general-purpose"):
  "Read these report files and extract a 3-5 bullet summary of key findings from each:
   - reports/path1.md
   - reports/path2.md
   Return the summaries in order."
```

For 3 or fewer, read them directly using the Read tool and extract key findings yourself.

## Step 3: Generate Digest

Format the digest as:

```markdown
## Research Digest — {date}

{N} queries completed since last review.

### 1. "{query text}"
**Mode:** {mode} | **Sources:** {N from report} | **Cost:** ${X.XX}
- Key finding 1
- Key finding 2
- Key finding 3
**Report:** reports/{path}.md

### 2. "{query text}"
...

---
**Total spend today:** ${X.XX} / ${budget}
**Remaining budget:** ${X.XX}
```

Display this digest to the user.

## Step 4: Mark as Reviewed

Ask the user: "Mark all N items as reviewed?"

- **If yes**: Edit `reports/queue.md` — append ` reviewed` to each unreviewed completed item.
- **If no**: Leave as-is. They'll appear again on next `/research:digest` run.
- **If selective**: If the user wants to mark only some items, edit just those lines.

## Step 5: Show Spend Summary

Read `reports/meta/daily_spend.json` and display:

```
Today's spend: ${total_spent} / ${budget} ({N} queries run)
Remaining budget: ${remaining}
```
