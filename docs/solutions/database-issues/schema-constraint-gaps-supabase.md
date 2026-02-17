---
title: "Schema Constraint Gaps — ERD Promises Not Enforced in SQL"
date: 2026-02-16
category: database-issues
tags:
  - supabase
  - schema
  - constraints
  - rls
  - code-review
  - postgresql
module: pf-intel/supabase
symptoms: |
  Initial schema migration compiles and runs without errors but silently
  allows invalid data: duplicate jobs per recording, out-of-range confidence
  values, negative file sizes, unconstrained enum columns, and missing
  storage UPDATE policy. No runtime errors — the problems are invisible
  until bad data is already stored.
severity: P1-P2
summary: >
  ERD and plan documents declared relationships and value ranges that the SQL
  migration did not enforce. Multi-agent review (9 agents, 92 raw findings →
  38 deduplicated) caught 5 fixable constraint gaps and 1 missing storage
  policy. Fixed via a follow-up migration (002_schema_fixes.sql) adding
  UNIQUE, CHECK, and RLS UPDATE constraints.
---

## Problem

After implementing `001_initial_schema.sql` for PF-Intel V1, the schema
compiled and ran without errors in Supabase. However, a multi-agent code
review revealed that several plan-level guarantees were not enforced:

1. **UNIQUE on jobs.recording_id** — Plan ERD declared `RECORDINGS ||--|| JOBS`
   (one-to-one), but the FK had no UNIQUE constraint. Multiple jobs could
   reference the same recording, breaking status polling.

2. **CHECK on entity_corrections.correction_type** — Free-form TEXT column with
   no validation, unlike `jobs.status` which had a CHECK. 5 of 9 review agents
   flagged this inconsistency.

3. **CHECK on entity_corrections.ai_confidence** — `recording_mentions.confidence`
   had a 0.0–1.0 range constraint but the sibling column `ai_confidence` did not.
   4 agents flagged this.

4. **CHECK on recordings.duration_ms and file_size** — Negative values would be
   silently accepted. No runtime error, just bad data.

5. **Missing storage UPDATE policy** — RLS covered INSERT/SELECT/DELETE but not
   UPDATE. Users could not update metadata on their own files.

## Root Cause

**Translation gap between design artifacts and SQL implementation.** The plan
document specified relationships, value ranges, and access patterns in prose and
ERD notation, but when writing the SQL migration, those constraints were not
systematically verified against the design.

Contributing factors:
- Writing one large migration (424 lines) makes it easy to lose consistency
  across similar columns (confidence in one table but not another)
- ERD cardinality notation (`||--||`) doesn't automatically translate to SQL
  constraints — you must manually add UNIQUE for one-to-one
- Storage policies are separate from table RLS and easy to forget one CRUD
  operation

## Solution

Created `002_schema_fixes.sql` as a follow-up migration:

```sql
-- One-to-one enforcement
ALTER TABLE jobs
    ADD CONSTRAINT jobs_recording_id_unique UNIQUE (recording_id);

-- Enum validation
ALTER TABLE entity_corrections
    ADD CONSTRAINT entity_corrections_correction_type_check CHECK (
        correction_type IN (
            'accepted', 'edited', 'dismissed',
            'reassigned', 'created', 'merged'
        )
    );

-- Range consistency
ALTER TABLE entity_corrections
    ADD CONSTRAINT entity_corrections_ai_confidence_range CHECK (
        ai_confidence >= 0.0 AND ai_confidence <= 1.0
    );

-- Non-negative guards
ALTER TABLE recordings
    ADD CONSTRAINT recordings_duration_ms_check CHECK (duration_ms >= 0);
ALTER TABLE recordings
    ADD CONSTRAINT recordings_file_size_check CHECK (file_size >= 0);

-- Missing CRUD policy
CREATE POLICY "Users update own folder"
    ON storage.objects FOR UPDATE
    USING (bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1])
    WITH CHECK (bucket_id = 'recordings'
        AND (SELECT auth.uid()::text) = (storage.foldername(name))[1]);
```

Also documented the `service_role_key` access pattern directly in the migration
file — the backend bypasses RLS by design, but this was nowhere stated in the
schema.

## Prevention

### Schema Writing Checklist

Before committing any migration, verify:

1. **Every FK with cardinality 1:1 in the ERD has UNIQUE on the FK column**
2. **Every TEXT column that holds enumerated values has a CHECK constraint**
3. **Every numeric column that represents a physical quantity has a range CHECK**
   (duration >= 0, confidence 0–1, file_size >= 0)
4. **If table A has a constraint on column X, every similar column in other tables
   has the same constraint** (the "sibling column" rule)
5. **Storage policies cover all 4 CRUD operations** (INSERT, SELECT, UPDATE, DELETE)
   — or document why one is intentionally omitted
6. **Access patterns are documented in the migration** — who uses anon_key + RLS
   vs. service_role_key bypass

### Process Insight

Multi-agent review was highly effective here. The "agent agreement" pattern —
where 4–6 independent agents flagged the same issue — reliably identified the
most impactful problems. Single-agent findings were often stylistic (P3), while
multi-agent consensus pointed to real constraint gaps (P1–P2).

## Cross-References

- Review findings: `docs/reviews/session-2-supabase/REVIEW-SUMMARY.md`
- Initial migration: `pf-intel/supabase/migrations/001_initial_schema.sql`
- Fix migration: `pf-intel/supabase/migrations/002_schema_fixes.sql`
- Related solution: `docs/solutions/workflow/validation-questions-between-sessions.md`
