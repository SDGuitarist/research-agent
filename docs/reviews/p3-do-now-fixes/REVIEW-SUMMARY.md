# Code Review Summary

**PR:** P3 "Do Now" Fixes (#25, #26, #28, #29, #30)
**Branch:** main (direct commits: 8ecfdb3, e647405, 9dde2c4, 8420227)
**Date:** 2026-02-23
**Agents Used:** kieran-python-reviewer, pattern-recognition-specialist, code-simplicity-reviewer, architecture-strategist, security-sentinel, performance-oracle, data-integrity-guardian, git-history-analyzer, agent-native-reviewer

## P1 — Critical (Blocks Merge)

None. All four commits are correct, well-scoped fixes.

> The pattern-recognition agent flagged the wrong function name in a comment as P1. Downgraded to P2 in synthesis — a misleading comment is important to fix but does not block merge.

## P2 — Important (Should Fix)

### 1. Sanitization contract is undocumented and inconsistent across modules
- **Source Agents:** kieran-python, pattern-recognition, code-simplicity, architecture, security (5 of 9 agents flagged aspects of this)
- **Files:** relevance.py:122, decompose.py:141, synthesize.py:413,497
- **Issue:** The removal of `sanitize_content()` calls from `decompose.py` and `relevance.py` creates an inconsistent convention: these two modules now trust the caller to pre-sanitize, but `synthesize.py` still double-sanitizes. The contract is documented only by a comment in `relevance.py:122` — which references a nonexistent function (`score_and_filter_sources` instead of `evaluate_sources`). `decompose.py` has no comment at all. The `score_source` docstring still says "original research query" when it now expects pre-sanitized input.
- **Fix:** Three small changes:
  1. Fix the comment at `relevance.py:122` → `# query is pre-sanitized by caller (evaluate_sources)`
  2. Add comment in `decompose.py:141` → `# critique_guidance is pre-sanitized by load_critique_history`
  3. Update `score_source` docstring to note the pre-sanitization precondition
- **Note:** Whether to also remove the double-sanitization in `synthesize.py` (for consistency) or restore it in `decompose.py`/`relevance.py` (for defense-in-depth) is a design decision. The data-integrity agent confirmed `sanitize_content` is NOT idempotent (`&` → `&amp;` → `&amp;amp;`), so double-sanitizing is actually a bug, not defense. Removing from `synthesize.py` is the correct path.

### 2. Plan document is uncommitted, breaking traceability
- **Source Agent:** git-history-analyzer
- **File:** docs/plans/2026-02-23-p3-do-now-fixes-plan.md
- **Issue:** The plan document is untracked in git. The four commits reference issues #25-#30 defined in this plan. If the file is lost, the rationale (particularly the sanitization data-flow analysis) becomes unrecoverable. Breaks the compound engineering traceability chain.
- **Fix:** `git add docs/plans/2026-02-23-p3-do-now-fixes-plan.md && git commit`

## P3 — Nice-to-Have

### 3. `safe_adjustments` variable name misleading after sanitize removal
- **Source Agent:** code-simplicity-reviewer
- **File:** relevance.py:136
- **Issue:** Variable still named `safe_adjustments` but only truncation happens at this site — no sanitization.
- **Fix:** Rename to `adjustments` or `truncated_guidance`.

### 4. Bool-as-int pattern also exists in schema.py
- **Source Agent:** data-integrity-guardian
- **File:** research_agent/schema.py:94
- **Issue:** `priority` field validation uses `isinstance(priority, int)` without bool guard. `priority: true` in YAML would pass as integer 1.
- **Fix:** Add `isinstance(priority, bool)` check before int check, same as context.py fix.

### 5. score_source is public but has undocumented preconditions
- **Source Agents:** architecture-strategist, data-integrity-guardian
- **File:** relevance.py:108
- **Issue:** Module-level function now requires pre-sanitized query, but naming and signature don't signal this.
- **Fix:** Consider renaming to `_score_source` in a future session.

### 6. Missing test for `False` as score value
- **Source Agent:** data-integrity-guardian
- **File:** tests/test_context.py
- **Issue:** New test covers `True` but not `False`. While `False` (int 0) fails range check anyway, explicit test documents intent.
- **Fix:** Add `test_bool_false_rejected_as_score` in a future session.

### 7. String-based mode dispatch (pre-existing)
- **Source Agents:** pattern-recognition, architecture-strategist
- **File:** research_agent/agent.py:146, 203, 208, 215, 458, 480
- **Issue:** Mode identity checked via `self.mode.name == "quick"` in 6+ places. Pre-existing pattern, not introduced by these commits. New commit adds another instance.
- **Fix:** Future: boolean properties on ResearchMode (e.g., `mode.has_critique`).

### 8. Missing issue reference in commit subject
- **Source Agent:** git-history-analyzer
- **File:** commit 8420227
- **Issue:** Subject line omits `(#26, #30)`. `git log --grep="#26"` won't find it.
- **Fix:** Note for future commits. No retroactive fix.

### 9. Three commits lack dedicated tests
- **Source Agent:** git-history-analyzer
- **Issue:** Only 8ecfdb3 adds a test. Quick-mode guard (e647405) has no negative test. Plan explicitly says "no test needed" for each, acceptable for these sizes.
- **Fix:** Consider adding quick-mode guard test in a future session.

### 10. Positive findings (no action needed)
- **Performance:** Quick mode skip saves 10-50ms disk I/O; query sanitization hoisting reduces O(N) to O(1) (performance-oracle)
- **Data integrity:** Removed double-sanitization actually fixes a latent `&amp;amp;` encoding bug (data-integrity-guardian)
- **Agent-native:** All changes maintain full agent parity, 11/12 capabilities accessible (agent-native-reviewer)

## Statistics

| Severity | Count |
|----------|-------|
| P1 Critical | 0 |
| P2 Important | 2 |
| P3 Nice-to-have | 8 (+ 3 positive/info) |
| **Total** | **10** (excluding positives) |

## Agents & Batches

| Batch | Agents | Findings |
|-------|--------|----------|
| batch1 | kieran-python, pattern-recognition, code-simplicity | 10 raw (3 unique after dedup) |
| batch2 | architecture, security, performance | 7 raw (4 unique after dedup) |
| batch3 | data-integrity, git-history, agent-native | 9 raw (5 unique after dedup) |

## Three Questions

1. **Hardest judgment call in this review?** Downgrading the pattern-recognition agent's P1 (wrong function name in comment) to P2. A misleading comment about a security contract is genuinely important — it could cause a future developer to skip sanitization — but it doesn't block merge because the code itself is correct and all tests pass.

2. **What did you consider flagging but chose not to, and why?** The architecture agent's suggestion to restore redundant `sanitize_content()` calls for defense-in-depth. The data-integrity agent proved that double-sanitization is actually a *bug* (non-idempotent encoding), so the "defense-in-depth" argument doesn't hold — the second layer actively corrupts data. The correct fix is to remove the remaining double-sanitization in `synthesize.py`, not to re-add it elsewhere.

3. **What might this review have missed?** Integration-level prompt injection testing. All agents verified the sanitization data flow by reading code, but none actually tested whether injecting `<system>` or `</critique_guidance>` into a YAML weakness field would escape the XML boundary in a live prompt. The unit tests mock the LLM call, so this class of attack is only catchable through manual or integration testing.
