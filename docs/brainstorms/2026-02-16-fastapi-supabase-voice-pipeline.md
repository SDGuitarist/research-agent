# FastAPI + Supabase Voice-to-Data Pipeline: Research Brainstorm

**Date:** 2026-02-16
**Scope:** Best practices, edge cases, and pitfalls for a Python FastAPI backend with Supabase serving an Expo mobile app. Pipeline: audio upload -> Whisper transcription -> Claude parsing -> structured data.

---

## A. FastAPI Project Structure

### Recommended Directory Layout

For a solo developer directing Claude Code, the **file-type structure** (not domain-driven) is the right starting point. It is simpler to navigate, maps directly to FastAPI's own tutorial, and avoids premature abstraction. You can refactor to domain-driven later when you have 4+ distinct feature areas.

```
pf-intel/
  app/
    __init__.py
    main.py              # FastAPI() instance, startup/shutdown, include_router()
    config.py            # Pydantic BaseSettings, all env vars
    dependencies.py      # Shared deps: get_supabase, get_current_user, get_settings
    routers/
      __init__.py
      audio.py           # POST /audio/upload, GET /audio/{id}/status
      transcriptions.py  # GET /transcriptions/{id}
      health.py          # GET /health
    services/
      __init__.py
      transcription.py   # Whisper API call logic
      parsing.py         # Claude API call logic
      pipeline.py        # Orchestrates: upload -> transcribe -> parse -> store
      storage.py         # Supabase Storage operations
    models/
      __init__.py
      schemas.py         # Pydantic request/response models
      database.py        # Supabase table schemas (documentation, not ORM)
    middleware/
      __init__.py
      error_handler.py   # Global exception handlers
    utils/
      __init__.py
      logging.py         # Structured logging config
  tests/
    __init__.py
    conftest.py          # Fixtures: mock_supabase, test_client, etc.
    test_audio.py
    test_pipeline.py
  Dockerfile
  pyproject.toml
  .env.example
  .env                   # Never committed
```

**Source:** [FastAPI Official - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)

### Router Organization

Each router gets its own file under `routers/`. Include them in `main.py`:

```python
# app/main.py
from fastapi import FastAPI
from app.routers import audio, transcriptions, health

app = FastAPI(title="PF Intel API", version="0.1.0")

app.include_router(health.router, tags=["health"])
app.include_router(audio.router, prefix="/api/v1", tags=["audio"])
app.include_router(transcriptions.router, prefix="/api/v1", tags=["transcriptions"])
```

Each router file:

```python
# app/routers/audio.py
from fastapi import APIRouter, Depends, UploadFile, File
from app.dependencies import get_supabase

router = APIRouter(prefix="/audio")

@router.post("/upload")
async def upload_audio(file: UploadFile = File(...), supabase=Depends(get_supabase)):
    ...
```

**Key rule:** Routers contain only HTTP-layer logic (validate input, call service, return response). Business logic lives in `services/`.

### Dependency Injection

FastAPI's `Depends()` is the core pattern. Create all shared dependencies in one file:

```python
# app/dependencies.py
from functools import lru_cache
from supabase import create_client, Client
from app.config import Settings

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Create Supabase client ONCE (httpx client creation is slow)
_supabase_client: Client | None = None

def get_supabase(settings: Settings = Depends(get_settings)) -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client
```

**Critical pitfall:** supabase-py creates an httpx client every time you call `create_client()`. This is slow. Create the client once at startup, not per request. The `@lru_cache` pattern on settings is from FastAPI's official docs.

**Source:** [FastAPI Official - Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)

### Configuration Management

Use `pydantic-settings` (separate package from pydantic since v2):

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase
    supabase_url: str
    supabase_key: str          # anon key for client operations
    supabase_service_key: str  # service role key for admin operations

    # APIs
    anthropic_api_key: str
    openai_api_key: str        # for Whisper API

    # App
    environment: str = "development"
    debug: bool = False
    max_audio_size_mb: int = 100
    allowed_audio_types: list[str] = ["audio/mpeg", "audio/wav", "audio/m4a", "audio/ogg"]
```

**Install:** `pip install pydantic-settings`

**.env.example** (committed to git, documents required vars):
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
ENVIRONMENT=development
```

### Logging

Use Python's built-in `logging` with structured output. Do not use `print()`.

```python
# app/utils/logging.py
import logging
import sys

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

# Usage in any module:
logger = logging.getLogger(__name__)
logger.info("Processing audio file", extra={"file_id": file_id})
```

For production, consider `structlog` for JSON-formatted logs that Railway/Render can parse.

---

## B. FastAPI + Supabase Integration

### Which Client Library to Use

**Recommendation: Use supabase-py for everything at your scale.**

| Approach | Pros | Cons | When to use |
|----------|------|------|-------------|
| **supabase-py** | Simple API, includes storage + auth, matches Supabase docs | Not async-native, no connection pooling | Solo dev, < 100 req/min |
| **asyncpg + SQLAlchemy** | True async, connection pooling, raw performance | Complex setup, Supabase pooler quirks, no storage API | High-concurrency production |
| **psycopg3** | Modern, async support, prepared statements | Manual SQL, no Supabase storage integration | Performance-critical queries |

For 8-10 voice requests/month plus data serving, supabase-py is the correct choice. Do not over-engineer with asyncpg unless you hit connection limits.

**Source:** [Supabase Connection Scaling Guide for FastAPI](https://medium.com/@papansarkar101/supabase-connection-scaling-the-essential-guide-for-fastapi-developers-2dc5c428b638), [Supabase Pooling and asyncpg Issues](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249)

### Supabase Client Setup in FastAPI

```python
# app/dependencies.py
from supabase import create_client, Client
from app.config import Settings

# Module-level singleton -- created once at import time
_settings = Settings()
_supabase: Client = create_client(_settings.supabase_url, _settings.supabase_key)

def get_supabase() -> Client:
    """Dependency: returns the shared Supabase client."""
    return _supabase
```

Alternatively, use FastAPI's lifespan events for cleaner setup:

```python
# app/main.py
from contextlib import asynccontextmanager
from supabase import create_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.supabase = create_client(settings.supabase_url, settings.supabase_key)
    yield
    # Shutdown (cleanup if needed)

app = FastAPI(lifespan=lifespan)
```

### Connection Pooling

Supabase provides two pooler modes via Supavisor:

- **Transaction mode (port 6543):** Recommended for web backends. Connection released after each transaction. Maximizes concurrency.
- **Session mode (port 5432):** Connection held for entire session. Limited to pool size (20 on free tier).

**For supabase-py:** You do not need to worry about pooling -- the client uses Supabase's REST API (PostgREST), not direct Postgres connections. The pooler matters only if you use asyncpg/SQLAlchemy with a direct Postgres connection string.

**Free tier limits:**
- 20 direct Postgres connections (Session mode)
- 200 connections through pooler (Transaction mode)
- PostgREST (what supabase-py uses): effectively unlimited at low traffic

### Supabase File Storage from FastAPI

Upload audio files to Supabase Storage:

```python
# app/services/storage.py
from supabase import Client
import uuid

async def upload_audio(supabase: Client, file_content: bytes, content_type: str) -> str:
    """Upload audio to Supabase Storage, return the file path."""
    file_id = str(uuid.uuid4())
    extension = content_type.split("/")[-1]  # e.g., "mpeg" -> "mpeg"
    file_path = f"audio/{file_id}.{extension}"

    supabase.storage.from_("audio-uploads").upload(
        file_path,
        file_content,
        {"content-type": content_type, "upsert": "false"}
    )
    return file_path

async def download_audio(supabase: Client, file_path: str) -> bytes:
    """Download audio from Supabase Storage."""
    return supabase.storage.from_("audio-uploads").download(file_path)

async def delete_audio(supabase: Client, file_path: str):
    """Clean up audio after processing."""
    supabase.storage.from_("audio-uploads").remove([file_path])
```

**Setup required in Supabase Dashboard:**
1. Create a storage bucket called `audio-uploads`
2. Set it to private (not public)
3. Set max file size (100MB should cover 15-minute audio files)

### Row Level Security (RLS)

**For a single-user app with a backend that uses the service role key: RLS is not enforced.**

The service role key bypasses RLS entirely. This means:
- You do not need to set up RLS policies for your backend operations
- Your backend has full access to all data
- RLS becomes important only if your mobile app ever talks directly to Supabase (it should not -- always go through your FastAPI backend)

**Recommendation:** Keep RLS enabled on tables with a permissive policy for authenticated users. This is a safety net in case you ever add direct client access later.

### Migrations

**Recommendation: Use Supabase Dashboard + SQL migrations for your scale.**

| Approach | Complexity | When to use |
|----------|-----------|-------------|
| Supabase Dashboard (GUI) | Simplest | Prototyping, < 5 tables |
| Supabase CLI migrations | Medium | Team projects, CI/CD |
| Alembic | Complex | Heavy SQLAlchemy usage, existing Alembic expertise |

For a solo developer with a few tables:
1. Design tables in the Supabase Dashboard
2. Export the SQL (Supabase Dashboard > SQL Editor)
3. Save migration files in `supabase/migrations/` in your repo for version control
4. Apply changes through the Dashboard

When the app grows, move to `supabase db diff` and `supabase db push` via the Supabase CLI.

---

## C. Audio Upload Endpoint

### File Size Considerations

A 15-minute audio file is roughly:
- MP3 (128kbps): ~14 MB
- WAV (uncompressed): ~150 MB
- M4A (AAC): ~10 MB

**OpenAI Whisper API limit: 25 MB per file.** This is the binding constraint. If users upload WAV files > 25MB, you must either:
1. Convert to a compressed format before sending to Whisper, or
2. Split the audio into chunks

### Upload Endpoint Design

```python
# app/routers/audio.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from app.config import Settings
from app.dependencies import get_supabase, get_settings
from app.services.pipeline import process_audio_pipeline

router = APIRouter(prefix="/audio")

MAX_SIZE = 100 * 1024 * 1024  # 100 MB

@router.post("/upload", status_code=202)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    supabase = Depends(get_supabase),
):
    # 1. Validate file type
    if file.content_type not in settings.allowed_audio_types:
        raise HTTPException(400, f"Unsupported type: {file.content_type}")

    # 2. Read file content (must read BEFORE background task -- UploadFile closes)
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, f"File too large. Max: {MAX_SIZE // (1024*1024)} MB")

    # 3. Generate job ID
    import uuid
    job_id = str(uuid.uuid4())

    # 4. Store initial job record
    supabase.table("jobs").insert({
        "id": job_id,
        "status": "uploaded",
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": len(content),
    }).execute()

    # 5. Kick off background processing
    background_tasks.add_task(
        process_audio_pipeline,
        job_id=job_id,
        audio_content=content,  # Pass bytes, NOT UploadFile
        content_type=file.content_type,
        supabase=supabase,
        settings=settings,
    )

    # 6. Return immediately with job ID
    return {"job_id": job_id, "status": "processing"}


@router.get("/{job_id}/status")
async def get_job_status(job_id: str, supabase = Depends(get_supabase)):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Job not found")
    return result.data
```

### Critical Pitfall: UploadFile Closes After Response

**This is the number one mistake developers make with FastAPI file uploads + background tasks.** The `UploadFile` object is backed by a SpooledTemporaryFile that gets closed when the response is sent. If you pass the `UploadFile` to a background task, it will be closed and unreadable.

**The fix:** Read the file content (`await file.read()`) in the endpoint handler and pass the `bytes` to the background task, not the UploadFile object.

**Source:** [FastAPI Discussion #10936 - UploadFile and BackgroundTasks](https://github.com/fastapi/fastapi/discussions/10936)

### Sync vs Async: Return Immediately (HTTP 202)

**Recommendation: Async with polling.** Return HTTP 202 (Accepted) immediately, process in background, let the mobile app poll for status.

**Why not synchronous (wait for full pipeline)?**
- Whisper transcription of 15 min audio: 30-90 seconds
- Claude parsing: 5-15 seconds
- Total: 35-105 seconds
- Most HTTP clients (and mobile frameworks) timeout at 30-60 seconds
- Railway/Render request timeout: typically 30 seconds (configurable to 5 min)
- Users staring at a spinner for 90 seconds is bad UX

**Polling pattern:**
1. Mobile app calls `POST /api/v1/audio/upload` -> gets back `{job_id, status: "processing"}`
2. Mobile app polls `GET /api/v1/audio/{job_id}/status` every 3-5 seconds
3. Status progresses: `uploaded -> transcribing -> parsing -> completed` (or `failed`)
4. When `completed`, the response includes the structured data

### Background Task Processing: Which Tool?

| Tool | Complexity | Reliability | Use when |
|------|-----------|-------------|----------|
| **FastAPI BackgroundTasks** | Simplest | Low (in-process, lost on crash) | < 50 jobs/day, okay to lose a job |
| **ARQ (async Redis queue)** | Medium | Medium (Redis-backed, retries) | Need retries, moderate volume |
| **Celery + Redis** | Complex | High (battle-tested, retries, monitoring) | High volume, mission-critical |

**Recommendation for your use case: Start with FastAPI BackgroundTasks.**

At 8-10 requests/month, Celery is massive overkill. BackgroundTasks runs in-process, requires no Redis, and is zero-configuration. The risk (job lost on crash) is acceptable when you can just re-upload.

**Upgrade path:** If you later need retries and crash recovery, migrate to ARQ (much lighter than Celery, built for async Python).

### Pipeline Service

```python
# app/services/pipeline.py
import logging
from app.services.transcription import transcribe_audio
from app.services.parsing import parse_transcript
from app.services.storage import upload_audio, delete_audio

logger = logging.getLogger(__name__)

async def process_audio_pipeline(
    job_id: str,
    audio_content: bytes,
    content_type: str,
    supabase,
    settings,
):
    """Full pipeline: upload -> transcribe -> parse -> store results."""
    try:
        # 1. Upload to Supabase Storage
        _update_status(supabase, job_id, "uploading_storage")
        file_path = await upload_audio(supabase, audio_content, content_type)

        # 2. Transcribe with Whisper
        _update_status(supabase, job_id, "transcribing")
        transcript = await transcribe_audio(audio_content, settings.openai_api_key)

        # 3. Parse with Claude
        _update_status(supabase, job_id, "parsing")
        structured_data = await parse_transcript(transcript, settings.anthropic_api_key)

        # 4. Store results
        _update_status(supabase, job_id, "storing")
        supabase.table("results").insert({
            "job_id": job_id,
            "transcript": transcript,
            "structured_data": structured_data,
        }).execute()

        # 5. Clean up audio from storage (optional -- keep if you want replay)
        # await delete_audio(supabase, file_path)

        # 6. Mark complete
        _update_status(supabase, job_id, "completed")

    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}")
        supabase.table("jobs").update({
            "status": "failed",
            "error": str(e)[:500],  # Truncate error message
        }).eq("id", job_id).execute()


def _update_status(supabase, job_id: str, status: str):
    supabase.table("jobs").update({"status": status}).eq("id", job_id).execute()
```

### What Happens If the Server Crashes Mid-Processing?

With FastAPI BackgroundTasks, the job is lost. Mitigations:

1. **Status tracking in database:** The mobile app sees `status: "transcribing"` and knows the job stalled. Show a "retry" button if status has not changed in 5 minutes.
2. **Startup recovery:** On app startup, query for jobs with status not in `("completed", "failed")` and mark them as `"failed_crash"`. The user can re-upload.
3. **Idempotent operations:** Design the pipeline so re-running it with the same audio produces the same result with no side effects.

```python
# In main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mark stale jobs as failed on startup
    supabase.table("jobs").update(
        {"status": "failed_crash", "error": "Server restarted during processing"}
    ).not_.is_("status", "completed").not_.is_("status", "failed").execute()
    yield
```

---

## D. Deployment (Beginner-Friendly)

### Platform Comparison

| Factor | Railway | Render | Fly.io |
|--------|---------|--------|--------|
| **Beginner friendliness** | Best | Great | Harder |
| **Deploy from git push** | Yes | Yes | Yes (with config) |
| **Pricing model** | Usage-based | Flat-rate | Usage-based |
| **Free tier** | $5 trial credit | Free tier (750 hrs/mo, sleeps after 15 min inactivity) | $5 trial credit |
| **Minimum paid cost** | ~$5/mo | $7/mo (Starter instance) | ~$3-5/mo |
| **Request timeout** | Configurable | 5 min max | Configurable |
| **Docker support** | Native | Native | Native |
| **Managed Postgres** | Yes | Yes | Yes |
| **Environment vars GUI** | Yes | Yes | Yes (via fly secrets) |

**Recommendation: Railway for the prototype, Render for production.**

- Railway: Fastest from zero-to-deployed. Connect GitHub repo, it detects Python, deploys. Usage-based pricing means near-zero cost at 8-10 requests/month.
- Render: More predictable pricing and mature platform. Better docs. Auto-deploys from git. Good for when you want stability.

**Source:** [Railway vs Fly.io vs Render Comparison](https://medium.com/ai-disruption/railway-vs-fly-io-vs-render-which-cloud-gives-you-the-best-roi-2e3305399e5b), [Python Hosting Comparison](https://www.nandann.com/blog/python-hosting-options-comparison)

### Whisper: API vs Self-Hosted

**Use the OpenAI Whisper API. Do not self-host.**

At 8-10 files/month of 15 minutes each: ~150 minutes/month

- **API cost:** 150 min x $0.006/min = **$0.90/month**
- **Self-hosted GPU:** Minimum ~$276/month for an always-on GPU instance

Self-hosting only makes sense at 10,000+ hours/month. The API is 300x cheaper at your scale.

**Alternative to consider:** OpenAI's newer `gpt-4o-mini-transcribe` at $0.003/min ($0.45/month for your usage) offers similar quality at half the price.

**Source:** [Whisper API Pricing Analysis](https://brasstranscripts.com/blog/openai-whisper-api-pricing-2025-self-hosted-vs-managed)

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ app/

# Don't run as root
RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Note:** Use Python 3.12-slim, not 3.14. Railway and Render support 3.12 reliably. Python 3.14 is too bleeding-edge for container deployments.

### Environment Variables on Deployment

On Railway/Render, set environment variables through their web dashboard:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `ENVIRONMENT=production`

Never put secrets in your Dockerfile, docker-compose, or git repo.

### Cost Estimates (8-10 voice requests/month + data serving)

| Service | Monthly Cost |
|---------|-------------|
| Railway/Render hosting | $5-7 |
| Supabase (free tier) | $0 |
| OpenAI Whisper API | ~$0.90 |
| Claude API (parsing) | ~$0.50 (depends on prompt size) |
| **Total** | **~$6-9/month** |

### CI/CD

Both Railway and Render auto-deploy on git push to main. No additional CI/CD needed for your scale.

For basic validation before deploy, add a GitHub Action:

```yaml
# .github/workflows/test.yml
name: Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[test]"
      - run: pytest tests/ -v
```

### Health Check Endpoint

Required for Railway/Render to know your app is alive:

```python
# app/routers/health.py
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

Configure the health check path in your platform dashboard (Railway: Settings > Health Check Path > `/health`).

---

## E. API Design for Mobile

### REST API Design

Keep it simple. Three core endpoints:

```
POST   /api/v1/audio/upload          # Upload audio, start processing
GET    /api/v1/audio/{job_id}/status  # Poll for processing status
GET    /api/v1/data                   # Fetch all structured data
GET    /api/v1/data/{id}              # Fetch single structured data item
```

**Versioning:** Prefix with `/api/v1`. When you need breaking changes, add `/api/v2` without removing v1. The mobile app can be pinned to a version.

### Authentication: Simplest Approach for Single User

**Recommendation: Static API key in a custom header.**

For a single-user app that only you use, a full OAuth2/JWT flow is overkill. Use a shared secret:

```python
# app/dependencies.py
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    settings = get_settings()
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

```python
# app/main.py -- apply globally
app.include_router(audio.router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
```

In the Expo app, store the API key in a secure storage (expo-secure-store) and send it with every request:

```typescript
// In Expo app
const response = await fetch(`${API_URL}/api/v1/audio/upload`, {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
  },
  body: formData,
});
```

**Upgrade path:** When you add multiple users, switch to Supabase Auth with JWT verification.

### Error Response Format

Use a consistent error shape that the mobile app can parse predictably:

```python
# app/middleware/error_handler.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
        },
    )

# In main.py
app.add_exception_handler(HTTPException, http_exception_handler)
```

Mobile app always checks:
```typescript
if (data.error) {
  // Show data.message to user
} else {
  // Process data normally
}
```

### CORS: Not Needed for Native Mobile Apps

**CORS is a browser security mechanism.** Native mobile apps (React Native/Expo) are not browsers and do not enforce CORS. You do not need CORSMiddleware for a native-only API.

**However,** add it anyway if you might test from a web browser or add a web admin panel later:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],  # Expo web dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Never use `allow_origins=["*"]` in production** unless the API is intentionally public.

### Rate Limiting

At 8-10 requests/month, rate limiting is not urgent. But as a safety net against accidental infinite loops in the mobile app:

```python
# Use slowapi (simple rate limiting for FastAPI)
# pip install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/upload")
@limiter.limit("10/hour")
async def upload_audio(request: Request, ...):
    ...
```

---

## F. What Can Go Wrong (Failure Modes)

### 1. Memory Issues with Large Audio Files

**Problem:** Reading a 150MB WAV file into memory with `await file.read()` uses 150MB of RAM. On a 512MB Railway container, this can OOM the process.

**Mitigations:**
- Set a hard file size limit (100MB) and reject larger files at the endpoint
- Encourage compressed formats (M4A, MP3) -- 15 min MP3 is ~14MB
- On Railway/Render, use at least 1GB RAM instance ($7/mo) if handling WAV files
- Stream the upload directly to Supabase Storage instead of reading into memory:

```python
# Streaming upload approach (if memory is tight)
import tempfile
import shutil

@router.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    # Write to temp file instead of memory
    with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    # Now process from disk...
```

### 2. Long-Running Requests Timing Out

**Problem:** Platform default timeouts:
- Railway: 30 seconds (configurable)
- Render: 60 seconds for free tier, 5 min for paid
- Fly.io: 60 seconds (configurable)

A synchronous audio pipeline takes 35-105 seconds.

**Solution:** The async pattern (return 202 immediately, poll for results) avoids this entirely. The background task runs independently of the HTTP request timeout.

### 3. Supabase Free Tier Connection Limits

**Problem:** Free tier allows 20 direct Postgres connections. If you accidentally create a new client per request, you exhaust connections.

**Solution:** Use a singleton Supabase client (shown above). supabase-py uses PostgREST (HTTP), not direct Postgres, so connection limits are less relevant. But if you add asyncpg later, use Transaction mode (port 6543).

**Additional free tier gotcha:** Projects inactive for 7 days get paused. For a low-traffic app, set up a cron ping (GitHub Actions, UptimeRobot free tier) to hit your `/health` endpoint daily.

### 4. Cold Starts on Container Platforms

**Problem:** Render's free tier sleeps after 15 minutes of inactivity. First request after sleep takes 30-60 seconds to boot.

**Mitigations:**
- Use Render's paid Starter tier ($7/mo) which stays awake
- Railway: Does not sleep on paid plan, but trial credit depletes
- Add a cron job to ping `/health` every 10 minutes (keeps the container warm)
- UptimeRobot (free tier) can do this for you

### 5. Claude API or Whisper API Is Down

**Problem:** External API outages will fail your pipeline.

**Mitigations:**
- Wrap API calls in retry logic with exponential backoff:

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
async def transcribe_audio(audio_content: bytes, api_key: str) -> str:
    """Call Whisper API with retries."""
    # ... API call here
```

- Store the job status as `"failed"` with the error message so the user can retry
- Consider a fallback: if Whisper fails, try Deepgram or AssemblyAI (future enhancement)
- Monitor API status pages: [OpenAI Status](https://status.openai.com), [Anthropic Status](https://status.anthropic.com)

### 6. Database Migration Failures

**Problem:** Applying a migration that breaks existing data.

**Mitigations:**
- Always back up before migrations (Supabase Dashboard > Database > Backups)
- Test migrations on a staging project first (Supabase free tier allows multiple projects)
- Use additive migrations: add columns with defaults, never rename or drop columns directly
- For your scale, migrations are manual and rare -- the risk is low

### 7. Orphaned Audio Files in Storage

**Problem:** Audio uploaded to Supabase Storage but pipeline fails, leaving files that never get cleaned up.

**Mitigations:**
- Add a `storage_path` column to the `jobs` table
- Run a periodic cleanup: delete storage files for jobs older than 7 days

```python
# Cleanup script (run manually or via cron)
from datetime import datetime, timedelta

cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
old_jobs = supabase.table("jobs").select("id, storage_path").lt("created_at", cutoff).execute()

for job in old_jobs.data:
    if job["storage_path"]:
        supabase.storage.from_("audio-uploads").remove([job["storage_path"]])
```

### 8. Whisper API 25MB File Size Limit

**Problem:** User uploads a large WAV file > 25MB. Whisper rejects it.

**Solution:** Convert to MP3 before sending to Whisper:

```python
# pip install pydub
# Requires ffmpeg installed in Docker image
from pydub import AudioSegment
import io

def compress_for_whisper(audio_bytes: bytes, content_type: str) -> bytes:
    """Compress audio to MP3 if it exceeds Whisper's 25MB limit."""
    if len(audio_bytes) <= 25 * 1024 * 1024:
        return audio_bytes

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    mp3_buffer = io.BytesIO()
    audio.export(mp3_buffer, format="mp3", bitrate="64k")
    return mp3_buffer.getvalue()
```

**Docker requirement:** Add `RUN apt-get update && apt-get install -y ffmpeg` to your Dockerfile if using pydub.

### 9. Supabase-py Is Synchronous in an Async Context

**Problem:** supabase-py's operations are synchronous (blocking). In an async FastAPI endpoint, blocking calls can stall the event loop.

**Solution:** For your traffic (8-10 requests/month), this is not a real problem. If it becomes one:

```python
# Wrap synchronous supabase calls in run_in_executor
import asyncio

async def store_result(supabase, job_id, data):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("results").insert(data).execute()
    )
```

Or switch to `supabase[async]` which provides an async client (still experimental as of early 2026).

---

## G. Recommended Database Schema

```sql
-- Supabase SQL Editor

-- Jobs table: tracks pipeline status
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'uploading_storage', 'transcribing', 'parsing', 'storing', 'completed', 'failed', 'failed_crash')),
    filename TEXT,
    content_type TEXT,
    file_size INTEGER,
    storage_path TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Results table: stores pipeline output
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    transcript TEXT,
    structured_data JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Index for polling queries
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_results_job_id ON results(job_id);
```

---

## H. Complete Dependency List

```toml
# pyproject.toml
[project]
name = "pf-intel"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic-settings>=2.0",
    "supabase>=2.0",
    "openai>=1.0",          # Whisper API
    "anthropic>=0.40",       # Claude API
    "python-multipart",      # Required for FastAPI file uploads
    "tenacity>=8.0",         # Retry logic
    "httpx>=0.27",           # HTTP client (used by supabase-py)
]

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx",                 # For TestClient
]
dev = [
    "ruff",                  # Linting
]
```

**Critical:** `python-multipart` is required for `UploadFile` to work. FastAPI will throw a cryptic error without it.

---

## I. Quick-Start Checklist

1. [ ] Create Supabase project (free tier)
2. [ ] Run the SQL schema in Supabase SQL Editor
3. [ ] Create `audio-uploads` storage bucket (private, 100MB limit)
4. [ ] Copy `.env.example` to `.env`, fill in real keys
5. [ ] `pip install -e .`
6. [ ] `uvicorn app.main:app --reload` (local dev)
7. [ ] Test with: `curl -X POST http://localhost:8000/api/v1/audio/upload -H "X-API-Key: your-key" -F "file=@test.mp3"`
8. [ ] Push to GitHub
9. [ ] Connect repo to Railway/Render
10. [ ] Set environment variables in platform dashboard
11. [ ] Configure health check path: `/health`
12. [ ] Test deployed API from Expo app

---

## Sources

### Official Documentation
- [FastAPI - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI - Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI - Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
- [FastAPI - CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Supabase Python Client Documentation](https://supabase.com/docs/reference/python/introduction)
- [Supabase Connection Management](https://supabase.com/docs/guides/database/connection-management)
- [Supabase Storage](https://supabase.com/docs/guides/storage)

### Community Best Practices
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [FastAPI + Supabase Template (AtticusZeller)](https://github.com/AtticusZeller/fastapi_supabase_template)
- [Supabase Connection Scaling Guide for FastAPI](https://medium.com/@papansarkar101/supabase-connection-scaling-the-essential-guide-for-fastapi-developers-2dc5c428b638)
- [Supabase Pooling and asyncpg Issues](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249)

### Deployment
- [Railway vs Fly.io vs Render Comparison](https://medium.com/ai-disruption/railway-vs-fly-io-vs-render-which-cloud-gives-you-the-best-roi-2e3305399e5b)
- [Python Hosting Options Comparison](https://www.nandann.com/blog/python-hosting-options-comparison)
- [Render - FastAPI Deployment Options](https://render.com/articles/fastapi-deployment-options)

### Whisper / Transcription
- [Whisper API Pricing Analysis](https://brasstranscripts.com/blog/openai-whisper-api-pricing-2025-self-hosted-vs-managed)
- [OpenAI Transcription Pricing](https://costgoat.com/pricing/openai-transcription)

### File Upload Pitfalls
- [FastAPI Discussion #10936 - UploadFile and BackgroundTasks](https://github.com/fastapi/fastapi/discussions/10936)
- [File Uploading and Background Tasks on FastAPI](https://medium.com/@marcelo.benencase/file-uploading-and-background-tasks-on-fastapi-883d73f5ea61)
