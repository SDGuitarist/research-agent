# PR Metadata

**Commit:** 67490b7
**Title:** feat(session-2): supabase schema, auth, and storage
**Branch:** main (direct commit)
**Date:** 2026-02-16

## Description

Initial SQL migration with all 8 tables (venues, contacts, events,
recordings, jobs, action_items, recording_mentions, entity_corrections),
RLS policies on every table using (SELECT auth.uid()) optimization,
private storage bucket with MIME/size limits, storage RLS, pg_trgm
indexes, phone normalization trigger, updated_at triggers, CHECK
constraints, and rollback script.

## Files Changed

- `pf-intel/supabase/migrations/001_initial_schema.sql` (424 lines added)
- `pf-intel/supabase/migrations/001_rollback.sql` (90 lines added)
