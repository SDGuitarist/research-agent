# Review Summary Template

Use this for new written reviews.

## Naming Rule

Store new review summaries at:
- `docs/reviews/[branch-or-cycle]/REVIEW-SUMMARY.md`

Keep legacy review filenames as-is unless you are intentionally migrating references.

## Review Metadata

- Branch:
- Base:
- Date:
- Scope:
- Checks run:

## Findings

List findings first, ordered by severity.

### [P1/P2/P3] Title

- Files:
- Risk:
- Why it matters:
- Suggested fix:

## What Was Not Reviewed Or Verified

- Item:
- Why:

## Suggested Fix Order

1. Fix:
2. Fix:
3. Fix:

## Claude Code Fix Prompt

```text
Read HANDOFF.md, CLAUDE.md, and docs/reviews/CODEX-REVIEW-GATE.md. Fix the review findings in [files]. Keep scope limited to the listed findings. Run `python3 -m pytest tests/ -v` and call out any skipped live or integration verification.
```
