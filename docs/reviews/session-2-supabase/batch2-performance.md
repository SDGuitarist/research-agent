# Performance Oracle — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** session-2-supabase
**Date:** 2026-02-16
**Agent:** performance-oracle

## Findings

### Missing Composite Index on `jobs` for Pipeline Polling
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:241
- **Issue:** Client polls `jobs` by `recording_id` and `status` every 3-5 seconds. Separate single-column indexes exist but no composite index. PostgreSQL can only use one B-tree index per scan.
- **Suggestion:** Add `CREATE INDEX idx_jobs_recording_status ON jobs (recording_id, status);`. Drop standalone `idx_jobs_recording_id` since composite covers it.

### Missing Index on `events.date` for Chronological Queries
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:78
- **Issue:** No index on `events.date`. Sorting by date, filtering date ranges ("last 90 days") will require sequential scans.
- **Suggestion:** Add `CREATE INDEX idx_events_date ON events (date);`

### Missing Partial Index on `action_items.completed`
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:128
- **Issue:** "Show open action items" query has no index support. Boolean columns have low selectivity for standard B-tree.
- **Suggestion:** Add partial index: `CREATE INDEX idx_action_items_open ON action_items (user_id) WHERE completed = FALSE;`

### N+1 Query Risk on Review Screen
- **Severity:** P2
- **File:** Schema-wide concern
- **Issue:** Loading recording → mentions → entity per mention is a classic N+1 pattern. With 10 mentions, that's 12 queries instead of 1.
- **Suggestion:** Application-layer concern. Document JOIN query pattern for FastAPI sessions. Schema already supports efficient JOINs (all FKs indexed).

### `raw_parse_output` JSONB Column Without Index (correct)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:95
- **Issue:** No GIN index on JSONB column. This is correct — column is for debugging, not querying. Adding index would waste write I/O.
- **Suggestion:** Do not add index now. Add `jsonb_path_ops` GIN index later only if query patterns emerge.

### `recordings.file_size` is INTEGER (max ~2.1 GB)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:93
- **Issue:** 50 MB bucket limit makes this safe. Would overflow only if limit raised above 2.1 GB.
- **Suggestion:** Keep as INTEGER. Revisit only if bucket limit changes.

### TEXT columns for pay/capacity (correct for voice data)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:79,52
- **Issue:** TEXT prevents numeric sorting/filtering. Correct choice for AI-extracted unstructured data.
- **Suggestion:** Keep TEXT. Add typed companion columns in V2 if needed.

### Storage RLS uses `storage.foldername()` function
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:405-424
- **Issue:** Function call on every row prevents simple index pushdown. Fine at current scale, could slow at 10,000+ files.
- **Suggestion:** No change needed. Standard Supabase pattern. Monitor if scale increases.

### Trigram indexes at small scale (correct decision)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:227-228
- **Issue:** GIN trigram indexes are larger than B-tree (3-5x) and slower to update. At 50-200 rows, seq scan might be faster. But overhead is immeasurable at this scale.
- **Suggestion:** Keep them. Enables fuzzy matching from day one. Write overhead is zero in practice.

## Positive Findings

- `(SELECT auth.uid())` optimization correctly applied — stable scalar subquery evaluated once per query.
- Trigger overhead is negligible — `NOW()` assignment and `regexp_replace` are sub-microsecond.
- FK index coverage is complete — every FK column has a corresponding index.
- Rollback script is correct with proper reverse dependency order.

## Summary
- P1 (Critical): 0
- P2 (Important): 4
- P3 (Nice-to-have): 5
