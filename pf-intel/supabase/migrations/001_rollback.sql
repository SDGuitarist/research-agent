-- PF-Intel V1: Rollback for 001_initial_schema.sql
-- Drops everything created by the initial migration in reverse order
-- Run in Supabase Dashboard > SQL Editor if you need to start over

-- =============================================================
-- STORAGE: Remove bucket and policies
-- =============================================================

-- Drop storage policies first
DROP POLICY IF EXISTS "Users upload to own folder" ON storage.objects;
DROP POLICY IF EXISTS "Users read own folder" ON storage.objects;
DROP POLICY IF EXISTS "Users delete from own folder" ON storage.objects;

-- Delete the bucket (must be empty first)
-- To empty: DELETE FROM storage.objects WHERE bucket_id = 'recordings';
DELETE FROM storage.buckets WHERE id = 'recordings';

-- =============================================================
-- RLS POLICIES: Drop all (reverse order of tables)
-- =============================================================

-- entity_corrections
DROP POLICY IF EXISTS "Users select own entity_corrections" ON entity_corrections;
DROP POLICY IF EXISTS "Users insert own entity_corrections" ON entity_corrections;
DROP POLICY IF EXISTS "Users update own entity_corrections" ON entity_corrections;
DROP POLICY IF EXISTS "Users delete own entity_corrections" ON entity_corrections;

-- recording_mentions
DROP POLICY IF EXISTS "Users select own recording_mentions" ON recording_mentions;
DROP POLICY IF EXISTS "Users insert own recording_mentions" ON recording_mentions;
DROP POLICY IF EXISTS "Users update own recording_mentions" ON recording_mentions;
DROP POLICY IF EXISTS "Users delete own recording_mentions" ON recording_mentions;

-- action_items
DROP POLICY IF EXISTS "Users select own action_items" ON action_items;
DROP POLICY IF EXISTS "Users insert own action_items" ON action_items;
DROP POLICY IF EXISTS "Users update own action_items" ON action_items;
DROP POLICY IF EXISTS "Users delete own action_items" ON action_items;

-- jobs
DROP POLICY IF EXISTS "Users select own jobs" ON jobs;
DROP POLICY IF EXISTS "Users insert own jobs" ON jobs;
DROP POLICY IF EXISTS "Users update own jobs" ON jobs;
DROP POLICY IF EXISTS "Users delete own jobs" ON jobs;

-- recordings
DROP POLICY IF EXISTS "Users select own recordings" ON recordings;
DROP POLICY IF EXISTS "Users insert own recordings" ON recordings;
DROP POLICY IF EXISTS "Users update own recordings" ON recordings;
DROP POLICY IF EXISTS "Users delete own recordings" ON recordings;

-- events
DROP POLICY IF EXISTS "Users select own events" ON events;
DROP POLICY IF EXISTS "Users insert own events" ON events;
DROP POLICY IF EXISTS "Users update own events" ON events;
DROP POLICY IF EXISTS "Users delete own events" ON events;

-- contacts
DROP POLICY IF EXISTS "Users select own contacts" ON contacts;
DROP POLICY IF EXISTS "Users insert own contacts" ON contacts;
DROP POLICY IF EXISTS "Users update own contacts" ON contacts;
DROP POLICY IF EXISTS "Users delete own contacts" ON contacts;

-- venues
DROP POLICY IF EXISTS "Users select own venues" ON venues;
DROP POLICY IF EXISTS "Users insert own venues" ON venues;
DROP POLICY IF EXISTS "Users update own venues" ON venues;
DROP POLICY IF EXISTS "Users delete own venues" ON venues;

-- =============================================================
-- TABLES: Drop in reverse dependency order
-- =============================================================

DROP TABLE IF EXISTS entity_corrections;
DROP TABLE IF EXISTS recording_mentions;
DROP TABLE IF EXISTS action_items;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS recordings;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS venues;

-- =============================================================
-- FUNCTIONS
-- =============================================================

DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS normalize_phone();

-- Note: pg_trgm extension is NOT dropped (other things may depend on it)
