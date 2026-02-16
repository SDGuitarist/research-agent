# PF-Intel V1: Security, Privacy, and Production Readiness Research

**Date**: 2026-02-16
**Status**: Research complete
**For**: PF-Intel V1 planning phase
**Context**: Solo-user Expo + FastAPI + Supabase app processing voice recordings of business contacts

---

## Priority Legend

- **MUST HAVE (V1)** -- Do this before shipping or you have a real legal/security exposure
- **SHOULD HAVE (V1)** -- Strongly recommended; low effort, high protection
- **NICE TO HAVE (V2+)** -- Important but acceptable to defer for a single-user V1

---

## A. Voice Data Privacy and Legal

### A1. One-Party vs Two-Party Consent -- You Are Fine

**California is a two-party consent state** for recording *conversations* between parties (Penal Code 632). However, the PF-Intel use case is fundamentally different:

- The owner is recording **their own monologue** (a car debrief) -- not a conversation with another person
- No other party is participating in the recording
- Penal Code 632 applies to "confidential communications" between two or more people, not one-sided voice memos about other people

**Actionable**: You are not recording conversations. You are dictating your own observations. This falls squarely outside California's wiretapping statute. No consent from mentioned contacts is needed for the recording itself.

**Edge case to watch**: If the owner ever records *during* a conversation with a vendor or coordinator (e.g., at a break), that becomes a two-party consent situation. The app should not encourage recording conversations -- only personal debriefs.

**MUST HAVE (V1)**: Add a brief note in the app's recording screen: "Record your own observations only. Do not record conversations with others without their consent."

Sources:
- [California Recording Law - Digital Media Law Project](https://www.dmlp.org/legal-guide/california-recording-law)
- [Can I Record a Conversation in California? - Romano Law](https://www.romanolaw.com/can-i-record-a-conversation-in-california/)

### A2. CCPA -- Almost Certainly Does Not Apply to You

CCPA applies to for-profit businesses that meet **any one** of these thresholds:
1. Gross annual revenue over $26.625 million (as of 2025)
2. Buy, sell, or share personal information of 100,000+ California residents/households
3. Derive 50%+ of revenue from selling/sharing personal information

A solo entertainment business with 8-10 events per month and 2-3 new contacts per event (~300 contacts/year) does not come close to any threshold. CCPA **does not apply** to PF-Intel.

**However**: California's privacy landscape is evolving. Even below the thresholds, having a basic privacy practice protects you.

**SHOULD HAVE (V1)**: A simple privacy policy (see A3 below), even though CCPA does not mandate it for your business size.

Sources:
- [CCPA - California Attorney General](https://oag.ca.gov/privacy/ccpa)
- [CCPA Requirements 2026 Complete Guide](https://secureprivacy.ai/blog/ccpa-requirements-2026-complete-compliance-guide)

### A3. Privacy Policy -- Yes, Even for a Single-User App

You need a privacy policy because:
1. **Apple App Store requires it** for any app that collects personal data (and yours collects contact names, phone numbers)
2. **Google Play Store requires it** if you ever publish there
3. If you plan to open-source or sell the tool later, you need a policy in place
4. It forces you to think through your data practices

**MUST HAVE (V1)**: A simple, honest privacy policy covering:
- What data is collected (voice recordings, contact info, venue details)
- Where data is stored (Supabase, encrypted at rest)
- Third-party services that process data (OpenAI Whisper, Anthropic Claude)
- Data retention periods
- How to request data deletion
- That you are the sole user (this simplifies everything)

This does not need to be lawyer-written for V1. A clear, plain-English document hosted at a URL the app can link to is sufficient.

### A4. Data Retention -- Delete Audio After Transcription

**Recommendation**: Delete audio recordings from Supabase storage within **7 days** of successful transcription. Keep the transcript and structured data indefinitely (that is the whole point of the app).

Rationale:
- Audio files are large and expensive to store
- The audio contains the rawest form of personal information (actual voice, ambient sounds)
- Once transcribed and parsed, the audio has no further business purpose
- Keeping audio increases your exposure if there is ever a breach

**MUST HAVE (V1)**: Automated deletion of audio files 7 days after successful transcription. Keep a boolean flag `audio_deleted` on the recording record.

**SHOULD HAVE (V1)**: Allow the owner to manually delete audio immediately after reviewing the parsed data.

### A5. Contact Data Deletion Requests

Even though CCPA likely does not apply, a contact could still ask you to remove their information. This is good business practice regardless of legal obligation.

**NICE TO HAVE (V2+)**: A simple admin function to search for and delete all records mentioning a specific contact. For V1, you can do this manually via Supabase dashboard.

---

## B. API Security for a Single-User Mobile App

### B1. Authentication Strategy -- Supabase Auth with a Single Account

For a single-user app, the question is: "What is the simplest thing that is still secure?"

**Recommended approach: Supabase Auth (email/password) with a single user account.**

Why Supabase Auth over alternatives:
- **API key in the app**: Too risky. If the key leaks, anyone can access your data. API keys cannot be revoked without redeploying.
- **Custom JWT**: Unnecessary complexity. You would be building your own auth system.
- **Supabase Auth**: Already built into Supabase. Gives you JWT tokens automatically. Works with RLS policies. Free. One account is all you need.

How it works:
1. Create one Supabase user account (your email/password)
2. App logs in via Supabase Auth, gets a JWT
3. All API requests to FastAPI include the JWT in the Authorization header
4. FastAPI validates the JWT against Supabase's JWT secret
5. Supabase RLS policies enforce row-level access using `auth.uid()`

**MUST HAVE (V1)**: Supabase Auth with email/password login. Single user account. JWT-based request authentication.

Sources:
- [FastAPI OAuth2 with JWT - Official Docs](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security)

### B2. Secure Storage of Credentials on the Phone

**MUST HAVE (V1)**: Use `expo-secure-store` for all sensitive values on the device:
- Supabase JWT token (after login)
- Refresh token
- Any cached credentials

**Never store in AsyncStorage** -- it is plain text on the filesystem. Anyone with a rooted/jailbroken device can read it.

```
expo-secure-store uses:
- iOS: Keychain Services (hardware-backed encryption)
- Android: EncryptedSharedPreferences (Android Keystore)
```

**Important limitation**: expo-secure-store has a practical size limit (~2KB per value on some iOS versions). Store only tokens and keys, not large data.

Sources:
- [SecureStore - Expo Documentation](https://docs.expo.dev/versions/latest/sdk/securestore/)
- [React Native Security - Official Docs](https://reactnative.dev/docs/security)

### B3. HTTPS Enforcement

**MUST HAVE (V1)**: All communication between the Expo app and FastAPI server must use HTTPS. No exceptions.

- Railway, Render, and Fly.io all provide free SSL/TLS certificates automatically
- In the Expo app, hardcode the `https://` URL -- never allow `http://`
- In FastAPI, add middleware to redirect HTTP to HTTPS if deployed behind a reverse proxy

### B4. API Abuse Prevention

For a single-user app, the threat is not scale abuse -- it is unauthorized access. If someone discovers your API endpoint, they could:
- Upload arbitrary audio files (running up your Whisper/Claude costs)
- Read your contact database
- Delete your data

**MUST HAVE (V1)**:
- JWT authentication on every endpoint (covered in B1)
- Supabase RLS on every table (covered in B1)

**SHOULD HAVE (V1)**:
- Basic rate limiting on the FastAPI server (e.g., `slowapi` library: 10 requests/minute on the upload endpoint). Prevents runaway costs if a token is compromised.
- CORS configuration: Only allow requests from your Expo app's origin

### B5. Supabase Key Safety

Supabase gives you two keys:
- **anon key**: Safe to use in the client (with RLS enabled). This is the public key.
- **service_role key**: **NEVER expose this.** It bypasses all RLS. Server-side only.

**MUST HAVE (V1)**:
- The Expo app uses ONLY the anon key
- The service_role key lives ONLY on the FastAPI server as an environment variable
- RLS is enabled on EVERY table, with policies restricting access to `auth.uid()`

Sources:
- [Supabase Security Best Practices](https://www.supadex.app/blog/best-security-practices-in-supabase-a-comprehensive-guide)
- [Supabase Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)

---

## C. Sensitive Data in Transit and at Rest

### C1. Audio File Upload Encryption

**Already handled by HTTPS** (Section B3). When the Expo app uploads audio over HTTPS, the data is encrypted in transit via TLS. No additional encryption layer is needed for the upload itself.

**NICE TO HAVE (V2+)**: Client-side encryption of audio before upload (so even if the server is compromised, audio is unreadable). This is overkill for V1.

### C2. Supabase Encryption at Rest

Supabase provides **encryption at rest by default** for both the Postgres database and Storage (file storage). Your data on Supabase's servers is encrypted on disk.

**No action needed for V1** -- this is already handled by the platform.

### C3. Phone Numbers and Contact Info in the Database

Phone numbers and names in your Supabase database are protected by:
1. Encryption at rest (Supabase default)
2. RLS policies (only your authenticated user can read them)
3. Supabase Auth (JWT required for access)

**SHOULD HAVE (V1)**: Store phone numbers in a consistent format (E.164: +16195551234). This makes searching and deduplication easier later. No additional encryption of individual fields is needed for V1.

**NICE TO HAVE (V2+)**: Column-level encryption for phone numbers using Postgres `pgcrypto`. Only worth it if you are handling many contacts or have regulatory requirements.

### C4. API Keys on the Server -- Environment Variables Only

Your FastAPI server needs these secrets:
- `ANTHROPIC_API_KEY` (for Claude parsing)
- `OPENAI_API_KEY` (for Whisper transcription) or equivalent
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`

**MUST HAVE (V1)**:
- All secrets stored as **environment variables** on your hosting platform (Railway/Render dashboard)
- **Never** in source code, config files committed to git, or Docker images
- Commit a `.env.example` file with placeholder values (no real keys)
- `.env` in `.gitignore` (verify this before first push)

Sources:
- [Railway Variables Documentation](https://docs.railway.com/variables)
- [Render Environment Variables](https://render.com/docs/configure-environment-variables)

### C5. What Should NEVER Be Logged

**MUST HAVE (V1)** -- Configure your FastAPI logging to **never** output:
- Full transcription text (contains names, phone numbers, business details)
- API keys or tokens (even partial)
- Phone numbers or contact names
- Audio file contents or paths that reveal personal information
- Full request/response bodies on AI API calls

**What IS safe to log**:
- Request IDs and timestamps
- HTTP status codes
- Processing duration (e.g., "Transcription completed in 4.2s")
- Error types (e.g., "TranscriptionError: audio too short") without the content
- Recording metadata (file size, duration, format) without personal content

**Implementation**: Use Python's `logging` module with a custom formatter that redacts sensitive patterns. At minimum, never log `request.body` on the upload or parse endpoints.

Sources:
- [Best Logging Practices for Safeguarding Sensitive Data](https://betterstack.com/community/guides/logging/sensitive-data/)
- [How to Keep Sensitive Data Out of Your Logs](https://www.skyflow.com/post/how-to-keep-sensitive-data-out-of-your-logs-nine-best-practices)

---

## D. Third-Party API Security

### D1. OpenAI Whisper API Data Retention

**Current policy (as of 2025)**:
- API data is retained for **up to 30 days** for abuse monitoring, then deleted
- API data is **NOT used for model training** by default (you must explicitly opt in)
- Audio files sent to the Whisper API are processed and temporarily stored under these terms

**Actionable**: The 30-day retention means OpenAI holds your audio recordings (containing names, phone numbers, business observations) for up to a month. For V1 with a single user, this is acceptable. For future versions with more users or stricter privacy requirements, consider local Whisper (see D3).

Sources:
- [OpenAI Data Usage Policy](https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/)
- [OpenAI Community - API Data for Training](https://community.openai.com/t/does-open-ai-api-use-api-data-for-training/659053)

### D2. Anthropic Claude API Data Retention

**Current policy (as of 2025)**:
- API logs retained for **7 days** (as of September 2025 update), then auto-deleted
- API data is **NOT used for model training**
- Zero data retention agreements are available for enterprise customers
- Commercial API terms are separate from consumer terms

**Actionable**: Anthropic's 7-day retention is quite short and reasonable. Your parsed transcripts (containing contact names, venue details) are held briefly, then deleted. This is acceptable for V1.

Sources:
- [Anthropic Privacy Center - Organization Data Retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)
- [Claude Data Retention Overview](https://www.datastudios.org/post/claude-data-retention-policies-storage-rules-and-compliance-overview)

### D3. Privacy-Preserving Alternative: Local Whisper

Running Whisper locally on your FastAPI server means audio never leaves your infrastructure.

**Trade-offs**:

| Factor | OpenAI Whisper API | Local Whisper (faster-whisper) |
|--------|-------------------|-------------------------------|
| Privacy | 30-day retention at OpenAI | Audio never leaves your server |
| Cost | ~$0.006/min (~$0.03 per 5-min debrief) | Free (but needs server resources) |
| Speed | Fast (OpenAI infrastructure) | Depends on server CPU/GPU |
| Quality | Excellent | Same model, same quality |
| Server requirements | None | CPU: slow (30-60s for 5min). GPU: fast but expensive hosting |
| Maintenance | None | You manage the model |

**Recommendation for V1**: Use the OpenAI Whisper API. The cost is negligible ($0.30-0.60/month at 8-10 events), the privacy exposure is acceptable for a single-user app, and it avoids the complexity of GPU hosting.

**NICE TO HAVE (V2+)**: Switch to `faster-whisper` running locally on the FastAPI server. This eliminates the OpenAI dependency entirely. Only worth it when privacy requirements increase (e.g., if the tool is sold to other performers).

Sources:
- [Local Whisper vs Cloud Transcription Comparison](https://sotto.to/blog/whisper-local-vs-cloud)
- [OpenAI Whisper for Developers - AssemblyAI](https://www.assemblyai.com/blog/openai-whisper-developers-choosing-api-local-server-side-transcription)

### D4. API Key Compromise Response

If your API keys are compromised:
- **OpenAI**: Immediately rotate at platform.openai.com. Set spending limits ($10/month is plenty for your usage).
- **Anthropic**: Immediately rotate at console.anthropic.com. Set spending limits.
- **Supabase**: Rotate the service_role key via the Supabase dashboard. The anon key is less critical (it relies on RLS), but rotate it too.

**MUST HAVE (V1)**:
- Set **spending limits** on both OpenAI and Anthropic accounts (e.g., $10/month hard cap)
- Know how to rotate each key (bookmark the rotation pages)

**SHOULD HAVE (V1)**:
- Set up billing alerts at 50% and 80% of your spending limit
- Document the key rotation procedure somewhere accessible

### D5. Rate Limiting and Outage Handling

**SHOULD HAVE (V1)**: Graceful handling of third-party API failures:
- If Whisper API is down: Queue the audio for retry, show the user "Transcription pending"
- If Claude API is down: Store the transcript, queue for parsing later, show "Parsing pending"
- Implement exponential backoff on retries (do not hammer a failing API)

This aligns with the brainstorm's "offline recording queue" concept -- the same queue mechanism handles both no-connectivity and API-outage scenarios.

---

## E. Mobile App Security

### E1. expo-secure-store -- The Foundation

As covered in B2, use `expo-secure-store` for all sensitive data on the device. This is non-negotiable.

**What goes in expo-secure-store**:
- Authentication tokens (JWT, refresh token)
- Supabase URL and anon key (can also be in app config, but secure-store is safer)

**What does NOT go in expo-secure-store**:
- Large data (venue records, contact lists) -- these should be in Supabase with local caching via AsyncStorage or SQLite (not sensitive once authenticated)
- Audio files (too large; use the device filesystem with proper cleanup)

### E2. Phone Lost or Stolen

If the phone is lost, what is exposed?

**Without app-level lock**:
- Cached venue/contact data in AsyncStorage (if any) -- readable on rooted device
- Auth tokens in expo-secure-store -- protected by device lock (PIN/biometric)
- Audio files queued for upload -- readable on filesystem
- The app itself is accessible if the phone has no device-level lock

**With device-level lock (PIN/Face ID)**:
- expo-secure-store data is encrypted and inaccessible without the device PIN
- AsyncStorage is still readable if the device is rooted/jailbroken after unlock
- Audio files are accessible after device unlock

**MUST HAVE (V1)**:
- Store auth tokens in expo-secure-store (not AsyncStorage)
- Delete audio files from the device after successful upload
- Rely on the device's own lock screen as the primary protection

**NICE TO HAVE (V2+)**: App-level PIN/biometric lock using `expo-local-authentication`. This adds a second layer -- even if someone bypasses the device lock, the app itself requires authentication. Low effort to implement but not critical for a single-user V1 where the owner already locks their phone.

Sources:
- [expo-local-authentication - Expo Documentation](https://docs.expo.dev/versions/latest/sdk/local-authentication/)
- [Biometric Authentication in React Native with Expo](https://blog.logrocket.com/implementing-react-native-biometric-authentication-expo/)

### E3. Audio File Handling on Device

**MUST HAVE (V1)**:
- Record to a temporary directory (not the camera roll or shared storage)
- Delete the local audio file immediately after successful upload confirmation
- If upload fails, keep the file in the queue but do not expose it in the device's media library

### E4. Development vs Production Builds

**MUST HAVE (V1)** -- before shipping:
- Remove all debug endpoints from FastAPI (e.g., `/docs` Swagger UI in production, or password-protect it)
- Disable React Native development menu in production builds
- Ensure no `console.log` statements leak sensitive data
- Use Expo's production build (`eas build --profile production`), not development builds

Sources:
- [10 Mobile App Security Best Practices for React Native 2025](https://market.gluestack.io/blog/mobile-app-security-best-practices)

---

## F. Production Readiness Checklist

### F1. What Solo Developers Commonly Forget

Based on research and community patterns, these are the most frequently missed items:

1. **No error monitoring** -- the app crashes and you do not know until you open it
2. **No spending limits on APIs** -- a bug causes infinite retries, racking up hundreds of dollars overnight
3. **No backup strategy** -- the database corrupts or you accidentally delete data, and there is no recovery path
4. **Secrets in git history** -- the key was removed from the code but it is still in a previous commit
5. **No health check endpoint** -- the server is down and you do not know
6. **Logging PII** -- transcript text with names and phone numbers shows up in Railway/Render logs
7. **Swagger UI exposed** -- anyone can see all your API endpoints and their schemas
8. **No CORS configuration** -- the API accepts requests from any origin
9. **Audio files in public Supabase bucket** -- anyone with the URL can download them
10. **No rate limiting** -- a compromised token allows unlimited API calls

### F2. Error Monitoring -- Sentry

**MUST HAVE (V1)**: Set up Sentry (free tier) for both the FastAPI server and the Expo app.

FastAPI setup is minimal:
```python
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,  # 10% of transactions for performance
    send_default_pii=False,  # IMPORTANT: do not send PII to Sentry
)
```

**Critical**: Set `send_default_pii=False`. You do not want contact names and phone numbers showing up in your Sentry dashboard.

For the Expo app, use `@sentry/react-native` (there is an Expo plugin: `sentry-expo`).

Sources:
- [FastAPI Error & Performance Monitoring - Sentry](https://sentry.io/for/fastapi/)
- [Sentry FastAPI Integration Docs](https://docs.sentry.io/platforms/python/integrations/fastapi/)

### F3. Backup Strategy

**MUST HAVE (V1)**: Supabase Pro plan includes daily automatic backups with 7-day retention. The free tier has no backups.

**Recommendation**: Start on Supabase's free tier for development, but **upgrade to Pro ($25/month) before going to production** for automatic backups. The cost of losing your entire venue/contact database is far higher than $25/month.

**SHOULD HAVE (V1)**: A manual backup script that exports key tables (venues, contacts, events) to JSON/CSV and saves to a secure location (e.g., an encrypted local folder or a private Google Drive). Run it weekly.

### F4. What to Monitor

**MUST HAVE (V1)** -- minimal monitoring:
- **Health check endpoint**: `GET /health` returns 200 if the server is up and can reach Supabase
- **Sentry alerts**: Email notification on any unhandled exception
- **API spending**: Check OpenAI and Anthropic dashboards weekly (set billing alerts)

**SHOULD HAVE (V1)**:
- Uptime monitoring: Use a free service (UptimeRobot, Better Stack free tier) to ping your health endpoint every 5 minutes and alert you if it goes down
- Track transcription success rate (simple counter in logs: "Transcription succeeded" / "Transcription failed")

### F5. Incident Response -- Server Down During a Gig Weekend

The app's core value is **recording voice memos**. If the server is down:

1. **Recording still works** (if offline queue is implemented in V1): Audio is saved locally, queued for upload
2. **Transcription and parsing are delayed** until the server is back
3. **Existing data is inaccessible** if cached locally (gig prep mode depends on server for V1)

**MUST HAVE (V1)**:
- Offline recording queue (already in the brainstorm as Session 11) -- this is also your incident resilience strategy
- Clear user feedback: "Recording saved. Will process when connection is available."

**SHOULD HAVE (V1)**:
- Basic local caching of recent venue data for gig prep (so you can review venue details even if server is down)

### F6. Cost Monitoring

Expected monthly costs at 8-10 events/month:

| Service | Estimated Cost | Notes |
|---------|---------------|-------|
| OpenAI Whisper API | $0.30-0.60 | ~50 min audio/month at $0.006/min |
| Anthropic Claude API | $0.50-1.00 | ~10 parse calls/month |
| Supabase (Pro) | $25.00 | Includes backups, 8GB storage |
| Railway/Render hosting | $5-7 | Starter tier for FastAPI |
| Sentry | $0 | Free tier (5K errors/month) |
| **Total** | **~$31-34/month** | |

**MUST HAVE (V1)**:
- Hard spending caps on OpenAI ($10/month) and Anthropic ($10/month)
- Monthly review of actual costs vs estimates

---

## G. What Can Go Wrong -- Threat Model and Mitigations

### G1. API Keys Committed to Git

**Risk**: High. Once in git history, the key is permanently exposed (even if the file is deleted).

**MUST HAVE (V1)**:
- `.env` in `.gitignore` before the first commit
- Install `gitleaks` as a pre-commit hook:
  ```yaml
  # .pre-commit-config.yaml
  repos:
    - repo: https://github.com/gitleaks/gitleaks
      rev: v8.24.2
      hooks:
        - id: gitleaks
  ```
- Run `gitleaks detect` on the repo before first production deploy to scan history
- Commit a `.env.example` with placeholder values

Sources:
- [Gitleaks - GitHub](https://github.com/gitleaks/gitleaks)
- [Pre-commit Secret Scanning Guide](https://m3ssap0.github.io/2023/09/29/pre-commit-gitleaks.html)

### G2. Supabase RLS Misconfiguration

**Risk**: Critical. Without RLS, anyone with the anon key (which is in your app's JavaScript bundle) can read/write your entire database.

**MUST HAVE (V1)**:
- Enable RLS on EVERY table
- Write explicit policies (do not rely on defaults): `auth.uid() = user_id` for SELECT, INSERT, UPDATE, DELETE
- **Test RLS from the client SDK**, not the SQL editor (SQL editor bypasses RLS)
- Add `user_id UUID REFERENCES auth.users(id)` to every table

**Testing approach**: After setting up RLS, try to access data without authentication using `curl` or Postman with just the anon key. You should get zero rows.

### G3. Audio Files Accessible Without Authentication

**Risk**: High. If the Supabase Storage bucket is public, anyone can construct a URL to download audio files.

**MUST HAVE (V1)**:
- Use a **private** Supabase Storage bucket for audio files
- Access audio via **signed URLs** with short expiration (e.g., 60 seconds)
- RLS policies on the storage bucket: only the authenticated user can read/write

### G4. Server Logs Containing Personal Information

**Risk**: Medium. Railway and Render store your stdout/stderr logs. If transcripts or contact names appear in logs, they are accessible to anyone with your platform account.

**MUST HAVE (V1)**: Never log:
- Full or partial transcript text
- Contact names, phone numbers, or company names
- Full request bodies on AI endpoints
- API keys or tokens

Use structured logging with explicit fields, not string interpolation of request data.

### G5. Phone Stolen with Cached Data

**Risk**: Medium (mitigated by device lock).

**MUST HAVE (V1)**:
- Auth tokens in expo-secure-store (protected by device lock)
- Delete audio files from device after successful upload
- Do not cache contact phone numbers in AsyncStorage

**NICE TO HAVE (V2+)**:
- Remote token revocation (log out of all devices via Supabase dashboard)
- App-level biometric lock

### G6. Expo Development Builds with Debug Endpoints

**Risk**: Medium. Development builds include the React Native dev menu, Expo debugger, and often connect to development servers.

**MUST HAVE (V1)** -- before shipping:
- Build with `eas build --profile production`
- Verify no development-only code paths remain (React Native `__DEV__` flag should disable debug features)
- Disable or password-protect FastAPI's `/docs` and `/redoc` Swagger endpoints in production:
  ```python
  app = FastAPI(docs_url=None, redoc_url=None)  # Disable in production
  ```

### G7. Third-Party API Outage During Critical Recording

**Risk**: Low impact (if offline queue exists). The recording is safe on the device.

**MUST HAVE (V1)**:
- Offline recording queue with local storage
- Clear UI state: "Saved locally. Will process when server is available."
- Retry logic with exponential backoff when connectivity returns

---

## V1 Checklist Summary

### MUST HAVE (Ship-Blocking)

| # | Item | Section |
|---|------|---------|
| 1 | Supabase Auth with single user account, JWT on all endpoints | B1 |
| 2 | expo-secure-store for auth tokens (not AsyncStorage) | B2, E1 |
| 3 | HTTPS on all communications | B3 |
| 4 | RLS enabled on every Supabase table, tested from client | B5, G2 |
| 5 | Private Supabase Storage bucket with signed URLs for audio | G3 |
| 6 | All API keys in environment variables, never in code | C4 |
| 7 | .env in .gitignore, gitleaks pre-commit hook installed | G1 |
| 8 | Spending limits on OpenAI and Anthropic accounts | D4, F6 |
| 9 | Delete audio from device after successful upload | E3 |
| 10 | Delete audio from server 7 days after transcription | A4 |
| 11 | Sentry error monitoring (send_default_pii=False) | F2 |
| 12 | Never log PII (transcripts, names, phone numbers) | C5, G4 |
| 13 | Simple privacy policy hosted at a URL | A3 |
| 14 | Disable FastAPI /docs and /redoc in production | G6 |
| 15 | Production Expo build (not development) | G6 |
| 16 | Health check endpoint on FastAPI | F4 |
| 17 | Recording screen disclaimer about not recording conversations | A1 |
| 18 | Offline recording queue (also covers API outages) | G7, F5 |

### SHOULD HAVE (Strongly Recommended for V1)

| # | Item | Section |
|---|------|---------|
| 19 | Basic rate limiting on upload endpoint (slowapi) | B4 |
| 20 | CORS configuration (restrict origins) | B4 |
| 21 | Uptime monitoring (UptimeRobot free tier) | F4 |
| 22 | Supabase Pro plan for automatic backups | F3 |
| 23 | Billing alerts at 50% and 80% of spending limits | D4 |
| 24 | Graceful API failure handling with retry queue | D5 |
| 25 | E.164 phone number format for consistency | C3 |
| 26 | Weekly manual backup export of key tables | F3 |

### NICE TO HAVE (V2+)

| # | Item | Section |
|---|------|---------|
| 27 | App-level biometric/PIN lock (expo-local-authentication) | E2 |
| 28 | Local Whisper (faster-whisper) for full privacy | D3 |
| 29 | Client-side audio encryption before upload | C1 |
| 30 | Column-level encryption for phone numbers (pgcrypto) | C3 |
| 31 | Automated contact deletion function | A5 |
| 32 | Remote token revocation capability | G5 |

---

## Key Takeaway

The biggest risks for PF-Intel V1 are not exotic attacks -- they are **configuration mistakes**:
1. Leaving RLS disabled on a Supabase table
2. Committing an API key to git
3. Using a public Supabase Storage bucket
4. Logging transcript text with personal information

These four items alone account for the vast majority of real-world breaches in apps like this. Get these right and the single-user V1 is well-protected. The rest of the checklist layers defense in depth around these fundamentals.
