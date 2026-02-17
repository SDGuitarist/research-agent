# Kieran Python Reviewer — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** main (commit 67490b7)
**Date:** 2026-02-16
**Agent:** kieran-python-reviewer

## Findings

### 1. Missing CHECK constraints on duration_ms and file_size
- **Severity:** P1
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:92-93
- **Issue:** `duration_ms INTEGER` and `file_size INTEGER` lack CHECK constraints. A negative file size or negative duration would be silently accepted.
- **Suggestion:** Add `CHECK (duration_ms > 0)` and `CHECK (file_size > 0)`.

### 2. `capacity` on venues is TEXT but should be INTEGER
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:51
- **Issue:** Discovery doc lists "Capacity" as "Number". TEXT prevents range queries, sorting, aggregation, and invites inconsistent entries.
- **Suggestion:** Change to `INTEGER CHECK (capacity > 0)`. Add `capacity_notes TEXT` if freeform is needed.

### 3. `pay` on events is TEXT but should be numeric
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:79
- **Issue:** Monetary value stored as TEXT prevents aggregation ("total revenue this quarter").
- **Suggestion:** Use `NUMERIC(10, 2) CHECK (pay >= 0)`. Add `pay_notes TEXT` for complex cases.

### 4. `deadline` on action_items is TEXT instead of DATE
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:126
- **Issue:** Cannot query "show overdue action items" or sort chronologically with TEXT.
- **Suggestion:** Change to `DATE`. Have AI parser output ISO dates.

### 5. `events.date` should be TIMESTAMPTZ, not DATE
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:78
- **Issue:** Events have a time component. `DATE` loses time-of-day. Also `date` is a SQL reserved word.
- **Suggestion:** Rename to `event_date TIMESTAMPTZ`.

### 6. Missing recording_id FK on action_items
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:120-134
- **Issue:** Cannot trace action items back to the recording that generated them. Essential for the review UI.
- **Suggestion:** Add `recording_id UUID REFERENCES recordings(id) ON DELETE SET NULL` and corresponding index.

### 7. Missing confidence range CHECK on entity_corrections.ai_confidence
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:176
- **Issue:** `recording_mentions.confidence` has range constraint but `entity_corrections.ai_confidence` does not. Inconsistency.
- **Suggestion:** Add `CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0)`.

### 8. Missing correction_type CHECK constraint
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:175
- **Issue:** Enumerable field without CHECK constraint, unlike `jobs.status` and `action_items.priority`.
- **Suggestion:** Add CHECK with known values, or document that it's intentionally unconstrained for V1.

### 9. Missing updated_at on recording_mentions and entity_corrections
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:186-212
- **Issue:** 6 tables get `updated_at` triggers. 2 tables don't even have the column. Omission looks like a mistake.
- **Suggestion:** Either add `updated_at` + trigger, or document as "intentionally append-only."

### 10. FLOAT should be explicit (REAL or NUMERIC)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:148, 176
- **Issue:** `FLOAT` without precision is implementation-defined. Ambiguous alias.
- **Suggestion:** Use `REAL` (approximate) or `NUMERIC(3, 2)` (exact 0.00-1.00).

### 11. Storage bucket `audio/m4a` is not a registered MIME type
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:398
- **Issue:** `audio/m4a` is not a registered IANA MIME type. Correct type for .m4a is `audio/mp4` or `audio/x-m4a`.
- **Suggestion:** Replace with `audio/x-m4a`. Consider adding `audio/wav` and `audio/webm` for Android.

### 12. Missing storage UPDATE policy
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:401-424
- **Issue:** Storage RLS covers INSERT/SELECT/DELETE but not UPDATE. File replacement requires delete+reinsert (non-atomic).
- **Suggestion:** Add UPDATE policy, or document why updates are blocked.

### 13. Rollback does not drop indexes or triggers explicitly
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_rollback.sql`:70-81
- **Issue:** Indexes/triggers dropped implicitly by DROP TABLE. Inconsistent with explicit policy drops.
- **Suggestion:** Add comment explaining implicit cleanup.

### 14. Rollback missing storage UPDATE policy drop
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_rollback.sql`:10-12
- **Issue:** If UPDATE policy is added, rollback needs corresponding DROP.
- **Suggestion:** Keep rollback in sync with migration.

### 15. Schema is leaner than discovery document (informational)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:46-184
- **Issue:** V1 has minimal columns vs. discovery doc's full spec. Intentional but undocumented.
- **Suggestion:** Document "V1 ships minimal; additional fields come in migration 002."

## Summary
- P1 (Critical): 1
- P2 (Important): 6
- P3 (Nice-to-have): 8
