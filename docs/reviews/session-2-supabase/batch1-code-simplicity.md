# Code Simplicity Reviewer — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** main (commit 67490b7)
**Date:** 2026-02-16
**Agent:** code-simplicity-reviewer

## Findings

### 1. entity_corrections table is premature (YAGNI)
- **Severity:** P1
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:164-184
- **Issue:** Tracks AI vs. user corrections with `ai_value`, `user_value`, `correction_type`, `ai_confidence`. This is a machine-learning feedback loop for a pipeline that doesn't exist yet. No code reads from this table. Classic YAGNI — building optimization infrastructure before the base system works.
- **Suggestion:** Remove entire table. Add in a migration when the correction feedback feature is built (~V2/V3). Saves ~45 lines across both files.

### 2. recording_mentions table is premature (YAGNI)
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:139-160
- **Issue:** Provenance layer linking recordings to parsed entities with confidence and source_quote. Nice-to-have but not a V1 requirement. Core pipeline writes directly to entities. No UI exists for provenance display.
- **Suggestion:** Defer to later migration. `recording_id` FK on recordings/jobs already provides basic traceability. Saves ~40 lines.

### 3. Trigram indexes and pg_trgm extension are premature
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:13, 227-228
- **Issue:** Fuzzy search optimization for a single user with 20-50 venues. `ILIKE '%term%'` is instant at this scale. Adds write overhead and extension dependency.
- **Suggestion:** Remove `CREATE EXTENSION IF NOT EXISTS pg_trgm;` and both `idx_*_trgm` indexes. Add when search feature is built with enough data.

### 4. Phone normalization trigger is premature
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:29-39, 218-220, 234
- **Issue:** Denormalized `phone_normalized` column + trigger for phone search that doesn't exist. Solo user types phones manually.
- **Suggestion:** Remove function, column, trigger, and index. Add when phone search feature is built. Saves ~15 lines.

### 5. RLS policies could use FOR ALL instead of 4 separate per table
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:266-384
- **Issue:** 32 policies (4 per table x 8 tables) all checking `user_id = (SELECT auth.uid())`. `FOR ALL` with `USING` clause works identically when USING and WITH CHECK are the same.
- **Suggestion:** Replace with 8 `FOR ALL` policies. Saves ~90 lines in migration, ~50 in rollback.

### 6. Jobs status has too many states for V1
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:110-116
- **Issue:** 9 status values for a pipeline that doesn't exist yet. `failed` vs `failed_crash` has no consumer. Fine-grained states (`transcribing`/`transcribed`/`parsing`/`parsed`/`review_ready`) may not match actual implementation.
- **Suggestion:** Simplify to `'pending', 'processing', 'completed', 'failed'`. Expand when pipeline is built.

### 7. raw_parse_output JSONB on recordings is speculative
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:95
- **Issue:** Debugging/audit column for parse output that's redundant with structured tables. Encourages unstructured data dumps.
- **Suggestion:** Borderline — keep for debugging but acknowledge it's speculative.

### 8. audio_deleted boolean is premature
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:96
- **Issue:** Storage management feature for a single user who won't hit storage limits for years. No UI for "delete audio but keep transcript."
- **Suggestion:** Remove. Add when storage management feature is built.

### 9. Rollback could use CASCADE to avoid explicit policy drops
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_rollback.sql`:22-68
- **Issue:** 46 lines of explicit policy drops are redundant — `DROP TABLE ... CASCADE` drops all dependent objects.
- **Suggestion:** Use `DROP TABLE IF EXISTS ... CASCADE` and remove explicit policy drops. Saves ~50 lines.

### 10. Excessive foreign key indexes
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:230-247
- **Issue:** 17 indexes for a low-volume V1 app. FK indexes on tables being deferred (recording_mentions, entity_corrections) are wasted. FK indexes on rarely-queried nullable columns add write overhead without proven benefit.
- **Suggestion:** Keep `user_id` indexes (RLS) and `jobs.status`/`jobs.recording_id`. Drop the rest; add when queries are slow.

## What Is Done Well (Keep As-Is)
- `(SELECT auth.uid())` pattern — real Supabase performance optimization
- `updated_at` triggers — cheap, prevents bugs
- `ON DELETE CASCADE` / `SET NULL` choices — correct semantics
- Storage bucket with MIME restrictions and size limit — low-cost defense
- CHECK constraints on jobs.status and action_items.priority — good pattern
- The 6 core tables — all directly serve the pipeline

## Potential Reduction

| Metric | Value |
|--------|-------|
| Current LOC (migration) | 424 |
| Current LOC (rollback) | 90 |
| **Total current** | **514** |
| Est. removable (P1+P2) | ~105 lines |
| Est. removable (P3) | ~140 lines |
| **Potential total reduction** | **~245 lines (~48%)** |

## Summary
- P1 (Critical): 1
- P2 (Important): 3
- P3 (Nice-to-have): 6
