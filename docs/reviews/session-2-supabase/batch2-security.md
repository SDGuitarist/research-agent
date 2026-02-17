# Security Sentinel — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** session-2-supabase
**Date:** 2026-02-16
**Agent:** security-sentinel

## Findings

### Hardcoded Secrets Committed to Version Control
- **Severity:** P1
- **File:** `pf-intel/server/.env`:1-4
- **Issue:** The `.env` file contains Supabase URL, anon key, service role key, and JWT secret committed to git. The service role key bypasses all RLS policies. The JWT secret allows forging authentication tokens.
- **Suggestion:** (1) Rotate all secrets in Supabase dashboard immediately. (2) `git rm --cached pf-intel/server/.env`. (3) Add to `.gitignore`. (4) Consider `git filter-repo` to purge from history. (5) Create `.env.example` with placeholders.

### No Storage UPDATE Policy
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:405-424
- **Issue:** Storage policies cover INSERT, SELECT, DELETE but not UPDATE. If another service adds a permissive UPDATE policy on `storage.objects`, it could apply to this bucket too.
- **Suggestion:** Add explicit UPDATE policy scoped to `recordings` bucket with USING and WITH CHECK clauses.

### PII Stored in Plain Text
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:65-67
- **Issue:** `contacts` stores `phone`, `phone_normalized`, `email` in plain TEXT. Visible to anyone with database-level access (service role key, backups, dashboard).
- **Suggestion:** Acceptable for V1 single-tenant if service role key is secured. Plan for application-level encryption in V2.

### Transcripts and Raw AI Output Without Size Limits
- **Severity:** P2
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:94-95
- **Issue:** `transcript` (TEXT) and `raw_parse_output` (JSONB) have no length constraints. Malicious or buggy client could insert arbitrarily large content causing storage bloat and slow queries.
- **Suggestion:** Add CHECK constraints: `length(transcript) <= 500000` and `pg_column_size(raw_parse_output) <= 1048576`.

### `CREATE OR REPLACE FUNCTION` Can Silently Overwrite
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:20,29
- **Issue:** `CREATE OR REPLACE` silently overwrites existing functions with the same name. Could cause subtle breakage if another migration defines the same function.
- **Suggestion:** Use project-prefixed names (e.g., `pf_update_updated_at_column()`) or use `CREATE FUNCTION` (without REPLACE) for initial migration.

### Missing CHECK Constraints on Free-Text Enum Fields
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:175
- **Issue:** `entity_corrections.correction_type` has no CHECK constraint. Allows inconsistent values.
- **Suggestion:** Add CHECK constraint with defined enum values.

### No Email Format Validation
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:67
- **Issue:** `contacts.email` accepts any TEXT value with no format validation.
- **Suggestion:** Add minimal regex CHECK constraint for basic email format.

### `ON DELETE CASCADE` from `auth.users` Deletes All User Data
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:48 (and all tables)
- **Issue:** If a user is deleted from `auth.users`, ALL data across all 8 tables is immediately and irrecoverably deleted. No soft-delete, no grace period.
- **Suggestion:** Consider `ON DELETE RESTRICT` or soft-delete pattern. At minimum ensure automated backups.

### Storage Policies Don't Restrict Filename Characters
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:405-424
- **Issue:** No restriction on filename characters. Special characters or path traversal sequences in filenames could cause downstream issues.
- **Suggestion:** Add filename pattern check in INSERT policy: `name ~ '^[0-9a-f-]+/[a-zA-Z0-9._-]+$'`

### `audio/m4a` Is Not a Standard MIME Type
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:398
- **Issue:** `audio/m4a` is not IANA-registered. Correct type is `audio/mp4` or `audio/x-m4a`.
- **Suggestion:** Replace with standard MIME types and add common variants like `audio/x-m4a`, `audio/aac`.

### No `FORCE ROW LEVEL SECURITY` for Table Owners
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:254-261
- **Issue:** Table owner (postgres role) bypasses RLS by default. Any service-role code bypasses all policies.
- **Suggestion:** Not needed for V1 client-only access. Add `FORCE ROW LEVEL SECURITY` if backend Edge Functions are added.

### Cross-User FK References Not Validated
- **Severity:** P3
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:61,77,90
- **Issue:** FK constraints don't enforce same `user_id`. User A could reference User B's entities. FK checks bypass RLS.
- **Suggestion:** Single-user V1 is not exploitable. Add trigger-based ownership validation for multi-user V2.

## Positive Findings

- RLS on all 8 tables with per-operation policies — thorough coverage.
- `(SELECT auth.uid())` optimization correctly applied everywhere.
- Private storage bucket with MIME type and file size restrictions.
- CHECK constraints on `jobs.status` and `action_items.priority`.
- One-entity CHECK constraint enforces exactly one FK non-null.
- Reverse-order rollback script handles dependency chains correctly.

## Summary
- P1 (Critical): 1
- P2 (Important): 3
- P3 (Nice-to-have): 8
