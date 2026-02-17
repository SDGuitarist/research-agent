# Data Integrity Guardian — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** session-2-supabase
**Date:** 2026-02-16
**Agent:** data-integrity-guardian

## Findings

### Cross-user FK references — no tenant isolation on FK columns
- **Severity:** P1
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:46-184
- **Issue:** Every FK relationship (contacts.venue_id, events.venue_id, etc.) references the target table's `id` only — no constraint ensures the referenced row belongs to the same `user_id`. User A could reference User B's venue. In `recording_mentions`/`entity_corrections` with ON DELETE CASCADE, User A deleting their venue could delete User B's mention rows.
- **Suggestion:** Add trigger-based validation that referenced entities belong to the same user_id, or enforce at application layer with documentation.

### CASCADE delete destroys audit history (mentions/corrections)
- **Severity:** P1
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:143-146, 168-171
- **Issue:** ON DELETE CASCADE on entity FK columns in `recording_mentions` and `entity_corrections` means deleting a venue/contact/event/action_item silently destroys all associated mentions and corrections — losing the audit trail of AI extractions and user corrections.
- **Suggestion:** Use ON DELETE SET NULL instead. Relax the `recording_mentions_one_entity` CHECK to allow all-NULL (orphaned but preserved). Consider adding `orphaned BOOLEAN DEFAULT FALSE` for clarity.

### NULL confidence bypasses range constraint
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:148, 157-159
- **Issue:** `confidence FLOAT` allows NULL, which passes the CHECK constraint (PostgreSQL CHECK evaluates to TRUE on NULL). Plan specifies confidence is mandatory. Also, `entity_corrections.ai_confidence` has no range constraint at all.
- **Suggestion:** Add `NOT NULL` to confidence. Add range constraint to `entity_corrections.ai_confidence`.

### TEXT columns for typed data (pay, capacity, deadline)
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:50, 79, 126
- **Issue:** `venues.capacity`, `events.pay`, and `action_items.deadline` are all TEXT. Cannot sort, filter, or validate at DB level. Changing types after production data requires a migration.
- **Suggestion:** Use INTEGER for capacity, NUMERIC(10,2) or INTEGER (cents) for pay, DATE for deadline. Keep raw TEXT columns alongside if needed for original transcription text.

### No transaction wrapper around the migration
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:1-424
- **Issue:** No `BEGIN; ... COMMIT;` wrapper. If any statement fails mid-way, the database is left in an inconsistent state with some tables/indexes created and others not.
- **Suggestion:** Wrap the migration in `BEGIN; ... COMMIT;`. Put `CREATE EXTENSION` before `BEGIN` (some extensions can't be created in transactions).

### Missing FK indexes on entity columns in recording_mentions and entity_corrections
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:222-247
- **Issue:** No indexes on venue_id, contact_id, event_id, or action_item_id in recording_mentions or entity_corrections. These columns have CASCADE deletes — without indexes, deletes require sequential scans and table locks.
- **Suggestion:** Add 8 indexes (4 per table) on the entity FK columns.

### phone_normalized derivation not documented
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:29-39, 66-67
- **Issue:** The trigger correctly overwrites phone_normalized on every INSERT/UPDATE, but it's not obvious from the schema that this column is derived and trigger-protected.
- **Suggestion:** Add a SQL comment or consider GENERATED ALWAYS AS if supported.

### Rollback fails if storage objects exist
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_rollback.sql:16
- **Issue:** The rollback deletes the bucket but does not empty it first. If objects exist, the DELETE will fail due to FK constraints.
- **Suggestion:** Add `DELETE FROM storage.objects WHERE bucket_id = 'recordings';` before the bucket delete.

### Service role RLS bypass undocumented
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:252-384
- **Issue:** The migration doesn't document that Supabase service_role key bypasses RLS entirely. This is by design but should be explicit since this file is the security model source of truth.
- **Suggestion:** Add a comment block explaining the dual-access pattern (client RLS + server service_role bypass).

### Missing storage UPDATE policy
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:401-424
- **Issue:** Storage policies cover INSERT, SELECT, DELETE but not UPDATE. Users cannot update file metadata if ever needed.
- **Suggestion:** Add UPDATE policy if needed, or document that audio files are immutable.

## Summary
- P1 (Critical): 2
- P2 (Important): 4
- P3 (Nice-to-have): 4
