# Agent-Native Reviewer — Review Findings

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** session-2-supabase
**Date:** 2026-02-16
**Agent:** agent-native-reviewer

## Findings

### RLS blocks the entire backend pipeline (9 of 13 operations inaccessible)
- **Severity:** P1
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:252-384
- **Issue:** Every RLS policy gates on `auth.uid()`, which requires a Supabase Auth JWT from a logged-in user. The AI processing pipeline (Whisper transcription, Claude parsing, job status updates) runs server-side in FastAPI BackgroundTasks — it has no `auth.uid()`. The backend literally cannot read, write, or update any row through the Supabase client. 9 of 13 identified operations (update job status, write transcript, insert entities, read audio, etc.) are blocked.
- **Suggestion:** Document the dual-access pattern: mobile client uses `anon_key` with RLS, backend uses `service_role` key which bypasses RLS. Add a comment block in the migration explaining this. The service_role key is already planned (line 346 of plan). Alternatively, add explicit service-role RLS policies for auditability.

### Storage RLS blocks backend audio reads
- **Severity:** P1
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:401-424
- **Issue:** Storage policies only allow reads where `auth.uid()::text = foldername[1]`. The backend pipeline needs to read audio files for Whisper transcription but has no `auth.uid()`.
- **Suggestion:** Same fix as above — service_role bypasses storage RLS. Document this pattern.

### No job status transition validation in the database
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:102-117
- **Issue:** The CHECK constraint validates status values but not transition sequences. An agent (or bug) could set status from `pending` directly to `completed`, skipping the pipeline. With multiple agents/processes touching jobs (pipeline worker, stale-job recovery, future retry endpoint), application-level enforcement is fragile.
- **Suggestion:** Add a BEFORE UPDATE trigger that validates transitions (e.g., `pending` can only go to `transcribing` or `failed`). Single source of truth at DB level.

### entity_corrections.correction_type has no CHECK constraint
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:175
- **Issue:** No constraint on `correction_type` values. Different code paths could write inconsistent values ("rename", "Rename", "RENAME"), making aggregate queries for agent learning unreliable.
- **Suggestion:** Add `CHECK (correction_type IN ('accepted', 'edited', 'dismissed', 'reassigned', 'created', 'merged'))`. Define the vocabulary before any code writes to this table.

### Missing index on entity_corrections.field_name for agent learning queries
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:246-247
- **Issue:** The plan calls entity_corrections "gold for prompt improvement." The most valuable agent query is "for field X on entity type Y, how often does the AI get it wrong?" Currently only user_id and recording_id are indexed.
- **Suggestion:** Add `CREATE INDEX idx_entity_corrections_field_name ON entity_corrections (field_name);` and consider partial composite indexes for entity type + field combinations.

### recording_mentions.confidence allows NULL (plan says mandatory)
- **Severity:** P2
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:148
- **Issue:** NULL confidence creates ambiguity for agents filtering on confidence thresholds. The plan specifies confidence is mandatory (0.0-1.0).
- **Suggestion:** Add `NOT NULL` to the confidence column.

### No pipeline_version tracking on jobs
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:102-117
- **Issue:** When iterating on parsing prompts or Whisper models, you won't know which agent version processed each recording. Can't segment correction rates by agent version.
- **Suggestion:** Add `pipeline_version TEXT` to the jobs table. Cheap insurance for debugging prompt iterations.

### deadline TEXT prevents agent date queries
- **Severity:** P3
- **File:** pf-intel/supabase/migrations/001_initial_schema.sql:126
- **Issue:** An agent trying to query "action items due this week" cannot use date comparison on TEXT. The AI pipeline writes free-form text from voice ("follow up next Tuesday"), which is fine for initial extraction.
- **Suggestion:** Add `deadline_date DATE` alongside the TEXT `deadline`. Pipeline writes raw text, review UI parses into structured date.

## Positive Observations

- **raw_parse_output JSONB** preserves the agent's full work product — shared-workspace pattern
- **entity_corrections as first-class table** creates structured learning signal for prompt improvement
- **Exclusive-FK pattern** on recording_mentions/entity_corrections provides real FK integrity
- **phone_normalized trigger** ensures consistency regardless of which actor (user, agent, API) writes the data
- **Trigram indexes from day one** enable fuzzy entity matching for future agent use

## Summary
- P1 (Critical): 2
- P2 (Important): 4
- P3 (Nice-to-have): 2
