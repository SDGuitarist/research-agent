-- PF-Intel V1: Initial Schema Migration
-- Run in Supabase Dashboard > SQL Editor
-- Then commit this file to version control
--
-- Creates: 8 tables, RLS policies, triggers, indexes, storage bucket
-- Tables: venues, contacts, events, recordings, jobs, action_items,
--         recording_mentions, entity_corrections

-- =============================================================
-- EXTENSIONS
-- =============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================
-- HELPER FUNCTIONS
-- =============================================================

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Normalize phone to digits only (strips everything except 0-9)
CREATE OR REPLACE FUNCTION normalize_phone()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.phone IS NOT NULL THEN
        NEW.phone_normalized = regexp_replace(NEW.phone, '[^0-9]', '', 'g');
    ELSE
        NEW.phone_normalized = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- TABLES
-- =============================================================

-- 1. VENUES
CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    location TEXT,
    capacity TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. CONTACTS
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    role TEXT,
    organization TEXT,
    phone TEXT,
    phone_normalized TEXT,
    email TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. EVENTS
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE SET NULL,
    date DATE,
    pay TEXT,
    set_details TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. RECORDINGS
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    storage_path TEXT,
    duration_ms INTEGER,
    file_size INTEGER,
    transcript TEXT,
    raw_parse_output JSONB,
    audio_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. JOBS
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    recording_id UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT jobs_status_check CHECK (
        status IN (
            'pending', 'transcribing', 'transcribed',
            'parsing', 'parsed', 'review_ready',
            'completed', 'failed', 'failed_crash'
        )
    )
);

-- 6. ACTION_ITEMS
CREATE TABLE action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    assignee TEXT,
    deadline TEXT,
    priority TEXT DEFAULT 'medium',
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT action_items_priority_check CHECK (
        priority IN ('high', 'medium', 'low')
    )
);

-- 7. RECORDING_MENTIONS
-- Separate nullable FKs instead of polymorphic entity_type + entity_id
-- (polymorphic pattern has no FK integrity in Postgres)
CREATE TABLE recording_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    recording_id UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    action_item_id UUID REFERENCES action_items(id) ON DELETE CASCADE,
    raw_mention TEXT,
    confidence FLOAT,
    source_quote TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recording_mentions_one_entity CHECK (
        (venue_id IS NOT NULL)::int +
        (contact_id IS NOT NULL)::int +
        (event_id IS NOT NULL)::int +
        (action_item_id IS NOT NULL)::int = 1
    ),
    CONSTRAINT recording_mentions_confidence_range CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    )
);

-- 8. ENTITY_CORRECTIONS
-- Separate nullable FKs instead of polymorphic entity_type + entity_id
CREATE TABLE entity_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    recording_id UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    venue_id UUID REFERENCES venues(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    action_item_id UUID REFERENCES action_items(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    ai_value TEXT,
    user_value TEXT,
    correction_type TEXT,
    ai_confidence FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT entity_corrections_one_entity CHECK (
        (venue_id IS NOT NULL)::int +
        (contact_id IS NOT NULL)::int +
        (event_id IS NOT NULL)::int +
        (action_item_id IS NOT NULL)::int = 1
    )
);

-- =============================================================
-- TRIGGERS: updated_at
-- =============================================================

CREATE TRIGGER set_venues_updated_at
    BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_recordings_updated_at
    BEFORE UPDATE ON recordings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_action_items_updated_at
    BEFORE UPDATE ON action_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- TRIGGER: Phone normalization
-- =============================================================

CREATE TRIGGER normalize_contact_phone
    BEFORE INSERT OR UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION normalize_phone();

-- =============================================================
-- INDEXES
-- =============================================================

-- Trigram indexes for fuzzy search
CREATE INDEX idx_contacts_name_trgm ON contacts USING gin (name gin_trgm_ops);
CREATE INDEX idx_venues_name_trgm ON venues USING gin (name gin_trgm_ops);

-- Foreign key lookups
CREATE INDEX idx_venues_user_id ON venues (user_id);
CREATE INDEX idx_contacts_user_id ON contacts (user_id);
CREATE INDEX idx_contacts_venue_id ON contacts (venue_id);
CREATE INDEX idx_contacts_phone_normalized ON contacts (phone_normalized);
CREATE INDEX idx_events_user_id ON events (user_id);
CREATE INDEX idx_events_venue_id ON events (venue_id);
CREATE INDEX idx_recordings_user_id ON recordings (user_id);
CREATE INDEX idx_recordings_event_id ON recordings (event_id);
CREATE INDEX idx_jobs_user_id ON jobs (user_id);
CREATE INDEX idx_jobs_recording_id ON jobs (recording_id);
CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_action_items_user_id ON action_items (user_id);
CREATE INDEX idx_action_items_event_id ON action_items (event_id);
CREATE INDEX idx_recording_mentions_user_id ON recording_mentions (user_id);
CREATE INDEX idx_recording_mentions_recording_id ON recording_mentions (recording_id);
CREATE INDEX idx_entity_corrections_user_id ON entity_corrections (user_id);
CREATE INDEX idx_entity_corrections_recording_id ON entity_corrections (recording_id);

-- =============================================================
-- ROW LEVEL SECURITY
-- =============================================================

-- Enable RLS on all 8 tables
ALTER TABLE venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE recording_mentions ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_corrections ENABLE ROW LEVEL SECURITY;

-- RLS policies use (SELECT auth.uid()) subquery pattern
-- This is evaluated once per query instead of per-row (performance optimization)

-- VENUES
CREATE POLICY "Users select own venues"
    ON venues FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own venues"
    ON venues FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own venues"
    ON venues FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own venues"
    ON venues FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- CONTACTS
CREATE POLICY "Users select own contacts"
    ON contacts FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own contacts"
    ON contacts FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own contacts"
    ON contacts FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own contacts"
    ON contacts FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- EVENTS
CREATE POLICY "Users select own events"
    ON events FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own events"
    ON events FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own events"
    ON events FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own events"
    ON events FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- RECORDINGS
CREATE POLICY "Users select own recordings"
    ON recordings FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own recordings"
    ON recordings FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own recordings"
    ON recordings FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own recordings"
    ON recordings FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- JOBS
CREATE POLICY "Users select own jobs"
    ON jobs FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own jobs"
    ON jobs FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own jobs"
    ON jobs FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own jobs"
    ON jobs FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- ACTION_ITEMS
CREATE POLICY "Users select own action_items"
    ON action_items FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own action_items"
    ON action_items FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own action_items"
    ON action_items FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own action_items"
    ON action_items FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- RECORDING_MENTIONS
CREATE POLICY "Users select own recording_mentions"
    ON recording_mentions FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own recording_mentions"
    ON recording_mentions FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own recording_mentions"
    ON recording_mentions FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own recording_mentions"
    ON recording_mentions FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- ENTITY_CORRECTIONS
CREATE POLICY "Users select own entity_corrections"
    ON entity_corrections FOR SELECT
    USING (user_id = (SELECT auth.uid()));
CREATE POLICY "Users insert own entity_corrections"
    ON entity_corrections FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users update own entity_corrections"
    ON entity_corrections FOR UPDATE
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY "Users delete own entity_corrections"
    ON entity_corrections FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- =============================================================
-- STORAGE: Private recordings bucket
-- =============================================================

-- Create private bucket for audio files
-- 50 MB file size limit, only audio MIME types allowed
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'recordings',
    'recordings',
    FALSE,
    52428800,  -- 50 MB in bytes
    ARRAY['audio/mp4', 'audio/m4a', 'audio/mpeg']
);

-- Storage RLS: users can only access files in their own folder
-- Files stored as: {user_id}/{filename}
-- storage.foldername(name) extracts folder segments from the path

CREATE POLICY "Users upload to own folder"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]
    );

CREATE POLICY "Users read own folder"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]
    );

CREATE POLICY "Users delete from own folder"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]
    );
