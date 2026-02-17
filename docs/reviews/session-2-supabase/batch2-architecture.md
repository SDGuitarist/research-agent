# Architecture Strategist — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** session-2-supabase
**Date:** 2026-02-16
**Agent:** architecture-strategist

## Findings

### Missing UNIQUE constraint on `jobs.recording_id`
- **Severity:** P1
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:105
- **Issue:** Plan ERD declares `RECORDINGS ||--|| JOBS` (one-to-one), but SQL has no UNIQUE constraint on `recording_id`. Multiple jobs could reference the same recording, causing ambiguity on status queries.
- **Suggestion:** Add `UNIQUE` to the column: `recording_id UUID NOT NULL UNIQUE REFERENCES recordings(id) ON DELETE CASCADE`

### Cross-user FK references not validated
- **Severity:** P1 (acceptable for V1, document it)
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:61
- **Issue:** `contacts.venue_id` references `venues(id)` with no requirement that the venue belongs to the same user. Same applies to `events.venue_id`, `recordings.event_id`, `action_items.event_id`, and all FK columns in `recording_mentions` and `entity_corrections`. FK checks bypass RLS.
- **Suggestion:** Document as known V1 limitation. For multi-user V2, add trigger-based ownership validation.

### `events` table has no title/name column
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:78
- **Issue:** Only identifying field is `date` (nullable). Events with all-null fields have no human-readable identifier for the review UI.
- **Suggestion:** Add `title TEXT` column. Parsing service can auto-generate titles like "Gig at The Blue Note".

### `file_size` column is INTEGER (max ~2.1 GB)
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:93
- **Issue:** `file_size INTEGER` caps at ~2.1 GB. Currently safe (50 MB bucket limit), but a latent risk if limit is raised.
- **Suggestion:** Use `BIGINT` instead. No practical storage cost difference at this scale.

### Missing CHECK on `entity_corrections.correction_type`
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:175
- **Issue:** No CHECK constraint or defined enum for `correction_type`. Inconsistent values undermine correction pattern analysis.
- **Suggestion:** Add `CONSTRAINT entity_corrections_type_check CHECK (correction_type IN ('edit', 'dismiss', 'add'))`

### Missing CHECK on `entity_corrections.ai_confidence`
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:176
- **Issue:** `recording_mentions` validates confidence range 0-1, but `entity_corrections.ai_confidence` has no equivalent constraint. Inconsistency between parallel tables.
- **Suggestion:** Add `CONSTRAINT entity_corrections_confidence_range CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0)`

### Missing storage UPDATE policy decision
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:401-424
- **Issue:** Storage has INSERT, SELECT, DELETE policies but no UPDATE. If files are immutable, document it. If not, add the policy.
- **Suggestion:** Add comment or UPDATE policy depending on intent.

### `recording_mentions`/`entity_corrections` mutability unclear
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:186-212
- **Issue:** Neither table has `updated_at`, but both have UPDATE RLS policies. If immutable audit logs, remove UPDATE/DELETE policies. If mutable, add `updated_at`.
- **Suggestion:** Choose immutable (remove UPDATE policies) or mutable (add `updated_at`).

### TEXT columns for capacity/pay/deadline (intentional trade-offs)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:50,79,126
- **Issue:** `capacity`, `pay`, `deadline` are TEXT. Prevents numeric sorting/filtering. Defensible for voice-transcribed data.
- **Suggestion:** Keep TEXT for V1. Add typed companion columns in V2 if needed.

### `audio/m4a` MIME type is non-standard
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:398
- **Issue:** `audio/m4a` is not an IANA-registered MIME type. Official type is `audio/mp4` (already included) or `audio/x-m4a`.
- **Suggestion:** Add `audio/x-m4a` to the allowed list for safety.

### Plan ERD diverges from implementation
- **Severity:** P3
- **File:** docs/plans/ (ERD section)
- **Issue:** Plan ERD shows `entity_type + entity_id` but implementation correctly uses separate nullable FKs. Documentation is now stale.
- **Suggestion:** Update ERD in plan to reflect actual implementation.

### Rollback script style (indexes/triggers not explicitly listed)
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_rollback.sql`:70-81
- **Issue:** Indexes and triggers are implicitly dropped with tables. Functionally correct but inconsistent with explicit policy drops.
- **Suggestion:** Add comment noting implicit drops. No code change needed.

## Positive Findings

- **Polymorphic avoidance pattern** — Separate nullable FKs with CHECK constraint is the correct architectural choice for referential integrity.
- **`(SELECT auth.uid())` optimization** — Correctly applied across all 32 RLS policies.
- **Proper normalization** — 3NF throughout, no unnecessary denormalization.
- **Rollback script** — Functionally correct, reverse dependency order.

## Summary
- P1 (Critical): 2 (UNIQUE constraint, cross-user FK)
- P2 (Important): 4
- P3 (Nice-to-have): 5
