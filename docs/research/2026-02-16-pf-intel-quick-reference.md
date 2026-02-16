# PF-Intel Backend Patterns — Quick Reference Card

A quick-lookup guide for the most important patterns from research-agent that pf-intel should replicate.

---

## 1. Exception Hierarchy Template

Copy this to `pf_intel/errors.py`:

```python
"""Custom exceptions for pf-intel."""

class PFIntelError(Exception):
    """Base exception for all pf-intel errors."""
    pass

class ValidationError(PFIntelError):
    """Data validation failed."""
    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else []

class PredictionError(PFIntelError):
    """Model prediction failed."""
    pass

class DataError(PFIntelError):
    """Data retrieval failed."""
    pass

class ConfigError(PFIntelError):
    """Configuration failed."""
    pass
```

**Usage:**
```python
# Accumulate errors before raising
errors = []
if not config.batch_size:
    errors.append("batch_size is required")
if config.timeout <= 0:
    errors.append("timeout must be positive")
if errors:
    raise ConfigError("Invalid config", errors=errors)

# Never do: except Exception
# Always do: except (SpecificError, AnotherError)
```

---

## 2. Frozen Dataclass Config Template

Copy this to `pf_intel/config.py`:

```python
"""Configuration for pf-intel."""

from dataclasses import dataclass

@dataclass(frozen=True)
class PredictionConfig:
    """Configuration for predictions."""
    name: str
    max_batch_size: int
    timeout_seconds: float
    model: str
    enable_cache: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        errors = []
        if self.max_batch_size < 1:
            errors.append("max_batch_size must be >= 1")
        if self.timeout_seconds < 0.1:
            errors.append("timeout_seconds must be >= 0.1")
        if not self.name:
            errors.append("name cannot be empty")
        if errors:
            raise ValueError(f"Invalid PredictionConfig: {'; '.join(errors)}")

    @classmethod
    def fast(cls) -> "PredictionConfig":
        return cls(
            name="fast",
            max_batch_size=10,
            timeout_seconds=5.0,
            model="fast-model-v1",
        )

    @classmethod
    def accurate(cls) -> "PredictionConfig":
        return cls(
            name="accurate",
            max_batch_size=5,
            timeout_seconds=30.0,
            model="large-model-v2",
        )
```

**Key points:**
- `frozen=True` prevents mutation
- `__post_init__` validates immediately on creation
- Factory methods centralize defaults
- All validation errors accumulated before raising

---

## 3. Three-Way Result Type Template

Use instead of returning `Optional[T]`:

```python
from dataclasses import dataclass
from enum import Enum

class LoadStatus(Enum):
    LOADED = "loaded"
    NOT_FOUND = "not_found"
    FAILED = "failed"

@dataclass(frozen=True)
class LoadResult:
    content: str | None
    status: LoadStatus
    source: str = ""
    error: str = ""

    def __bool__(self) -> bool:
        return self.status == LoadStatus.LOADED and self.content is not None

    @classmethod
    def loaded(cls, content: str, source: str = "") -> "LoadResult":
        if not content:
            raise ValueError("loaded() requires non-empty content")
        return cls(content=content, status=LoadStatus.LOADED, source=source)

    @classmethod
    def not_found(cls, source: str = "") -> "LoadResult":
        return cls(content=None, status=LoadStatus.NOT_FOUND, source=source)

    @classmethod
    def failed(cls, error: str, source: str = "") -> "LoadResult":
        if not error:
            raise ValueError("failed() requires non-empty error")
        return cls(content=None, status=LoadStatus.FAILED, source=source, error=error)
```

**Usage:**
```python
result = load_config("config.yaml")
if result.status == LoadStatus.LOADED:
    use(result.content)
elif result.status == LoadStatus.NOT_FOUND:
    logger.info(f"Config not found at {result.source}")
elif result.status == LoadStatus.FAILED:
    logger.error(f"Failed to load: {result.error}")
```

---

## 4. Atomic File Writing Template

Copy exactly from research-agent. Put in `pf_intel/safe_io.py`:

```python
"""Atomic file writing for safe state persistence."""

import os
import tempfile
from pathlib import Path
from .errors import PFIntelError

def atomic_write(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically.

    Prevents partial writes from corrupting state files.
    Writes to temp file, then atomically renames.

    Raises:
        PFIntelError: If write fails.
    """
    target = Path(path).resolve()
    if Path(path).is_symlink():
        raise PFIntelError(f"Refusing to write through symlink: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding=encoding) as f:
            fd = None  # os.fdopen takes ownership
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, target)  # Atomic on POSIX
    except OSError as exc:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if fd is not None:
            os.close(fd)
        raise PFIntelError(f"Failed to write {target}: {exc}") from exc
```

---

## 5. Public API Template

Put in `pf_intel/__init__.py`:

```python
"""PF-Intel prediction backend."""

__version__ = "1.0.0"

import asyncio
import os

from .predictor import PFIntelPredictor
from .errors import PFIntelError
from .config import PredictionConfig
from .results import PredictionResult

__all__ = [
    "PFIntelPredictor",
    "PredictionConfig",
    "PredictionResult",
    "PFIntelError",
    "predict",
    "predict_async",
]

def predict(data: dict, mode: str = "standard") -> PredictionResult:
    """Synchronous prediction wrapper."""
    try:
        return asyncio.run(predict_async(data, mode=mode))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            raise PFIntelError(
                "predict() cannot be called from async context. "
                "Use 'await predict_async()' instead."
            ) from e
        raise

async def predict_async(data: dict, mode: str = "standard") -> PredictionResult:
    """Async prediction for FastAPI, MCP, etc."""
    if not data:
        raise PFIntelError("Input data cannot be empty")

    try:
        config = PredictionConfig.from_name(mode)
    except ValueError:
        raise PFIntelError(f"Invalid mode: {mode!r}")

    if not os.environ.get("PFINTEL_API_KEY"):
        raise PFIntelError("PFINTEL_API_KEY environment variable is required")

    predictor = PFIntelPredictor(config=config)
    return await predictor.predict(data)
```

---

## 6. Test Fixture Template

Put in `tests/conftest.py`:

```python
"""Shared test fixtures."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Sample data fixtures
@pytest.fixture
def sample_input_data():
    return {
        "field1": "value1",
        "field2": 123,
        "field3": ["a", "b"]
    }

# Mock factories
@pytest.fixture
def mock_model_response():
    def _create(predictions: dict, confidence: float = 0.95):
        response = MagicMock()
        response.predictions = predictions
        response.confidence = confidence
        return response
    return _create

# Async mocks
@pytest.fixture
async def async_mock_predictor():
    mock = AsyncMock()
    mock.predict = AsyncMock(return_value={"result": "success"})
    return mock
```

**Usage:**
```python
def test_prediction(sample_input_data, mock_model_response):
    response = mock_model_response({"label": "A"})
    assert response.predictions == {"label": "A"}
```

**Mock where imported FROM:**
```python
# BAD: @patch("sklearn.predict")
# GOOD: @patch("pf_intel.predictor.sklearn.predict")
@patch("pf_intel.predictor.sklearn.predict")
def test_predict(mock_predict):
    mock_predict.return_value = [1, 2, 3]
```

---

## 7. Data Type Pipeline Template

```python
# Define intermediate types (one per stage)

@dataclass
class ValidatedData:
    data: dict
    is_valid: bool
    errors: list[str]

@dataclass
class EnrichedData:
    original: dict
    features: dict
    metadata: dict

@dataclass
class ModelPrediction:
    predictions: dict
    confidence: float
    model_version: str

# Use in orchestrator
class Predictor:
    async def predict(self, data: dict) -> PredictionResult:
        # Stage 1: Validate
        validated = await self.validate(data)
        if not validated.is_valid:
            return PredictionResult(
                predictions={},
                status="failed",
                message=f"Validation failed: {validated.errors}"
            )

        # Stage 2: Enrich
        enriched = await self.enrich(validated.data)

        # Stage 3: Predict
        prediction = await self.model.predict(enriched.features)

        # Stage 4: Return
        return PredictionResult(
            predictions=prediction.predictions,
            confidence=prediction.confidence,
            status="success",
        )
```

---

## 8. Module Organization Checklist

```
pf_intel/
├── __init__.py                 # Public API (sync + async wrappers)
├── errors.py                   # Exception hierarchy (COPY pattern)
├── config.py                   # Config dataclasses (COPY pattern)
├── safe_io.py                  # Atomic writes (COPY from research-agent)
├── results.py                  # Result types
├── sanitize.py                 # Prompt/injection defense if needed
├── predictor.py                # Orchestrator (coordinates pipeline)
├── cli.py                       # CLI argument parsing & formatting
├── validation.py               # Data validation
├── enrichment.py               # Feature engineering
├── model_interface.py          # Model API abstraction
├── caching.py                  # Caching layer (optional)
└── logging.py                  # Logging setup (optional)

tests/
├── conftest.py                 # Fixtures (COPY pattern)
├── test_errors.py              # Exception tests
├── test_config.py              # Config tests
├── test_predictor.py           # Orchestrator tests
├── test_validation.py
├── test_enrichment.py
└── fixtures/
    ├── sample_valid_data.json
    └── sample_invalid_data.json
```

Each file has ONE concern.

---

## 9. Concurrency Pattern (if needed)

```python
import asyncio
import httpx

async def fetch_concurrent(urls: list[str], max_concurrent: int = 5):
    """Fetch multiple URLs with concurrency limit."""

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch_one(client: httpx.AsyncClient, url: str):
        async with semaphore:
            return await client.get(url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_fetch_one(client, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetched = []
        for i, result in enumerate(results):
            if isinstance(result, httpx.Response):
                fetched.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Request {i} failed: {result}")

        return fetched
```

**Key points:**
- Semaphore limits concurrency
- Shared client for connection reuse
- `return_exceptions=True` prevents cascading failures
- Explicit exception handling in the loop

---

## 10. CLAUDE.md Template

Create `pf_intel/CLAUDE.md` with:

```markdown
# PF-Intel Backend — Claude Code Context

## What This Is

[Brief description of what the backend does]

## Architecture

```
main.py (CLI entry point)
pf_intel/
├── __init__.py       — Public API: predict(), predict_async(), list_modes()
├── predictor.py      — Orchestrator: validates, enriches, predicts, formats
├── errors.py         — Custom exception hierarchy
├── config.py         — Frozen dataclass configs
├── results.py        — Result types for public API
├── validation.py     — Data validation
├── enrichment.py     — Feature engineering
├── model_interface.py — Model API abstraction
├── cli.py            — CLI argument parsing
└── safe_io.py        — Atomic file writes
```

## Running

```bash
python3 main.py --help
python3 main.py predict --data input.json
python3 main.py predict --mode fast "input"
```

## Testing

```bash
python3 -m pytest tests/ -v
```

Must pass all tests before deployment.

## Environment

- Python 3.10+
- `.env` must contain: `PFINTEL_API_KEY`
- All models use `model-v1`

## Key Conventions

- **Frozen dataclasses**: All configuration is immutable
- **Specific exceptions**: Never bare `except Exception`
- **Three-way results**: No Optional[T], use Status enums
- **Atomic writes**: Use safe_io for file persistence
- **Mock where imported**: Test patches go on import location, not library

See LESSONS_LEARNED.md for development history.
```

---

## Checklist: Did You Implement the Pattern Correctly?

- [ ] Is the exception hierarchy complete (base class + specific subclasses)?
- [ ] Does every config class use `frozen=True`?
- [ ] Does every config class have `__post_init__` validation?
- [ ] Are there factory methods for common configs?
- [ ] Do result types use `Status` enums instead of `Optional`?
- [ ] Do you use `atomic_write()` for all file I/O?
- [ ] Does the public API have both sync and async versions?
- [ ] Is each module focused on ONE concern?
- [ ] Does `tests/conftest.py` have factories, not just samples?
- [ ] Are mocks patched at import location (`pf_intel.module.library`, not `library`)?
- [ ] Does the project have CLAUDE.md and LESSONS_LEARNED.md?
- [ ] Are all tests async-compatible (use `@pytest.mark.asyncio`)?
- [ ] Is there NO bare `except Exception` anywhere?

---

## Quick Lookup: "How do I..."

| Question | Answer |
|----------|--------|
| Handle API key validation? | Check in `__init__.py` before creating predictor (see pattern 5) |
| Create reusable test data? | Use `@pytest.fixture` factories in `conftest.py` (pattern 6) |
| Mock external libraries? | Use `@patch("pf_intel.module.library")` (pattern 6) |
| Save configuration safely? | Use `atomic_write()` from `safe_io.py` (pattern 4) |
| Report validation errors? | Accumulate in list, raise with `errors=` kwarg (pattern 1) |
| Make config immutable? | Use `@dataclass(frozen=True)` (pattern 2) |
| Handle async context from sync? | Use `try/except RuntimeError` with `"running event loop"` check (pattern 5) |
| Test async functions? | Use `@pytest.mark.asyncio` and `async def test_*(...)` (pattern 6) |
| Pipeline between stages? | Use typed dataclasses at each stage (pattern 7) |
| Limit concurrent requests? | Use `asyncio.Semaphore` (pattern 9) |

---

## Files to Copy Directly from research-agent

1. `research_agent/safe_io.py` → `pf_intel/safe_io.py` (no changes needed)
2. `research_agent/errors.py` → `pf_intel/errors.py` (adapt exception names)
3. `tests/conftest.py` → `tests/conftest.py` (adapt fixtures to pf-intel types)
4. `research_agent/sanitize.py` → `pf_intel/sanitize.py` (if handling untrusted input)

---

## One More Thing: The Git Commit Rule

From research-agent's LESSONS_LEARNED.md:

> "Commit every ~50-100 lines (checkpoints against context death + mid-edit protection)"

Before committing, ask: "Can this change be reverted cleanly if the next change breaks?"

If the answer is "no," split your commit.

```bash
# Good commits (~50-100 lines, one concern each):
git commit -m "feat: add ValidationError exception class"
git commit -m "feat: implement data validation module"
git commit -m "feat: add validation tests"

# Bad commits (~500+ lines, multiple concerns):
git commit -m "feat: add validation, enrichment, and model interface"
```

---

**Last Updated:** 2026-02-16
**Reference:** `/Users/alejandroguillen/research-agent/docs/research/2026-02-16-pf-intel-backend-patterns-analysis.md`
