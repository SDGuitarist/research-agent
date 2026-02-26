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

For each unreviewed item, extract the report file path. **Validate the path**: must start with `reports/`, must not contain `..`, must end with `.md`. Skip items with invalid paths and warn the user.

Read each valid report file using the Read tool and extract 3-5 key findings.

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
**Total cost this batch:** ${sum of costs above}
```

Display this digest to the user.

## Step 4: Mark as Reviewed

If the user passed "auto" as an argument, mark all items as reviewed automatically without asking.

Otherwise, ask the user: "Mark all N items as reviewed?"

- **If yes**: Edit `reports/queue.md` — append ` reviewed` to each unreviewed completed item.
- **If no**: Leave as-is. They'll appear again on next `/research:digest` run.
- **If selective**: If the user wants to mark only some items, edit just those lines.
