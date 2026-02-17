# Pattern Recognition Specialist — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** main (commit 67490b7)
**Date:** 2026-02-16
**Agent:** pattern-recognition-specialist

## Positive Patterns Identified

- **Nullable-FK over polymorphic** for recording_mentions/entity_corrections — correct PostgreSQL pattern with FK integrity
- **(SELECT auth.uid()) optimization** — evaluates once per query instead of per-row
- **Consistent primary keys** — every table uses `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- **Uniform user_id column** — enables clean multi-tenant RLS pattern
- **Naming conventions** — highly consistent across all 424 lines (see analysis below)

## Naming Convention Analysis

| Element | Convention | Adherence |
|---------|-----------|-----------|
| Tables | snake_case, plural | 8/8 (100%) |
| Columns | snake_case | All (100%) |
| Indexes | idx_{table}_{column(s)} | 17/17 (100%) |
| Triggers | set_{table}_updated_at | 7/7 (100%) |
| RLS policies | "Users {verb} own {table}" | 32/32 (100%) |
| CHECK constraints | {table}_{field}_check | 4/4 (100%) |

## Findings

### 1. Missing CHECK on entity_corrections.correction_type
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:175
- **Issue:** Free-form TEXT with no CHECK constraint, unlike `jobs.status` and `action_items.priority`.
- **Suggestion:** Add CHECK constraint with known values, or add `NOT NULL` at minimum.

### 2. Missing confidence range CHECK on entity_corrections.ai_confidence
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:176
- **Issue:** `recording_mentions.confidence` has range constraint but `entity_corrections.ai_confidence` does not.
- **Suggestion:** Add matching `CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0)`.

### 3. capacity and pay are TEXT instead of numeric types
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:50, 79
- **Issue:** Prevents range queries, sorting, aggregation. Invites formatting inconsistency.
- **Suggestion:** Use INTEGER for capacity, NUMERIC(10,2) for pay. Or add companion numeric columns.

### 4. action_items.deadline is TEXT instead of DATE
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:126
- **Issue:** Prevents time-based queries. `events.date` is typed as DATE but deadline is not.
- **Suggestion:** Change to DATE or TIMESTAMPTZ.

### 5. action_items.assignee is TEXT instead of FK to contacts
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:125
- **Issue:** No referential integrity, name variants will fragment queries.
- **Suggestion:** Add optional `assignee_contact_id UUID REFERENCES contacts(id)` alongside TEXT.

### 6. file_size INTEGER overflows at 2 GB
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:93
- **Issue:** INTEGER max ~2.1 GB. If bucket limit is raised, column overflows.
- **Suggestion:** Use BIGINT. Zero-cost change now, prevents painful migration later.

### 7. RLS policies copy-pasted 8 times (112 lines of duplication)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:266-384
- **Issue:** 32 policies with only table name varying. Risk of silent typo propagation.
- **Suggestion:** Consider PL/pgSQL loop, or accept explicit form for auditability. Mark as "consider for future."

### 8. updated_at trigger omission undocumented
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:190-212
- **Issue:** 6 tables get triggers, 2 don't. No comment explaining the exclusion.
- **Suggestion:** Add comment: "recording_mentions and entity_corrections are append-only (no updated_at)."

### 9. Missing storage UPDATE policy
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:401-424
- **Issue:** INSERT/SELECT/DELETE covered but not UPDATE. File replacement requires non-atomic delete+reinsert.
- **Suggestion:** Add UPDATE policy or document intentional omission.

### 10. Rollback does not explicitly drop indexes/triggers
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_rollback.sql`:70-81
- **Issue:** Implicit cleanup via DROP TABLE. Inconsistent with explicit policy drops.
- **Suggestion:** Add explanatory comment.

### 11. events.date column name shadows reserved word
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:78
- **Issue:** `date` as column name with DATE type creates ambiguity in queries.
- **Suggestion:** Rename to `event_date`.

### 12. Nullable-FK scaling threshold undocumented
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:139-184
- **Issue:** Pattern works for 4 entity types. At 8+, tables get wide with mostly-NULL columns.
- **Suggestion:** Document threshold. "At 6+ entity types, consider junction-table approach."

### 13. CASCADE vs SET NULL strategy undocumented
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:48-171
- **Issue:** Two FK deletion strategies used correctly but reasoning not documented.
- **Suggestion:** Add header comment explaining the strategy.

## Summary
- P1 (Critical): 0
- P2 (Important): 5
- P3 (Nice-to-have): 8
