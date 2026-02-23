# Batched Fix Execution

You are running batched fixes from a completed code review. This process reads the REVIEW-SUMMARY.md, groups findings into risk-based batches, and executes one batch per session with disk-persisted results.

## Rules — Read These First

1. **One batch per session.** After committing a batch, STOP. Tell the user to run the next batch in a new session.
2. **Always write result files before stopping.** Every batch produces a `docs/fixes/<branch>/batchN.md` file.
3. **The plan step does NOT fix anything.** It only writes the batch plan and stops.
4. **Each batch step has a STOPGAP.** List all changes, show affected lines, flag ordering dependencies. Wait for user confirmation before making any edits.
5. **Three questions are mandatory.** Every batch step ends with the hardcoded three questions answered in the result file.
6. **All output goes to `docs/fixes/<branch>/`.** Create the directory if it doesn't exist.
7. **Run tests after each batch.** `python3 -m pytest tests/ -v` must pass before committing.

## Parse the Argument

The argument is: `$ARGUMENTS`

Extract the command — one of: `plan`, `batch1`, `batch2`, `batch3`, `batch4`, `close`.

If no command is specified, tell the user:
```
Usage: /fix-batched <plan|batch1|batch2|batch3|batch4|close>

Run steps in order across separate sessions:
  Session 1: /fix-batched plan
  Session 2: /fix-batched batch1
  Session 3: /fix-batched batch2
  Session 4: /fix-batched batch3
  Session 5: /fix-batched close
```

---

## Resolve the Branch

Detect the current git branch using `git branch --show-current`.

For the `plan` step: also locate the review summary at `docs/reviews/<branch>/REVIEW-SUMMARY.md`. If it doesn't exist, tell the user to run `/review-batched synthesize` first.

For `batch1` through `batch4` and `close`: read the branch from `docs/fixes/<branch>/pr-metadata.md`. If it doesn't exist, tell the user to run `/fix-batched plan` first.

---

## plan — Group Findings into Batches

1. Read `docs/reviews/<branch>/REVIEW-SUMMARY.md`.
2. Read `docs/reviews/<branch>/pr-metadata.md` if it exists (for changed file context).
3. Group every finding (P1, P2, P3) into batches by risk profile:

   **Batch A — Deletes and removals** (zero regression risk)
   Dead code deletion, unused file removal, dead import cleanup. Things where the only change is removing lines. No new behavior introduced.

   **Batch B — Data integrity and hot-path changes** (needs care, separate commit)
   SSRF protections, sanitization logic, content extraction pipeline, anything touching the research agent's critical path. These changes alter runtime behavior in ways that affect data correctness or security.

   **Batch C — Code quality and abstractions** (safe but more surface area)
   Type hints, helper extractions, validation improvements, error handling, interface changes. Refactoring that changes structure but not behavior. More files touched, so higher review surface.

   **Batch D+ — Deferred or needs discussion**
   New dependencies, new features, test coverage (separate effort), architectural changes. Anything that adds dependencies, new features, or needs product decisions.

4. Create the directory `docs/fixes/<branch>/`.
5. Write `docs/fixes/<branch>/pr-metadata.md`:

```markdown
# Fix Metadata

**Branch:** <branch-name>
**Review source:** docs/reviews/<branch>/REVIEW-SUMMARY.md
**Date:** <today's date>
**Total findings:** <count>
**Batches planned:** <count>
```

6. Write `docs/fixes/<branch>/plan.md` using this format:

```markdown
# Fix Batch Plan — <branch>

**Date:** <date>
**Source:** docs/reviews/<branch>/REVIEW-SUMMARY.md
**Total findings:** <count>

## Batch A — Deletes and Removals

| # | Finding | Severity | File | Risk |
|---|---------|----------|------|------|
| 1 | <title> | P1/P2/P3 | `<file>` | Zero — deletion only |

## Batch B — Data Integrity and Hot Path

| # | Finding | Severity | File | Risk |
|---|---------|----------|------|------|
| 1 | <title> | P1/P2/P3 | `<file>` | <specific risk note> |

## Batch C — Code Quality and Abstractions

(same table format)

## Batch D — Deferred

| # | Finding | Severity | File | Why Deferred |
|---|---------|----------|------|-------------|
| 1 | <title> | P2/P3 | `<file>` | <reason> |
```

7. Print a summary table to the console showing the batch plan.
8. **STOP.** Do not begin any fixes. Tell the user:

```
Fix plan written to docs/fixes/<branch>/plan.md

Batch A: <count> findings (deletes, zero risk)
Batch B: <count> findings (data integrity, needs care)
Batch C: <count> findings (code quality, safe refactors)
Batch D: <count> findings (deferred — new deps or features)

Next: Open a new session and run /fix-batched batch1
```

---

## batchN — Execute One Batch (batch1 = A, batch2 = B, batch3 = C, batch4 = D)

Map: batch1 → Batch A, batch2 → Batch B, batch3 → Batch C, batch4 → Batch D.

### Step 1: Read context

- Read `docs/fixes/<branch>/plan.md` to get the findings for this batch.
- Read the relevant source files listed in the plan.
- If a previous batch's result file exists (e.g., `batch1.md` when running batch2), read it for scope changes noted in the three questions.

### Step 2: STOPGAP — Present changes before editing

Before making ANY edits, print:

```
STOPGAP — Batch <letter> (<batch name>)

Files to be modified:
  - <path/to/file.py> (lines X-Y: <what changes>)
  - <path/to/file2.py> (lines X-Y: <what changes>)

Fix ordering:
  1. <fix A> — no dependencies
  2. <fix B> — depends on fix A (explain why)
  3. <fix C> — no dependencies

Proceed? (Y to continue, or give instructions to adjust)
```

Wait for user confirmation before continuing.

### Step 3: Implement fixes

- Make all changes for this batch.
- Run `python3 -m pytest tests/ -v` to verify no regressions.
- Commit with message: `fix: batch <N> — <one-line summary>`
  Append `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` to the commit message.
- Push to origin.

### Step 4: Write batch result file

Write `docs/fixes/<branch>/batchN.md`:

```markdown
# Batch <N> — <Batch Name> Results

**Branch:** <branch>
**Date:** <date>
**Commit:** <short hash>

## Changes Made

### <Finding title>
**File:** `<path>:<lines>`
**What changed:** <description>
**Review finding:** <P-level> — <original description>

---

(repeat per fix)

## Considered but Rejected

- <thing> — <why rejected>

## Deferred to Later Batch

- <thing> — moved to batch <N> because <reason>

## Three Questions

### 1. Hardest fix in this batch?

<answer>

### 2. What did you consider fixing differently, and why didn't you?

<answer>

### 3. Least confident about going into the next batch or compound phase?

<answer>
```

Commit and push the result file separately:
`docs: fix batch <N> results`

### Step 5: STOP

Tell the user:
```
Batch <N> complete. <count> fixes committed as <short hash>.
Results written to docs/fixes/<branch>/batchN.md

Next: Open a new session and run /fix-batched <next-step>
```

---

## close — Write Summary and Update Handoff

### Step 1: Read all batch results

Read all `docs/fixes/<branch>/batchN.md` files that exist.

### Step 2: Write FIXES-SUMMARY.md

Write `docs/fixes/<branch>/FIXES-SUMMARY.md`:

```markdown
# Fix Summary — <branch>

**Date:** <date>
**Batches executed:** <count>
**Total findings fixed:** <count>
**Total findings deferred:** <count>

## Fixed

| # | Finding | Severity | Batch | Commit |
|---|---------|----------|-------|--------|
| 1 | <title> | P1 | A | `<hash>` |

## Deferred

| # | Finding | Severity | Reason |
|---|---------|----------|--------|
| 1 | <title> | P2 | <why> |

## Patterns Worth Capturing

<List any recurring patterns from the three-questions answers that should become
docs/solutions/ entries. Don't create the files — just flag them for a compound
session.>
```

### Step 3: Update HANDOFF.md

- Read `HANDOFF.md` (check project root, then `docs/`).
- Update the "Current phase" line to note fix phase complete.
- Add a brief section noting which batches were executed and the summary location.
- Commit both files: `docs: fix phase complete`
- Push.

Tell the user:
```
Fix phase complete!
  Summary: docs/fixes/<branch>/FIXES-SUMMARY.md
  HANDOFF: updated

Fixed: <count> findings across <batch count> batches
Deferred: <count> findings

Patterns flagged for compound phase: <count or "none">
```
