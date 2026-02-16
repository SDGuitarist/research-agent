# PF-Intel V1: Research Synthesis

**Date**: 2026-02-16
**Status**: Research complete — ready for `/workflows:plan`
**Input**: 5 parallel research agents across voice pipeline, Expo audio, FastAPI architecture, data modeling, and security

---

## What the Brainstorm Got Right

The brainstorm made strong decisions that the research confirms:

1. **Voice pipeline first** — Correct build order. The riskiest assumption (AI parsing accuracy) should be tested before building forms and search.
2. **One-pass parse for V1** — Research confirms two-pass only helps for 30+ minute transcripts or multi-speaker scenarios. Single speaker, 3-15 min memos = one pass.
3. **OpenAI Whisper API over self-hosted** — At 50 min/month, API costs $0.15-0.30/month. Self-hosting minimum is $276/month. Break-even at ~500 hours/month (1000x your volume).
4. **Supabase for everything** — Database, file storage, and auth in one platform. Good fit for solo developer.
5. **Deferred duplicate detection** — Entity resolution is hard. Research confirms deferring automated resolution but adds critical V1 foundations (see below).
6. **Multiple recordings per event** — Concatenating server-side before parsing is the right pattern.

---

## What the Brainstorm Missed or Got Wrong

### Critical Changes (Must Address in Plan)

#### 1. `expo-av` is deprecated — use `expo-audio`

The brainstorm references "Expo audio recording" generically, but the specific library matters. **`expo-av` was deprecated in SDK 53 and removed in SDK 55.** Use `expo-audio` exclusively. Many tutorials still reference `expo-av` — ignore them.

#### 2. Expo Go will NOT work for this project

The brainstorm doesn't mention this. You **must use a development build** from day one. Expo Go lacks support for:
- `react-native-mmkv` (queue persistence)
- Background audio recording configuration
- Foreground services (Android background recording)
- Custom config plugins

**Impact on Session 1**: Project scaffolding must include `expo-dev-client` and EAS Build configuration, not just basic Expo init.

#### 3. The upload endpoint must be async (HTTP 202), not synchronous

The brainstorm says "Send audio to FastAPI, run Whisper, return transcript" as if it's one synchronous request. Research shows the pipeline takes 35-105 seconds:
- Whisper: 30-90 seconds for 15 min audio
- Claude: 5-15 seconds
- Platform timeout: 30-60 seconds (Railway/Render defaults)

**Pattern**: Return HTTP 202 immediately with a `job_id`. Mobile app polls `GET /audio/{job_id}/status` every 3-5 seconds. Background task runs the pipeline.

#### 4. UploadFile closes after the endpoint returns (FastAPI gotcha)

This is the single most common FastAPI mistake with background tasks. You must call `await file.read()` in the endpoint handler and pass the `bytes` to the background task. Never pass the `UploadFile` object itself.

#### 5. Record in M4A at 16kHz mono 64kbps (not default Expo settings)

The brainstorm doesn't specify audio settings. Research reveals:
- Whisper internally resamples everything to 16kHz mono anyway
- Custom preset: 16kHz, mono, 64kbps = ~0.5 MB/min
- A 15-minute recording = ~7.5 MB (well under Whisper's 25 MB limit)
- Default Expo HIGH_QUALITY preset uses stereo 128kbps = double the file size for zero benefit

#### 6. Android background recording requires a foreground service

The brainstorm mentions "record throughout the gig" but doesn't address that Android pauses recording when the app is backgrounded. Requires:
- `@notifee/react-native` or custom native module for foreground service
- Persistent notification visible to user
- Development build (not Expo Go)

**Impact**: This is a known pain point. Test on real Android devices early.

#### 7. The data model needs three tables the brainstorm didn't mention

Research identified three critical tables missing from the brainstorm:

- **`recording_mentions`** — Raw text mentions linked to parsed entities. Stores "Sarah from LVL" exactly as extracted. This is the foundation for future entity resolution.
- **`entity_corrections`** — What the AI extracted vs. what the user corrected. Gold for prompt improvement over time.
- **`jobs`** — Pipeline status tracking (uploaded → transcribing → parsing → completed → failed). Required for the async pattern.

#### 8. Phone numbers must ALWAYS be flagged for manual review

The brainstorm identifies voice parsing accuracy as "THE risk" but doesn't specify which fields are most problematic. Research is clear: **phone numbers are always wrong.** The Whisper-to-Claude pipeline is a two-step telephone game for digits. Hard-code phone numbers as always-yellow/red in the review UI regardless of AI confidence score.

#### 9. Supabase Auth, not API keys

The brainstorm's Session 2 mentions "RLS policies" but leaves auth as an open question. Research recommends:
- **Supabase Auth with email/password** (single account) for V1
- JWT tokens automatically, works with RLS
- `expo-secure-store` on the phone (not AsyncStorage — that's plain text)
- FastAPI validates JWT against Supabase's JWT secret

A static API key is tempting but dangerous — if it leaks, anyone can access your data and run up API costs.

#### 10. Audio files must go in a PRIVATE Supabase Storage bucket

Not explicitly stated in the brainstorm. Audio files contain names, phone numbers, and business observations. A public bucket means anyone who guesses the URL can download them. Use signed URLs with short expiration (60 seconds).

### Important Additions (Should Be in Plan)

#### 11. Use TUS resumable uploads for audio > 6 MB

A 15-minute recording at 64kbps is ~7.5 MB. On a slow cellular connection (1 Mbps), that's ~60 seconds. TUS resumable upload via `tus-js-client` + Supabase Storage means if the upload fails at 80%, it resumes from 80%.

#### 12. Pipeline state machine with intermediate saves

If Whisper succeeds but Claude fails, don't lose the transcript. Track each recording through states: `uploaded → transcribing → transcribed → parsing → parsed → reviewed → failed`. Save intermediate results at each step.

#### 13. Confidence-colored review cards (not raw numbers)

The brainstorm says "editable summary screen" but doesn't specify how confidence is shown. Research from successful HITL apps:
- Green checkmark (>0.8): pre-approved, tap to edit
- Yellow warning (0.5-0.8): expanded by default, needs confirmation
- Red flag (<0.5): must explicitly confirm or dismiss
- Source quotes visible under every entity
- "Accept All" per section for power users

#### 14. `gitleaks` pre-commit hook before the first commit

Install before any code exists. One committed API key in git history is permanently exposed even after deletion. Also: `.env` in `.gitignore` from day zero.

#### 15. Spending limits on OpenAI and Anthropic ($10/month each)

A retry bug could cost hundreds overnight. Hard caps prevent this. Expected costs are ~$0.35/month total.

#### 16. Sentry for error monitoring (free tier)

Both FastAPI and the Expo app. Critical config: `send_default_pii=False` to prevent contact names and phone numbers from appearing in Sentry.

#### 17. pg_trgm extension and trigram indexes from day one

Costs nothing at V1 scale, but enables future duplicate detection:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_contacts_name_trgm ON contacts USING gin (name gin_trgm_ops);
```

#### 18. Store the raw transcript AND raw parse output

Both are essential:
- Raw transcript for re-parsing when prompts improve
- Raw parse output (full JSON from Claude) for debugging and prompt iteration
- Storage cost is negligible (~4 KB per 5-minute debrief)

#### 19. Whisper `prompt` parameter for domain vocabulary

Priming Whisper with domain-specific words dramatically improves transcription of venue names, song titles, and equipment terms:
```python
prompt="Voice memo about music gigs. May mention venue names, contact names, phone numbers, song titles, set lists, sound equipment."
```

#### 20. Normalized phone storage for future dedup

Store `phone_normalized` (digits only) alongside the display format. Two contacts with the same normalized phone are almost certainly the same person — the strongest dedup signal.

---

## Answers to Open Questions (from Brainstorm)

| # | Question | Answer |
|---|----------|--------|
| 1 | Whisper: API vs self-hosted? | **API.** $0.15-0.30/month vs $276/month. Use `gpt-4o-mini-transcribe` ($0.003/min). |
| 2 | Hosting: Railway vs Render vs Fly.io? | **Railway for prototype, Render for production.** Both auto-deploy from git push. ~$5-7/month. |
| 3 | Monorepo structure? | **Yes.** `app/` (Expo) and `server/` (FastAPI) in one repo. Simplest for solo developer. |
| 4 | Audio format? | **M4A, 16kHz mono, 64kbps.** Expo records M4A natively. Whisper accepts M4A directly. No conversion needed. |
| 5 | Auth in V1? | **Supabase Auth** with single email/password account. JWT tokens, RLS policies, expo-secure-store. |
| 6 | Parse prompt engineering? | Use Claude structured outputs with Pydantic schema. Mandatory `confidence` and `source_quote` fields. Pass existing contacts (last 90 days) as context. |

---

## Revised Session Estimates

The brainstorm proposed 13 sessions. Based on research, I recommend these adjustments:

### Added Sessions
- **Security foundations** (gitleaks, .gitignore, Supabase Auth, RLS policies, private storage bucket) — should be part of Session 1-2, not bolted on later
- **Pipeline state tracking** (jobs table, async processing, polling endpoint) — integral to Session 5, not an afterthought

### Session Complexity Increases
- **Session 1** (scaffolding): Now includes EAS Build setup, dev client, MMKV, expo-secure-store — more complex than "just init Expo"
- **Session 4** (recording): Must include custom audio preset, Android foreground service, interruption handling
- **Session 5** (upload + transcription): Must be async (HTTP 202 + polling), not synchronous
- **Session 7** (review UI): Must include confidence-colored cards, source quotes, always-flag-phone-numbers pattern

### Potentially Simplified
- **Session 11** (offline queue): MMKV + NetInfo + TUS upload is well-documented with clear patterns. Research provides the complete implementation architecture.

---

## Cost Summary

| Service | Monthly Cost |
|---------|-------------|
| OpenAI Whisper API (gpt-4o-mini-transcribe) | ~$0.15 |
| Anthropic Claude API (parsing) | ~$0.20 |
| Railway/Render hosting | $5-7 |
| Supabase Pro (with backups) | $25 |
| Sentry (free tier) | $0 |
| UptimeRobot (free tier) | $0 |
| **Total** | **~$31-34/month** |

Note: Supabase free tier works for development. Upgrade to Pro ($25/month) before production for automatic daily backups.

---

## Security Checklist (V1 Ship-Blockers)

1. `.env` in `.gitignore` + `gitleaks` pre-commit hook
2. Supabase Auth with JWT on all endpoints
3. RLS enabled on every table (tested from client, not SQL editor)
4. Private Supabase Storage bucket with signed URLs
5. `expo-secure-store` for auth tokens (not AsyncStorage)
6. HTTPS everywhere
7. Spending limits on OpenAI ($10) and Anthropic ($10)
8. Sentry with `send_default_pii=False`
9. Never log PII (transcripts, names, phone numbers)
10. Disable FastAPI `/docs` in production
11. Production Expo build (not development)
12. Delete audio files from device after upload, from server after 7 days
13. Privacy policy at a hosted URL
14. Recording screen disclaimer: "Record your own observations only"

---

## Research Documents

Full details with code examples, SQL schemas, and library comparisons:

1. [Voice-to-Structured-Data Pipeline](2026-02-16-voice-to-structured-data-research.md)
2. [Expo Audio + Offline Queue](2026-02-16-expo-audio-offline-queue-research.md)
3. [FastAPI + Supabase Architecture](2026-02-16-fastapi-supabase-voice-pipeline.md)
4. [Data Modeling + Entity Resolution](2026-02-16-pf-intel-data-modeling-research.md) *(agent saved inline — see agent output)*
5. [Security, Privacy, Production Readiness](2026-02-16-pf-intel-security-research.md)

---

*Next step: `/workflows:plan` using this synthesis + the original brainstorm as input.*
