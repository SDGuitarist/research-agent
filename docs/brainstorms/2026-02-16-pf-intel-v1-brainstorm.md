# PF-INTEL V1 Brainstorm

**Date**: 2026-02-16
**Status**: Ready for planning
**Input**: `pf-intel/PF-INTEL_ Complete Discovery & Handoff Document (v2).md`

---

## What We're Building

A mobile-first venue intelligence app for Pacific Flow Entertainment. The core innovation is a **voice-to-structured-data pipeline**: after every gig, the owner records a car debrief on his phone. The app transcribes it, AI-parses it into venue records, contact records, event records, and action items, then presents an editable summary for fast review and correction.

**Stack**: Expo (React Native) frontend, Python FastAPI backend, Supabase (Postgres + file storage).

**Repo**: New repo `pf-intel`, separate from `research-agent`. Python backend mirrors research-agent patterns (frozen dataclasses, modular single-concern files, specific exceptions, pip-installable package).

---

## Why This Approach

### Voice Pipeline First (Approach A)

The entire app's value hinges on one question: *Can AI reliably parse a stream-of-consciousness car debrief into structured data, and can the owner review/correct it faster than manual entry?*

If voice parsing doesn't work well enough, the app is just a manual database — and the owner already has HoneyBook for that. So we build and test the pipeline before anything else.

**Build order**:
1. Voice pipeline (record, upload, transcribe, parse, review, save)
2. Search and display (find what you've captured)
3. Gig prep mode (pre-gig briefing from saved data)
4. Manual entry forms (fallback for non-voice situations)

**Rejected alternatives**:
- **Database + Forms First (B)**: Delays testing the riskiest assumption. Risk of building forms for a data model that changes once we see parser output.
- **Vertical Slice (C)**: Good for stack validation, but the stack is well-understood (Expo + FastAPI + Supabase). The risk is in the AI pipeline, not the infrastructure.

---

## Key Decisions

### 1. Recording UX: Big Red Button, Multiple Per Event
Open app, tap Record, talk, tap Stop. One-purpose screen, minimal UI. No gig phases or timeline flow in V1 — the AI classifies content, not the user.

**Multiple recordings per event**: The owner records throughout the gig — a quick note during setup, another at break, the full car debrief driving home. All recordings are grouped under one event. Before parsing, the transcripts are concatenated in chronological order into a single unified text. The AI parses the combined transcript as one debrief, producing one set of structured records. The owner reviews one unified summary, not three separate ones.

- Phone UI shows recordings grouped by event with add/remove controls
- Backend concatenates transcripts with timestamps before the parse step
- Keeps the one-pass parse simple — just a longer input

### 2. Review UX: Editable Summary
After parsing, show all extracted data as an editable form on one screen. Owner scans it, fixes what's wrong, hits Save. Target: under 2 minutes to review a 5-minute debrief. If review is slower than manual entry, the pipeline is worthless.

### 3. One-Pass Parse for V1
Single Claude API call extracts everything (contacts, venues, events, actions) at once. Simpler to build, test, and debug. The two-pass split (quick parse for time-sensitive contacts vs. deep parse for venue intel) is deferred until real usage shows it's needed.

### 4. Offline: Recording Queue Only
Record voice memos locally, queue for upload when connectivity returns. Offline gig prep (caching venue data on phone) is deferred — it's a nice-to-have, not a V1 blocker. Signal is "sometimes" an issue, not "often."

### 5. Duplicate Detection: Deferred
Entity resolution ("Sarah from LVL" across 3 debriefs = 1 contact) is hard. V1 creates new records; the owner merges duplicates manually. Automated resolution comes later with real data to train on.

### 6. Supabase Schema: Start Simple
Three core tables (venues, contacts, events) plus a recordings table. Relationships via foreign keys. No denormalization, no materialized views. Add complexity when queries demand it.

---

## Riskiest Assumptions

1. **Voice parsing accuracy** — AI will misparse names and phone numbers. The review UX must make corrections fast, not just possible. This is THE risk.
2. **Whisper transcription quality** — Car audio (road noise, phone mic) may produce poor transcripts. Need to test with real car debrief recordings early.
3. **Server hosting complexity** — Python FastAPI needs cloud hosting (Railway, Render, or Fly.io). First time managing a server for this developer. Keep deployment simple.
4. **Expo learning curve** — React Native is new territory. Claude Code handles the coding, but the developer needs to understand enough to direct modifications.

---

## Proposed V1 Sessions (for `/workflows:plan`)

### Phase 1: Foundation
- **Session 1**: Project scaffolding — Expo app, FastAPI server, Supabase project, monorepo structure
- **Session 2**: Supabase schema — venues, contacts, events, recordings tables with RLS policies
- **Session 3**: FastAPI skeleton — health check, audio upload endpoint, Supabase client

### Phase 2: Voice Pipeline
- **Session 4**: Phone recording — Expo audio recording with big red button UI
- **Session 5**: Upload + transcription — Send audio to FastAPI, run Whisper, return transcript
- **Session 6**: AI parsing — Claude API prompt to extract structured data from transcript
- **Session 7**: Review/correction UI — Editable summary screen on phone, save to Supabase

### Phase 3: Data Access
- **Session 8**: Venue list + detail view — Browse and search saved venues
- **Session 9**: Contact list + detail view — Browse and search saved contacts
- **Session 10**: Gig prep mode — "Show me everything about [venue]" briefing view

### Phase 4: Polish + Offline
- **Session 11**: Offline recording queue — Record without signal, upload when back online
- **Session 12**: Manual entry forms — Fallback data entry for venues, contacts, events
- **Session 13**: End-to-end testing with real car debrief recordings

**Estimated sessions**: 13 (each ~50-100 lines, one concern)

---

## Open Questions (for planning phase)

1. **Whisper deployment**: OpenAI Whisper API vs. self-hosted Whisper on the FastAPI server? API is simpler but adds a dependency and cost. Self-hosted is free but needs GPU or runs slow on CPU.
2. **FastAPI hosting**: Railway vs. Render vs. Fly.io? Need something beginner-friendly with easy deploys from git push.
3. **Monorepo structure**: One repo with `app/` (Expo) and `server/` (FastAPI)? Or separate repos? Monorepo is simpler for a solo developer.
4. **Audio format**: What format does Expo record in? Does Whisper need conversion? Need to test the actual recording → transcription path.
5. **Supabase auth**: Does the app need user auth in V1 (single user)? Or just an API key? Simplest option for solo use.
6. **Parse prompt engineering**: The Claude API prompt for parsing car debriefs will need iteration. Plan for a prompt testing session with real transcripts.

---

## Ecosystem Context

PF-Intel is one node in a 4-node intelligence network. V1 is standalone. Future versions connect to:
- **Research Agent** (V3): `run_research_async()` import for venue background research
- **Lead Processor** (future): Shared Supabase tables
- **Sales Assistant** (future): Shared Supabase tables

All nodes share one Supabase instance. Python backends enable direct library imports between nodes.

---

*Next step: `/workflows:plan` to turn these sessions into detailed implementation steps.*
