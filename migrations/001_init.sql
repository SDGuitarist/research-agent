-- 001_init.sql — Phase A schema: job queue + report/gap/critique state.
-- All state that used to live in files (reports/, gap YAML, gap_audit.log,
-- reports/meta/critique-*.yaml) now lives here. contexts/*.md stay as files.
-- gen_random_uuid() is a core function in PostgreSQL 13+ (no extension needed).

-- jobs: the Postgres-table-as-queue. Claimed with FOR UPDATE SKIP LOCKED.
CREATE TABLE jobs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    query        text NOT NULL,
    mode         text NOT NULL CHECK (mode IN ('quick', 'standard', 'deep')),
    status       text NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts     integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    claim_id     uuid,          -- set at claim; checked at finish (owner guard)
    claimed_at   timestamptz,
    heartbeat_at timestamptz,   -- lease is a staleness window on this column
    finished_at  timestamptz,
    error        text,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- Partial indexes keep the FIFO claim and the reaper scan cheap as
-- done/failed rows accumulate.
CREATE INDEX jobs_queued_fifo   ON jobs (created_at)   WHERE status = 'queued';
CREATE INDEX jobs_running_lease ON jobs (heartbeat_at) WHERE status = 'running';

-- reports: finished markdown + metadata. One report per job (UNIQUE job_id,
-- nullable for CLI/MCP-created reports). report_key is the canonical,
-- collision-proof lookup key shared by CLI, MCP, and web (slug-{uuid8}).
CREATE TABLE reports (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id        uuid UNIQUE REFERENCES jobs (id),
    report_key    text NOT NULL UNIQUE,
    query         text NOT NULL,
    mode          text NOT NULL,
    content       text NOT NULL,
    gate_decision text,
    sources_used  integer,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- gaps: per-gap rows (replaces the whole-document YAML) so two writers can
-- update different gaps without clobbering. Mutated with targeted UPDATEs.
CREATE TABLE gaps (
    id            text PRIMARY KEY,
    category      text NOT NULL,
    status        text NOT NULL DEFAULT 'unknown'
                  CHECK (status IN ('unknown', 'verified', 'stale', 'blocked')),
    priority      integer NOT NULL DEFAULT 3,
    last_verified timestamptz,
    last_checked  timestamptz,
    ttl_days      integer,
    blocks        text[] NOT NULL DEFAULT '{}',
    blocked_by    text[] NOT NULL DEFAULT '{}',
    findings      text NOT NULL DEFAULT '',
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- gap_audit: append-only status-flip log (replaces gap_audit.log). event_at
-- preserves the original event time; inserted_at is the DB write time.
CREATE TABLE gap_audit (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gap_id      text NOT NULL REFERENCES gaps (id),
    old_status  text NOT NULL,
    new_status  text NOT NULL,
    reason      text NOT NULL DEFAULT '',
    event_at    timestamptz NOT NULL,
    inserted_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX gap_audit_gap_id ON gap_audit (gap_id);

-- critiques: self-critique results (replaces reports/meta/critique-*.yaml).
CREATE TABLE critiques (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at         timestamptz NOT NULL DEFAULT now(),
    overall_pass       boolean NOT NULL,
    mean_score         real NOT NULL,
    source_diversity   integer,
    claim_support      integer,
    coverage           integer,
    geographic_balance integer,
    actionability      integer,
    weaknesses         text,
    suggestions        text
);
