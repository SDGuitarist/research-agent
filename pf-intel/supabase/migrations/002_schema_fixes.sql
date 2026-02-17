-- PF-Intel V1: Schema Fixes from Code Review
-- Addresses review findings #2, #3, #5, #6, #7, #10
-- Run in Supabase Dashboard > SQL Editor after 001_initial_schema.sql
--
-- ACCESS PATTERN:
-- Mobile client uses anon_key + JWT → RLS policies enforce user_id ownership.
-- FastAPI backend uses service_role_key → bypasses RLS by design.
-- This is intentional: the AI pipeline (Whisper, Claude parsing, job status
-- updates) runs server-side with no user JWT. The service_role key gives it
-- full table access without needing per-operation RLS exceptions.

-- =============================================================
-- FIX #3: UNIQUE constraint on jobs.recording_id
-- Plan ERD declares RECORDINGS ||--|| JOBS (one-to-one).
-- Without UNIQUE, multiple jobs could reference the same recording.
-- =============================================================

ALTER TABLE jobs
    ADD CONSTRAINT jobs_recording_id_unique UNIQUE (recording_id);

-- =============================================================
-- FIX #5: CHECK on entity_corrections.correction_type
-- 5 review agents flagged this — free-form TEXT with no validation.
-- =============================================================

ALTER TABLE entity_corrections
    ADD CONSTRAINT entity_corrections_correction_type_check CHECK (
        correction_type IN (
            'accepted', 'edited', 'dismissed',
            'reassigned', 'created', 'merged'
        )
    );

-- =============================================================
-- FIX #6: CHECK on entity_corrections.ai_confidence
-- recording_mentions.confidence has a range constraint but
-- entity_corrections.ai_confidence does not. Fixing inconsistency.
-- =============================================================

ALTER TABLE entity_corrections
    ADD CONSTRAINT entity_corrections_ai_confidence_range CHECK (
        ai_confidence >= 0.0 AND ai_confidence <= 1.0
    );

-- =============================================================
-- FIX #10: CHECK on recordings.duration_ms and file_size
-- Negative values should not be silently accepted.
-- =============================================================

ALTER TABLE recordings
    ADD CONSTRAINT recordings_duration_ms_check CHECK (duration_ms >= 0);

ALTER TABLE recordings
    ADD CONSTRAINT recordings_file_size_check CHECK (file_size >= 0);

-- =============================================================
-- FIX #7: Missing storage UPDATE policy
-- Storage RLS covered INSERT/SELECT/DELETE but not UPDATE.
-- Users may need to update metadata on their own files.
-- =============================================================

CREATE POLICY "Users update own folder"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]
    )
    WITH CHECK (
        bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]
    );
