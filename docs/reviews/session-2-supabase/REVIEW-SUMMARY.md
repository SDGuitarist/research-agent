# Code Review Summary

**PR:** feat(session-2): supabase schema, auth, and storage
**Branch:** main (commit 67490b7)
**Date:** 2026-02-16
**Agents Used:** kieran-python-reviewer, pattern-recognition-specialist, code-simplicity-reviewer, architecture-strategist, security-sentinel, performance-oracle, data-integrity-guardian, git-history-analyzer, agent-native-reviewer

---

## P1 — Critical (Blocks Merge)

### 1. Hardcoded secrets committed to git
- **Source Agent:** security-sentinel
- **File:** `pf-intel/server/.env`
- **Issue:** Supabase URL, anon key, service role key, and JWT secret are committed to version control. The service role key bypasses all RLS policies. The JWT secret allows forging auth tokens.
- **Fix:** (1) Rotate all secrets in Supabase dashboard. (2) `git rm --cached pf-intel/server/.env`. (3) Add to `.gitignore`. (4) Consider `git filter-repo` to purge from history. (5) Create `.env.example` with placeholders.

### 2. Backend pipeline access pattern undocumented (RLS blocks 9 of 13 operations)
- **Source Agent:** agent-native-reviewer
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:252-384, 401-424
- **Issue:** Every RLS policy and storage policy gates on `auth.uid()`. The AI pipeline (Whisper, Claude parsing, job status updates) runs server-side in FastAPI with no auth JWT. The backend cannot read audio, write transcripts, update job status, or insert entities through RLS-gated access. The service_role key bypass is planned but nowhere documented in the migration.
- **Fix:** Add a comment block in the migration documenting the dual-access pattern: mobile client uses `anon_key` + RLS, backend uses `service_role` key which bypasses RLS by design.

### 3. Missing UNIQUE constraint on jobs.recording_id
- **Source Agent:** architecture-strategist
- **File:** `pf-intel/supabase/migrations/001_initial_schema.sql`:105
- **Issue:** Plan ERD declares `RECORDINGS ||--|| JOBS` (one-to-one), but SQL has no UNIQUE constraint. Multiple jobs could reference the same recording, breaking status queries.
- **Fix:** Change to `recording_id UUID NOT NULL UNIQUE REFERENCES recordings(id) ON DELETE CASCADE`.

---

## P2 — Important (Should Fix)

### 4. TEXT columns for typed data — capacity, pay, deadline
- **Source Agents:** kieran-python (3 findings), pattern-recognition, architecture, data-integrity, agent-native — **6 agents flagged this**
- **Files:** `:50` (capacity), `:79` (pay), `:126` (deadline)
- **Issue:** `venues.capacity` (should be INTEGER), `events.pay` (should be NUMERIC), `action_items.deadline` (should be DATE) are all TEXT. Prevents sorting, filtering, range queries, and agent-driven date comparisons ("overdue items this week").
- **Fix:** Change to `INTEGER`, `NUMERIC(10,2)`, and `DATE` respectively. Keep raw TEXT columns alongside if needed for original transcription text.

### 5. Missing CHECK on entity_corrections.correction_type
- **Source Agents:** kieran-python, pattern-recognition, architecture, security, agent-native — **5 agents flagged this**
- **File:** `:175`
- **Issue:** Free-form TEXT with no CHECK constraint, unlike `jobs.status` and `action_items.priority`. Different code paths could write inconsistent values.
- **Fix:** Add `CHECK (correction_type IN ('accepted', 'edited', 'dismissed', 'reassigned', 'created', 'merged'))`.

### 6. Missing CHECK on entity_corrections.ai_confidence
- **Source Agents:** kieran-python, pattern-recognition, architecture, data-integrity — **4 agents flagged this**
- **File:** `:176`
- **Issue:** `recording_mentions.confidence` has range constraint (0-1) but `entity_corrections.ai_confidence` does not. Inconsistency.
- **Fix:** Add `CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0)`.

### 7. Missing storage UPDATE policy
- **Source Agents:** kieran-python, pattern-recognition, architecture, security, data-integrity — **5 agents flagged this**
- **File:** `:401-424`
- **Issue:** Storage RLS covers INSERT/SELECT/DELETE but not UPDATE. If files should be immutable, document it. If not, add the policy.
- **Fix:** Add UPDATE policy or add comment: `-- Audio files are immutable; UPDATE intentionally omitted.`

### 8. Cross-user FK references not validated
- **Source Agents:** architecture, data-integrity, security — **3 agents flagged this**
- **File:** `:61, 77, 90` (all FK columns)
- **Issue:** FK constraints don't enforce same `user_id`. User A could reference User B's venue. FK checks bypass RLS. With CASCADE deletes, User A deleting their entity could cascade into User B's mentions.
- **Fix:** Document as known V1 limitation (single-user app). Add trigger-based ownership validation for multi-user V2.

### 9. CASCADE delete destroys mentions/corrections audit trail
- **Source Agent:** data-integrity-guardian
- **File:** `:143-146, 168-171`
- **Issue:** ON DELETE CASCADE on entity FK columns means deleting a venue/contact/event silently destroys all associated mentions and corrections — losing AI extraction and user correction history.
- **Fix:** Consider `ON DELETE SET NULL` on entity FK columns. Relax the one-entity CHECK to allow all-NULL (orphaned but preserved).

### 10. Missing CHECK on duration_ms and file_size
- **Source Agent:** kieran-python-reviewer
- **File:** `:92-93`
- **Issue:** Negative file sizes or durations would be silently accepted.
- **Fix:** Add `CHECK (duration_ms > 0)` and `CHECK (file_size > 0)`.

### 11. audio/m4a is not a registered MIME type
- **Source Agents:** kieran-python, architecture, security — **3 agents flagged this**
- **File:** `:398`
- **Issue:** `audio/m4a` is not IANA-registered. Correct type is `audio/mp4` (already included) or `audio/x-m4a`.
- **Fix:** Replace `audio/m4a` with `audio/x-m4a`. Consider adding `audio/aac` for completeness.

### 12. recording_mentions.confidence allows NULL (plan says mandatory)
- **Source Agents:** data-integrity, agent-native — **2 agents flagged this**
- **File:** `:148`
- **Issue:** NULL passes the CHECK constraint (PostgreSQL behavior). Plan specifies confidence is mandatory (0.0-1.0).
- **Fix:** Add `NOT NULL` to the confidence column.

### 13. No transaction wrapper on migration
- **Source Agent:** data-integrity-guardian
- **File:** `:1-424`
- **Issue:** If any statement fails mid-way, the database is left partially created. No rollback possible.
- **Fix:** Wrap in `BEGIN; ... COMMIT;`. Put `CREATE EXTENSION` before `BEGIN`.

### 14. file_size should be BIGINT
- **Source Agents:** pattern-recognition, architecture — **2 agents flagged this**
- **File:** `:93`
- **Issue:** INTEGER max ~2.1 GB. Currently safe (50 MB limit) but latent risk if limit changes.
- **Fix:** Change to `BIGINT`. No cost difference at this scale.

### 15. Missing recording_id FK on action_items
- **Source Agent:** kieran-python-reviewer
- **File:** `:120-134`
- **Issue:** Cannot trace action items back to the recording that generated them. Essential for the review UI.
- **Fix:** Add `recording_id UUID REFERENCES recordings(id) ON DELETE SET NULL`.

### 16. updated_at missing on recording_mentions and entity_corrections
- **Source Agents:** kieran-python, pattern-recognition, architecture — **3 agents flagged this**
- **File:** `:186-212`
- **Issue:** 6 tables get `updated_at` triggers, 2 don't. No documentation of why.
- **Fix:** Either add `updated_at` + trigger, or add comment: `-- Append-only tables; updated_at intentionally omitted.`

### 17. Events table missing title/name column
- **Source Agent:** architecture-strategist
- **File:** `:78`
- **Issue:** Only identifying field is `date` (nullable). Events have no human-readable identifier for the UI.
- **Fix:** Add `title TEXT`. Parsing can auto-generate titles like "Gig at The Blue Note".

### 18. Missing composite index on jobs(recording_id, status)
- **Source Agent:** performance-oracle
- **File:** `:241`
- **Issue:** Client polls jobs by recording_id + status every 3-5 seconds. Separate indexes exist but no composite.
- **Fix:** Add `CREATE INDEX idx_jobs_recording_status ON jobs (recording_id, status);`. Drop standalone `idx_jobs_recording_id`.

### 19. Missing index on events.date
- **Source Agent:** performance-oracle
- **File:** `:78`
- **Issue:** Chronological sorting and date-range filtering require sequential scans without an index.
- **Fix:** Add `CREATE INDEX idx_events_date ON events (date);`

### 20. Missing partial index on action_items.completed
- **Source Agent:** performance-oracle
- **File:** `:128`
- **Issue:** "Show open action items" has no index support.
- **Fix:** Add `CREATE INDEX idx_action_items_open ON action_items (user_id) WHERE completed = FALSE;`

### 21. Transcripts and raw_parse_output have no size limits
- **Source Agent:** security-sentinel
- **File:** `:94-95`
- **Issue:** TEXT and JSONB columns with no length constraints. Buggy client could insert arbitrarily large content.
- **Fix:** Add `CHECK (length(transcript) <= 500000)` and `CHECK (pg_column_size(raw_parse_output) <= 1048576)`.

### 22. No job status transition validation
- **Source Agent:** agent-native-reviewer
- **File:** `:102-117`
- **Issue:** CHECK validates status values but not transitions. A bug could skip `pending` directly to `completed`.
- **Fix:** Add BEFORE UPDATE trigger validating state transitions, or defer to application layer and document.

### 23. entity_corrections / recording_mentions may be premature (YAGNI)
- **Source Agent:** code-simplicity-reviewer
- **Files:** `:139-184`
- **Issue:** `entity_corrections` tracks AI vs. user corrections for a pipeline that doesn't exist yet. `recording_mentions` provides provenance with no UI consumer. Saves ~85 lines if deferred.
- **Fix:** Design decision — keep if the tables influence how you build the pipeline, defer if not. Document the decision either way.

---

## P3 — Nice-to-Have

### 24. events.date column name shadows SQL reserved word
- **Source Agents:** kieran-python, pattern-recognition
- **Fix:** Rename to `event_date TIMESTAMPTZ`.

### 25. FLOAT should be explicit (REAL or NUMERIC)
- **Source Agent:** kieran-python
- **Fix:** Use `REAL` or `NUMERIC(3,2)` for confidence columns.

### 26. Rollback doesn't explicitly drop indexes/triggers
- **Source Agents:** kieran-python, pattern-recognition, architecture
- **Fix:** Add comment explaining implicit cleanup via DROP TABLE.

### 27. action_items.assignee is TEXT, not FK to contacts
- **Source Agent:** pattern-recognition
- **Fix:** Add optional `assignee_contact_id UUID REFERENCES contacts(id)` alongside TEXT.

### 28. RLS policies could use FOR ALL (saves ~90 lines)
- **Source Agents:** pattern-recognition, code-simplicity
- **Fix:** Replace 4 per-table policies with 1 `FOR ALL` per table.

### 29. CREATE OR REPLACE could silently overwrite
- **Source Agent:** security-sentinel
- **Fix:** Use project-prefixed function names or `CREATE FUNCTION` (without REPLACE).

### 30. ON DELETE CASCADE from auth.users deletes all data
- **Source Agent:** security-sentinel
- **Fix:** Consider `ON DELETE RESTRICT` or soft-delete. Ensure backups.

### 31. Storage filenames unrestricted
- **Source Agent:** security-sentinel
- **Fix:** Add filename pattern check in INSERT policy.

### 32. Rollback fails if storage objects exist
- **Source Agent:** data-integrity-guardian
- **Fix:** Add `DELETE FROM storage.objects WHERE bucket_id = 'recordings';` before bucket delete.

### 33. Trigram indexes and phone normalization may be premature
- **Source Agent:** code-simplicity-reviewer (Performance disagrees — says overhead is negligible)
- **Fix:** Keep or remove. Disagreement between agents — developer's call.

### 34. Jobs status has too many states for V1
- **Source Agent:** code-simplicity-reviewer
- **Fix:** Simplify to `pending, processing, completed, failed` or keep detailed states for pipeline observability.

### 35. No pipeline_version tracking on jobs
- **Source Agent:** agent-native-reviewer
- **Fix:** Add `pipeline_version TEXT` for prompt iteration debugging.

### 36. Plan ERD diverges from implementation
- **Source Agent:** architecture-strategist
- **Fix:** Update ERD to reflect actual nullable-FK pattern.

### 37. PII stored in plain text
- **Source Agent:** security-sentinel
- **Fix:** Acceptable for V1 single-tenant. Plan for encryption in V2.

### 38. Session 1 appears skipped / commit convention shift
- **Source Agent:** git-history-analyzer
- **Fix:** Document whether Session 1 was deferred. Standardize commit prefix.

---

## Statistics

| Severity | Count |
|----------|-------|
| P1 Critical | 3 |
| P2 Important | 20 |
| P3 Nice-to-have | 15 |
| **Total (deduplicated)** | **38** |

## Agent Agreement (findings flagged by 3+ agents)

| Finding | Agents | Count |
|---------|--------|-------|
| TEXT columns for typed data | kieran, pattern, architecture, data-integrity, performance, agent-native | 6 |
| Missing correction_type CHECK | kieran, pattern, architecture, security, agent-native | 5 |
| Missing storage UPDATE policy | kieran, pattern, architecture, security, data-integrity | 5 |
| Missing ai_confidence CHECK | kieran, pattern, architecture, data-integrity | 4 |
| Cross-user FK not validated | architecture, security, data-integrity | 3 |
| audio/m4a MIME type | kieran, architecture, security | 3 |
| updated_at omission | kieran, pattern, architecture | 3 |
| Rollback implicit drops | kieran, pattern, architecture | 3 |

## Agents & Batches

| Batch | Agents | Findings (raw) |
|-------|--------|----------------|
| batch1 | kieran-python, pattern-recognition, code-simplicity | 15 + 13 + 10 = 38 |
| batch2 | architecture, security, performance | 11 + 12 + 9 = 32 |
| batch3 | data-integrity, git-history, agent-native | 10 + 4 + 8 = 22 |
| **Total raw** | | **92** |
| **Deduplicated** | | **38** |

## Recommended Fix Priority

**Do immediately (before next session):**
1. Remove `.env` from git, rotate secrets, add `.gitignore`
2. Add `UNIQUE` to `jobs.recording_id`
3. Add service_role documentation comment block in migration

**Do in Session 3 (schema refinements):**
4. Fix TEXT columns → proper types (capacity, pay, deadline)
5. Add missing CHECK constraints (correction_type, ai_confidence, duration_ms, file_size)
6. Fix MIME type (audio/m4a → audio/x-m4a)
7. Add `NOT NULL` to confidence
8. Add `BIGINT` for file_size
9. Add transaction wrapper
10. Add missing indexes (composite jobs, events.date, action_items partial)
11. Add recording_id FK to action_items
12. Add events.title column
13. Document storage UPDATE policy decision
14. Document updated_at omission rationale

**Defer to V2 (acceptable V1 limitations):**
- Cross-user FK validation (single-user app)
- PII encryption
- Job status transition triggers
- Pipeline version tracking
