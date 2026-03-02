---
name: update-learnings
description: Update all learning docs after compound phase — LESSONS_LEARNED.md, docs/lessons/, patterns-index.md, MEMORY.md, HANDOFF.md, and journal
argument-hint: "[cycle number]"
---

# Update Learnings

<command_purpose>After /workflows:compound creates the solution doc, this skill updates all the surrounding learning files so nothing falls through the cracks.</command_purpose>

## When to Run

Run immediately after `/workflows:compound` completes. The compound phase creates the solution doc; this skill propagates lessons to all the other files.

## Arguments

<update_target> $ARGUMENTS </update_target>

- First word = cycle number (e.g., "19" for Cycle 19). If omitted, detect from the newest solution doc's `cycle:` frontmatter or git log.

## Steps

### Step 1: Gather Context

Read these files to understand what just happened:

1. **Most recent solution doc** — `docs/solutions/` sorted by modification time, pick newest. Note its `category:` frontmatter (maps to `docs/lessons/` file).
2. **LESSONS_LEARNED.md** — current state of the hub
3. **The matching category file** — `docs/lessons/[category].md` (e.g., if solution doc has `category: security`, read `docs/lessons/security.md`)
4. **docs/lessons/patterns-index.md** — current pattern rows
5. **MEMORY.md** — at `/Users/alejandroguillen/.claude/projects/-Users-alejandroguillen-Projects-research-agent/memory/MEMORY.md`
6. **HANDOFF.md** — current handoff state
7. **Review summary** — `docs/reviews/*/REVIEW-SUMMARY.md` for the current branch (if it exists)
8. **Today's journal** — `~/Documents/dev-notes/$(date +%Y-%m-%d).md` (may not exist yet)

### Step 2: Identify New Lessons

From the solution doc and review summary, extract:

- **Key lesson** — one sentence for the Development History table
- **New top patterns** — did any pattern recur across 3+ cycles? Check existing Top 10 Patterns table.
- **Category file section** — narrative section for the matching `docs/lessons/[category].md`
- **Pattern index rows** — new rows for `docs/lessons/patterns-index.md`
- **Risk chain** — what was flagged in feed-forward, what actually happened, what was learned

### Step 3: Update Files

Update these files (read each one first before editing):

#### 3a. LESSONS_LEARNED.md

- Add row to **Development History** table: `| [cycle] | [feature] | [key lesson] |`
- If a pattern recurred across 3+ cycles, update **Top 10 Patterns** table (add cycle number, or add new row if it's a new top pattern)
- Keep under 100 lines — it's a hub, not a narrative

#### 3b. docs/lessons/[category].md

- Add a new section for this cycle's lessons. Follow the existing format in the file — each section has a cycle number header and narrative with code examples where relevant.
- Update the YAML frontmatter `cycles:` array to include the new cycle number.
- This is where the narrative detail lives — LESSONS_LEARNED.md just links here.

#### 3c. docs/lessons/patterns-index.md

- Add new rows to the patterns table for any new takeaways from this cycle.
- Format: `| [Category] | [Key Takeaway] | [Cycle(s)] | [category].md |`
- If an existing row's pattern recurred, append the new cycle number to its `Cycle(s)` column.

#### 3d. MEMORY.md

- Add or update implementation notes for the completed cycle (key decisions, solution doc path).
- Keep concise — MEMORY.md is loaded into every conversation context.

#### 3e. HANDOFF.md

- Update the header and **Current State** section to reflect the cycle is complete and learnings are propagated.
- Set **Next Phase** to indicate the next cycle begins with a new brainstorm.

#### 3f. Journal entry

- Append to `~/Documents/dev-notes/YYYY-MM-DD.md` (create if needed)
- Format: `## Research Agent — Cycle N Complete: [Feature Name]`
- Include: What shipped, key lesson, stats, solution doc path
- Keep it concise — 30-50 lines max

### Step 4: Report

Print a summary:

```
Update Learnings — Cycle [N] Complete

Files updated:
  - LESSONS_LEARNED.md — added row [cycle] | [feature]
  - docs/lessons/[category].md — added Cycle [N] section
  - docs/lessons/patterns-index.md — [N] new rows
  - MEMORY.md — cycle notes updated
  - HANDOFF.md — state updated
  - ~/Documents/dev-notes/YYYY-MM-DD.md — journal entry appended

New top patterns identified: [count or "none"]
Pattern index rows added: [count]
```

## Rules

1. **Read before writing** — always read a file before editing it
2. **Don't duplicate** — link to solution docs, don't copy their content into LESSONS_LEARNED.md
3. **Don't invent lessons** — only extract what's in the solution doc and review summary
4. **Keep LESSONS_LEARNED.md under 100 lines** — it's a hub, not a narrative
5. **Keep journal entries under 50 lines** — concise summary, not a rewrite of the solution doc
6. **Preserve existing content** — append, don't overwrite. Edit specific sections.
7. **Match existing format** — follow the table structures and section headers already in each file
8. **Use the `category:` frontmatter** — the solution doc's category determines which `docs/lessons/` file to update
