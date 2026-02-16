# Research Agent Architecture Patterns — PF-Intel Backend Reference

**Date:** 2026-02-16
**Purpose:** Extract and document patterns from research-agent that should carry over to pf-intel backend
**Scope:** Project structure, error handling, dataclasses, module organization, testing, and conventions

---

## Executive Summary

The research-agent is a mature, well-structured Python CLI built through 18 development cycles. It demonstrates professional-grade patterns in six key areas:

1. **Project Structure**: Modular, single-responsibility files with clear orchestration
2. **Error Handling**: Custom exception hierarchy with specific, typed exceptions (never bare `except Exception`)
3. **Configuration**: Frozen dataclasses with `__post_init__` validation (single source of truth)
4. **Data Flow**: Typed dataclass pipeline with intermediate results
5. **File I/O**: Atomic writes using tempfile + rename to prevent corruption
6. **Testing**: Factory fixtures, mock-where-imported-from rule, async support

These patterns should become the foundation for pf-intel's Python backend.

---

## 1. Project Structure & Module Organization

### Directory Layout

```
research-agent/
├── pyproject.toml              # Single source of truth for dependencies, metadata
├── main.py                     # CLI entry point (minimal: calls research_agent.cli.main())
├── research_agent/
│   ├── __init__.py             # Public API exports + async wrapper functions
│   ├── cli.py                  # CLI argument parsing, mode selection, output formatting
│   ├── agent.py                # Orchestrator: coordinates pipeline stages
│   ├── errors.py               # Exception hierarchy (all custom exceptions)
│   ├── modes.py                # Frozen dataclass: ResearchMode (configs)
│   ├── cycle_config.py         # Frozen dataclass: CycleConfig (resource limits)
│   ├── context_result.py       # Result type: ContextResult + ContextStatus enum
│   ├── results.py              # Result types for public API: ResearchResult, ModeInfo
│   ├── search.py               # Single concern: web search (Tavily + DuckDuckGo)
│   ├── fetch.py                # Single concern: async HTTP fetching + URL validation
│   ├── extract.py              # Single concern: content extraction (trafilatura + fallback)
│   ├── cascade.py              # Single concern: fetch fallback chain (Jina → Tavily → snippet)
│   ├── summarize.py            # Single concern: batch chunk summarization
│   ├── synthesize.py           # Single concern: report generation
│   ├── relevance.py            # Single concern: source quality scoring
│   ├── skeptic.py              # Single concern: adversarial verification
│   ├── schema.py               # Single concern: YAML parsing + Gap model
│   ├── state.py                # Single concern: gap state transitions
│   ├── sanitize.py             # Single concern: prompt injection defense
│   ├── token_budget.py         # Single concern: token counting & prioritization
│   ├── staleness.py            # Single concern: staleness detection
│   └── safe_io.py              # Single concern: atomic file writes
├── tests/
│   ├── conftest.py             # Shared fixtures (samples, mocks, factories)
│   ├── test_*.py               # One test file per module (558 tests total)
│   └── fixtures/               # HTML samples for extraction testing
├── CLAUDE.md                   # Project context for Claude Code
└── LESSONS_LEARNED.md          # Development history + patterns to reuse
```

### Key Principles

**One File = One Concern**
- `search.py` only does searching
- `fetch.py` only does HTTP fetching
- `extract.py` only does content extraction
- No utility files with 10 different unrelated functions

**Clear Dependency Flow**
```
search → fetch → extract → summarize → synthesize
```
Each stage outputs a typed dataclass that the next stage consumes.

**Orchestration Layer**
- `agent.py` coordinates pipeline (doesn't contain business logic)
- `cli.py` handles CLI concerns (argument parsing, formatting, file I/O)
- Public functions in `__init__.py` expose high-level API

**Recommendation for pf-intel:**
```
pf_intel/
├── __init__.py                 # Public API: run_prediction, run_prediction_async
├── cli.py                      # Argument parsing, output formatting
├── predictor.py                # Main orchestrator
├── errors.py                   # Exception hierarchy
├── config.py                   # Frozen dataclass configs
├── [business_logic]/           # One file per concern (validation, scoring, etc.)
└── [infrastructure]/           # File I/O, caching, logging
```

---

## 2. Error Handling Patterns

### Exception Hierarchy

All custom exceptions subclass a base `ResearchError`:

**File:** `/Users/alejandroguillen/research-agent/research_agent/errors.py`

```python
class ResearchError(Exception):
    """Base exception for research agent errors."""
    pass

class SearchError(ResearchError):
    """Raised when search fails."""
    pass

class SynthesisError(ResearchError):
    """Raised when report synthesis fails."""
    pass

class SkepticError(ResearchError):
    """Raised when skeptic review fails."""
    pass

class ContextError(ResearchError):
    """Base exception for all context loading failures."""
    pass

class SchemaError(ResearchError):
    """YAML parse or validation failure.

    Carries a list of validation errors so callers see all problems at once.
    """

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else []

class StateError(ResearchError):
    """State file read/write/corruption failure."""
    pass

class ContextResult + related types...
```

### Key Patterns

**1. Specific Exceptions, Never Bare**

Bad:
```python
try:
    data = yaml.safe_load(text)
except Exception:
    return None
```

Good:
```python
try:
    data = yaml.safe_load(text)
except yaml.YAMLError as exc:
    raise SchemaError(f"Invalid YAML: {exc}") from exc
```

**2. Exception Types Carry Extra Data**

SchemaError can accumulate multiple validation errors:
```python
errors = []
if not gap.id:
    errors.append("Gap missing id")
if priority not in range(1, 6):
    errors.append(f"Invalid priority: {priority}")
if errors:
    raise SchemaError("validation failed", errors=errors)
```

Callers can inspect `exc.errors` to see all problems at once, not just the first.

**3. Three-Layer Exception Handling in Async Context**

From `summarize.py` pattern (prevents one task failure from canceling others):
```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for i, result in enumerate(results):
    if isinstance(result, list):
        all_summaries.extend(result)
    elif isinstance(result, Exception):
        logger.error(f"Chunk {i} failed: {result}")
        # Continue processing other chunks
```

### Recommendation for pf-intel

```python
# pf_intel/errors.py
class PFIntelError(Exception):
    """Base exception for all pf-intel errors."""
    pass

class ValidationError(PFIntelError):
    """Data validation failed (schema, type, constraint)."""

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else []

class PredictionError(PFIntelError):
    """Model prediction or inference failed."""
    pass

class DataError(PFIntelError):
    """Data source or retrieval failed."""
    pass

class ConfigError(PFIntelError):
    """Configuration loading or validation failed."""
    pass
```

---

## 3. Frozen Dataclass Configuration Pattern

### Two Key Files

**`modes.py`** — Research mode configurations (quick/standard/deep):

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ResearchMode:
    """Configuration for a research mode."""
    name: str
    max_sources: int
    search_passes: int
    word_target: int
    max_tokens: int
    auto_save: bool
    synthesis_instructions: str
    pass1_sources: int
    pass2_sources: int
    min_sources_full_report: int
    min_sources_short_report: int
    relevance_cutoff: int = 3
    decompose: bool = True
    cost_estimate: str = ""
    model: str = "claude-sonnet-4-20250514"

    def __post_init__(self) -> None:
        """Validate mode configuration."""
        errors = []

        if self.pass1_sources < 1:
            errors.append(f"pass1_sources must be >= 1, got {self.pass1_sources}")
        if self.max_tokens < 100:
            errors.append(f"max_tokens must be >= 100, got {self.max_tokens}")
        # ... more validation

        if errors:
            raise ValueError(f"Invalid ResearchMode: {'; '.join(errors)}")

    @classmethod
    def quick(cls) -> "ResearchMode":
        return cls(
            name="quick",
            max_sources=4,
            search_passes=2,
            word_target=300,
            max_tokens=600,
            auto_save=False,
            synthesis_instructions="Provide a brief, focused summary...",
            pass1_sources=4,
            pass2_sources=2,
            min_sources_full_report=3,
            min_sources_short_report=1,
            cost_estimate="~$0.12",
        )

    @classmethod
    def standard(cls) -> "ResearchMode":
        # ... similar factory method
```

**`cycle_config.py`** — Resource limits for batch processing:

```python
@dataclass(frozen=True)
class CycleConfig:
    """Configuration for a single research cycle's resource limits."""

    max_gaps_per_run: int = 5
    max_tokens_per_prompt: int = 100_000
    reserved_output_tokens: int = 4096
    default_ttl_days: int = 30

    def __post_init__(self) -> None:
        """Validate configuration."""
        errors = []

        if self.max_gaps_per_run < 1:
            errors.append(f"max_gaps_per_run must be >= 1, got {self.max_gaps_per_run}")
        if self.reserved_output_tokens >= self.max_tokens_per_prompt:
            errors.append(
                f"reserved_output_tokens ({self.reserved_output_tokens}) must be < "
                f"max_tokens_per_prompt ({self.max_tokens_per_prompt})"
            )

        if errors:
            raise ValueError(f"Invalid CycleConfig: {'; '.join(errors)}")
```

### Key Design Decisions

**Why `frozen=True`:**
- Prevents accidental mutation at runtime
- All changes to config must go through constructors or factory methods
- Single source of truth — changes to one factory method affect everywhere it's instantiated

**Why `__post_init__`:**
- Validation runs immediately when object is created
- Accumulate ALL errors before raising (not fail-fast on first error)
- Errors list makes it easy to report all problems to users

**Why Factory Methods:**
- `ResearchMode.quick()`, `ResearchMode.standard()`, `ResearchMode.deep()`
- Centralizes defaults in one place
- Easy to add new modes without changing CLI parsing logic

### Recommendation for pf-intel

```python
# pf_intel/config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class PredictionConfig:
    """Configuration for a prediction job."""
    name: str
    max_batch_size: int
    timeout_seconds: float
    retry_count: int = 3
    enable_cache: bool = True
    model: str = "default-model-v1"

    def __post_init__(self) -> None:
        errors = []
        if self.max_batch_size < 1:
            errors.append("max_batch_size must be >= 1")
        if self.timeout_seconds < 1.0:
            errors.append("timeout_seconds must be >= 1.0")
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

---

## 4. Result Types & Three-Way Pattern

### ContextResult Pattern

Instead of returning `str | None`, use a typed result that distinguishes three states:

**File:** `/Users/alejandroguillen/research-agent/research_agent/context_result.py`

```python
from dataclasses import dataclass
from enum import Enum

class ContextStatus(Enum):
    LOADED = "loaded"
    NOT_CONFIGURED = "not_configured"
    EMPTY = "empty"
    FAILED = "failed"

@dataclass(frozen=True)
class ContextResult:
    """Result of a context loading operation."""

    content: str | None
    status: ContextStatus
    source: str = ""
    error: str = ""

    def __bool__(self) -> bool:
        """True only when content was successfully loaded."""
        return self.status == ContextStatus.LOADED and self.content is not None

    @classmethod
    def loaded(cls, content: str, source: str = "") -> "ContextResult":
        if not content:
            raise ValueError("loaded() requires non-empty content")
        return cls(content=content, status=ContextStatus.LOADED, source=source)

    @classmethod
    def not_configured(cls, source: str = "") -> "ContextResult":
        return cls(content=None, status=ContextStatus.NOT_CONFIGURED, source=source)

    @classmethod
    def empty(cls, source: str = "") -> "ContextResult":
        return cls(content=None, status=ContextStatus.EMPTY, source=source)

    @classmethod
    def failed(cls, error: str, source: str = "") -> "ContextResult":
        if not error:
            raise ValueError("failed() requires a non-empty error string")
        return cls(content=None, status=ContextStatus.FAILED, source=source, error=error)
```

### Usage Pattern

Bad (loses information):
```python
context = load_context("config.md")  # returns str | None
if context:
    # But you can't distinguish: was file missing? Was it empty? Did it fail?
    use(context)
```

Good:
```python
result = load_context("config.md")
if result.status == ContextStatus.LOADED:
    use(result.content)  # Guaranteed non-empty
elif result.status == ContextStatus.NOT_CONFIGURED:
    logger.info(f"No context configured at {result.source}")
elif result.status == ContextStatus.EMPTY:
    logger.info(f"Context file {result.source} exists but is empty")
elif result.status == ContextStatus.FAILED:
    logger.error(f"Failed to load context: {result.error}")
```

### Related: SchemaResult Pattern

For gap schema loading (similar three-way semantics):

```python
@dataclass(frozen=True)
class SchemaResult:
    """Result of loading a gap schema file."""

    gaps: tuple[Gap, ...]
    source: str = ""

    @property
    def is_loaded(self) -> bool:
        return len(self.gaps) > 0

    @property
    def is_empty(self) -> bool:
        return len(self.gaps) == 0 and self.source != ""

    @property
    def is_not_configured(self) -> bool:
        return len(self.gaps) == 0 and self.source == ""

    def __bool__(self) -> bool:
        return self.is_loaded
```

### Public API Result Type

For end-user-facing APIs:

```python
@dataclass(frozen=True)
class ResearchResult:
    """Result from a research query."""
    report: str
    query: str
    mode: str
    sources_used: int
    status: str  # "full_report", "short_report", "insufficient_data"

@dataclass(frozen=True)
class ModeInfo:
    """Information about an available research mode."""
    name: str
    max_sources: int
    word_target: int
    cost_estimate: str
    auto_save: bool
```

### Recommendation for pf-intel

```python
# pf_intel/results.py
from dataclasses import dataclass
from enum import Enum

class PredictionStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass(frozen=True)
class PredictionResult:
    """Result of a prediction operation."""
    predictions: dict
    confidence_scores: dict
    status: PredictionStatus
    message: str = ""
    processing_time_ms: float = 0.0
```

---

## 5. Data Flow & Pipeline Pattern

### Typed Dataclass Pipeline

Each stage transforms data and passes it to the next stage:

```
SearchResult → FetchedPage → ExtractedContent → Summary → str (report)
```

**SearchResult** (from search.py):
```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
```

**FetchedPage** (from fetch.py):
```python
@dataclass
class FetchedPage:
    url: str
    html: str
    status_code: int
```

**ExtractedContent** (from extract.py):
```python
@dataclass
class ExtractedContent:
    url: str
    title: str
    text: str
```

**Summary** (from summarize.py):
```python
@dataclass
class Summary:
    url: str
    title: str
    summary: str
```

Benefits:
- Type hints catch errors at development time
- Self-documenting — each dataclass shows what fields are available
- Easy to inspect intermediate results during debugging
- Can add fields without breaking downstream code (if handled carefully)

### Orchestration Pattern

From `agent.py` — high-level flow:

```python
async def research_async(self, query: str) -> str:
    """Orchestrate the research pipeline."""

    # Pass 1: Initial search and summarization
    search_results = await self.search(query)
    fetched_pages = await self.fetch(search_results)
    extracted = await self.extract(fetched_pages)
    summaries = await self.summarize(extracted, query)

    # Relevance gate
    gate_result = await self.evaluate_sources(summaries, query)

    # May trigger Pass 2 with refined query
    if gate_result.decision == "short_report" and gate_result.refined_query:
        refined_summaries = await self._pass2_research(gate_result.refined_query)
        # Combine results from both passes

    # Generate report
    report = await self.synthesize(gate_result.surviving_sources, query)
    return report
```

### Recommendation for pf-intel

```python
# pf_intel/predictor.py
@dataclass
class ValidationResult:
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
    prediction: dict
    confidence: float
    model_version: str

class PFIntelPredictor:
    async def predict(self, data: dict) -> PredictionResult:
        # Stage 1: Validate
        validation = await self.validate(data)
        if not validation.is_valid:
            return PredictionResult(
                predictions={},
                confidence_scores={},
                status=PredictionStatus.FAILED,
                message=f"Validation failed: {validation.errors}"
            )

        # Stage 2: Enrich
        enriched = await self.enrich(validation.data)

        # Stage 3: Predict
        prediction = await self.model.predict(enriched.features)

        # Stage 4: Format response
        return PredictionResult(
            predictions=prediction.prediction,
            confidence_scores={"overall": prediction.confidence},
            status=PredictionStatus.SUCCESS,
            processing_time_ms=self._elapsed_ms(),
        )
```

---

## 6. Atomic File Writing Pattern

### Safe State Persistence

**File:** `/Users/alejandroguillen/research-agent/research_agent/safe_io.py`

```python
import os
import tempfile
from pathlib import Path
from .errors import StateError

def atomic_write(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically.

    Writes to a temporary file in the same directory, then renames.
    If the write fails for any reason, the original file is unchanged.

    Raises:
        StateError: If the write fails (wraps underlying OSError).
    """
    target = Path(path).resolve()
    if Path(path).is_symlink():
        raise StateError(f"Refusing to write through symlink: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding=encoding) as f:
            fd = None  # os.fdopen takes ownership of the fd
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force to disk
        os.rename(tmp_path, target)  # Atomic on POSIX systems
    except OSError as exc:
        # Clean up temp file on failure
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if fd is not None:
            os.close(fd)
        raise StateError(f"Failed to write {target}: {exc}") from exc
```

### Key Safety Features

1. **Write to temp file first** — If process dies mid-write, original is untouched
2. **Atomic rename** — `os.rename()` is atomic on POSIX (Linux, macOS)
3. **Fsync before rename** — Ensures data reaches disk
4. **Symlink protection** — Refuses to write through symlinks (security)
5. **Cleanup on failure** — Removes temp files if write fails
6. **Parent directory creation** — No need for external mkdir

### Usage

```python
from research_agent.safe_io import atomic_write
from research_agent.errors import StateError

try:
    state_yaml = """
    gaps:
      - id: gap1
        status: verified
    """
    atomic_write("state.yaml", state_yaml)
except StateError as exc:
    logger.error(f"Failed to save state: {exc}")
```

### Recommendation for pf-intel

Use the same pattern if pf-intel needs to persist state, cache, or output files:

```python
# pf_intel/safe_io.py — copy from research-agent exactly
# Then use in pf_intel modules:

from pf_intel.safe_io import atomic_write
from pf_intel.errors import StateError

def save_predictions(predictions: dict, path: str) -> None:
    """Save predictions to JSON file atomically."""
    import json
    try:
        content = json.dumps(predictions, indent=2)
        atomic_write(path, content)
    except StateError as exc:
        raise PFIntelError(f"Failed to save predictions: {exc}") from exc
```

---

## 7. Testing Patterns

### Test Structure

**558 total tests** across 10 test files (one per module):

```
tests/
├── conftest.py                 # Shared fixtures (samples, factories, mocks)
├── test_agent.py               # 60+ tests for orchestrator
├── test_search.py              # Tests for search module
├── test_fetch.py               # Tests for HTTP fetching
├── test_extract.py             # Tests for content extraction
├── test_summarize.py           # Tests for LLM summarization
├── test_synthesize.py          # Tests for report generation
├── test_errors.py              # Tests for exception hierarchy
├── test_context_result.py      # Tests for result types
├── test_relevance.py           # Tests for scoring
├── test_staleness.py           # Tests for staleness logic
└── fixtures/                   # HTML samples for extraction
    ├── sample_html_simple.html
    ├── sample_html_complex.html
    ├── sample_html_empty.html
    └── sample_html_oversized.html
```

### Fixture Pattern

From `conftest.py`:

**1. Data Samples (real or representative)**

```python
@pytest.fixture
def sample_html_simple():
    """Basic HTML page with article content."""
    return (FIXTURES_DIR / "sample_html_simple.html").read_text()

@pytest.fixture
def sample_search_results():
    """List of SearchResult objects."""
    return [
        SearchResult(
            title="Python Async Best Practices",
            url="https://example1.com/python-async",
            snippet="Learn async/await patterns in Python with practical examples."
        ),
        SearchResult(
            title="Asyncio Tutorial",
            url="https://example2.com/asyncio-guide",
            snippet="Complete guide to Python asyncio for beginners."
        ),
    ]
```

**2. Mock Factories (flexible, reusable)**

```python
@pytest.fixture
def mock_anthropic_response():
    """Factory for creating mock Anthropic API responses."""
    def _create_response(text: str, stop_reason: str = "end_turn"):
        response = MagicMock()
        response.content = [MagicMock(text=text)]
        response.stop_reason = stop_reason
        return response
    return _create_response

# Usage:
def test_synthesis(mock_anthropic_response):
    response = mock_anthropic_response("Generated report text")
    # Use response in test
```

**3. Result Type Fixtures**

```python
@pytest.fixture
def sample_scored_sources():
    """List of SourceScore objects for relevance testing."""
    return [
        SourceScore(
            url="https://example1.com/page",
            title="Highly Relevant Article",
            score=5,
            explanation="Directly answers the query with specific information.",
        ),
        SourceScore(
            url="https://example2.com/page",
            title="Somewhat Relevant Article",
            score=3,
            explanation="Touches on the topic but missing key specifics.",
        ),
    ]
```

### Mocking Rule: Mock Where Imported FROM

**Key principle:** Don't mock the implementation; mock the import location.

Bad:
```python
@patch("trafilatura.extract")  # Mocking the library directly
def test_extract(mock_extract):
    # This might not work if extract.py imports differently
```

Good:
```python
@patch("research_agent.extract.trafilatura.extract")  # Mock where it's used
def test_extract(mock_extract):
    # Now it works because we're mocking the module's reference
    mock_extract.return_value = "<p>Content</p>"
    result = extract_content("https://example.com", "<html>...</html>")
    assert result.text == "Content"
```

### Async Testing

Using `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_fetch_concurrent():
    """Test that fetch handles concurrency correctly."""
    urls = [f"https://example{i}.com" for i in range(5)]

    with patch("research_agent.fetch.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = AsyncMock(...)

        results = await fetch_urls(urls)
        assert len(results) == 5
```

### Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# Single file
python3 -m pytest tests/test_search.py -v

# Single test
python3 -m pytest tests/test_agent.py::TestResearchAgentQuickMode::test_research_quick_mode_completes_pipeline -v

# With coverage
python3 -m pytest tests/ --cov=research_agent --cov-report=term-missing

# Async debugging
python3 -m pytest tests/ -v -s --tb=short
```

### Recommendation for pf-intel

```
pf_intel/tests/
├── conftest.py
├── test_predictor.py           # Main orchestrator tests
├── test_validator.py
├── test_model_interface.py
├── test_errors.py
└── fixtures/
    ├── sample_valid_data.json
    ├── sample_invalid_data.json
    └── sample_predictions.json

# conftest.py example:
@pytest.fixture
def sample_input_data():
    return {
        "field1": "value1",
        "field2": 123,
        "field3": ["a", "b"]
    }

@pytest.fixture
def mock_model_response():
    def _create(predictions: dict, confidence: float = 0.95):
        response = MagicMock()
        response.predictions = predictions
        response.confidence = confidence
        return response
    return _create

@pytest.mark.asyncio
async def test_predictor_success(sample_input_data, mock_model_response):
    # Test here
```

---

## 8. Public API Pattern

### Entry Points

**File:** `/Users/alejandroguillen/research-agent/research_agent/__init__.py`

```python
"""Research agent — search the web and generate structured reports."""

__version__ = "0.18.0"

import asyncio
import os

from .agent import ResearchAgent
from .errors import ResearchError
from .modes import ResearchMode
from .results import ModeInfo, ResearchResult

__all__ = [
    "ResearchAgent",
    "ResearchMode",
    "ResearchResult",
    "ResearchError",
    "ModeInfo",
    "run_research",
    "run_research_async",
    "list_modes",
]


def run_research(query: str, mode: str = "standard") -> ResearchResult:
    """Run a research query and return a structured result.

    Args:
        query: The research question.
        mode: Research mode — "quick", "standard", or "deep".

    Returns:
        ResearchResult with report, query, mode, sources_used, status.

    Raises:
        ResearchError: If query is empty, mode is invalid,
            API keys are missing, or research fails.
            Subclasses (SearchError, SynthesisError) propagate
            from the pipeline for specific failures.
    """
    try:
        return asyncio.run(run_research_async(query, mode=mode))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            raise ResearchError(
                "run_research() cannot be called from async context. "
                "Use 'await run_research_async()' instead."
            ) from e
        raise


async def run_research_async(query: str, mode: str = "standard") -> ResearchResult:
    """Async version of run_research for use in async contexts."""
    if not query or not query.strip():
        raise ResearchError("Query cannot be empty")

    try:
        research_mode = ResearchMode.from_name(mode)
    except ValueError:
        raise ResearchError(
            f"Invalid mode: {mode!r}. Must be one of: deep, quick, standard"
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ResearchError("ANTHROPIC_API_KEY environment variable is required")

    if not os.environ.get("TAVILY_API_KEY"):
        raise ResearchError("TAVILY_API_KEY environment variable is required")

    agent = ResearchAgent(mode=research_mode)
    report = await agent.research_async(query)

    return ResearchResult(
        report=report,
        query=query,
        mode=research_mode.name,
        sources_used=agent._last_source_count,
        status=agent._last_gate_decision or "error",
    )


def list_modes() -> list[ModeInfo]:
    """List available research modes with their configuration."""
    modes = [ResearchMode.quick(), ResearchMode.standard(), ResearchMode.deep()]
    return [
        ModeInfo(
            name=m.name,
            max_sources=m.max_sources,
            word_target=m.word_target,
            cost_estimate=m.cost_estimate,
            auto_save=m.auto_save,
        )
        for m in modes
    ]
```

### CLI Entry Point

**File:** `/Users/alejandroguillen/research-agent/main.py`

```python
#!/usr/bin/env python3
"""CLI entry point — delegates to research_agent.cli.main()."""
from research_agent.cli import main

if __name__ == "__main__":
    main()
```

**File:** `/Users/alejandroguillen/research-agent/research_agent/cli.py`

Contains:
- Argument parsing (argparse)
- Mode selection logic
- File output handling
- Progress display
- Error handling and user messaging

### pyproject.toml Integration

```toml
[project.scripts]
research-agent = "research_agent.cli:main"
```

This allows:
```bash
research-agent "your query"  # Direct command (installed package)
python3 main.py "your query"  # Via script
python3 -m research_agent.cli "your query"  # Via module
```

### Recommendation for pf-intel

```python
# pf_intel/__init__.py
"""PF-Intel prediction backend."""

__version__ = "1.0.0"

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
    import asyncio
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
    """Async prediction for use in FastAPI, MCP, etc."""
    if not data:
        raise PFIntelError("Input data cannot be empty")

    config = PredictionConfig.from_name(mode)
    predictor = PFIntelPredictor(config=config)
    return await predictor.predict(data)

# pyproject.toml
# [project.scripts]
# pf-intel = "pf_intel.cli:main"
```

---

## 9. Special Patterns Worth Noting

### Sanitization for Prompt Injection Defense

**File:** `/Users/alejandroguillen/research-agent/research_agent/sanitize.py`

```python
"""Shared content sanitization for prompt injection defense."""

def sanitize_content(text: str) -> str:
    """
    Sanitize untrusted content before including in prompts.

    Escapes XML-like delimiters to prevent prompt injection attacks
    where malicious web content tries to break out of data sections.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

**Usage:**
```python
# Before including user/web content in a prompt:
from research_agent.sanitize import sanitize_content

user_content = fetch_from_web()
safe_content = sanitize_content(user_content)

prompt = f"""
<article>
{safe_content}
</article>

Now analyze this article...
"""
```

### Fallback Chain Pattern

**File:** `/Users/alejandroguillen/research-agent/research_agent/extract.py`

```python
def extract_content(url: str, html: str) -> ExtractedContent | None:
    """Extract clean text from HTML with fallback."""

    # Try trafilatura first (faster)
    result = _extract_with_trafilatura(url, html)
    if result and len(result.text) >= 100:
        return result

    # Fall back to readability-lxml (more robust)
    result = _extract_with_readability(url, html)
    if result and len(result.text) >= 100:
        return result

    # Couldn't extract enough content
    return None
```

Pattern: Try fast path first, fall back to more robust (but slower) path if needed.

### Concurrency with Semaphore

**File:** `/Users/alejandroguillen/research-agent/research_agent/fetch.py`

```python
async def fetch_urls(urls: list[str], max_concurrent: int = 5) -> list[FetchedPage]:
    """Fetch multiple URLs concurrently with a semaphore."""

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch_single(client: httpx.AsyncClient, url: str) -> FetchedPage:
        async with semaphore:
            return await _do_fetch(client, url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_fetch_single(client, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetched = []
        for result in results:
            if isinstance(result, FetchedPage):
                fetched.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Fetch failed: {result}")

        return fetched
```

Key points:
- Semaphore limits concurrent requests (prevents overwhelming servers)
- Shared client for connection reuse
- `return_exceptions=True` so one failure doesn't cancel others
- Explicit exception handling for logging

---

## 10. CLAUDE.md & Developer Context

### CLAUDE.md (Project Instructions)

Located at `/Users/alejandroguillen/research-agent/CLAUDE.md`

Contains:
- What the project does (high-level)
- Architecture diagram with file descriptions
- Running instructions (all CLI modes)
- Testing instructions (pytest)
- Environment requirements (.env variables)
- Key conventions (dataclasses, sanitization, error handling)

**Recommendation:** pf-intel should have an equivalent file documenting:
- Project purpose and scope
- Backend architecture
- How to run the backend
- Testing instructions
- Environment configuration
- Key architectural decisions

### LESSONS_LEARNED.md (Development History)

Located at `/Users/alejandroguillen/research-agent/LESSONS_LEARNED.md`

Documents:
- 18 cycles of development
- Key lesson per cycle
- Security issues found during review
- Patterns worth reusing
- Mistakes to avoid
- Implementation details for non-obvious patterns

**Recommendation:** pf-intel should maintain a similar document tracking:
- Design decisions and rationale
- Bugs found and how to prevent them
- Performance findings
- Security considerations

---

## 11. Summary Checklist for pf-intel Backend

Use this checklist when building the pf-intel Python backend to ensure alignment with research-agent patterns:

### Project Structure
- [ ] One file per concern (no utility files)
- [ ] Clear dependency flow between modules
- [ ] `__init__.py` exposes public API
- [ ] Separate `cli.py` for CLI concerns
- [ ] Orchestrator layer (`predictor.py` or equivalent)

### Error Handling
- [ ] Custom exception hierarchy with base class
- [ ] Specific exceptions (never bare `except Exception`)
- [ ] SchemaError-style exceptions with error lists
- [ ] Proper exception chaining with `from exc`
- [ ] Three-layer async exception handling (return_exceptions=True)

### Configuration
- [ ] Frozen dataclasses for all config
- [ ] `__post_init__` validation
- [ ] Factory methods for pre-configured modes
- [ ] Config constants in one place
- [ ] Type hints on all config fields

### Data Types
- [ ] Typed dataclasses for all intermediate results
- [ ] Three-way result types (loaded/empty/failed) instead of Optional
- [ ] Public API returns frozen dataclasses
- [ ] Enums for status/state values

### File I/O
- [ ] Atomic writes using tempfile + rename
- [ ] Symlink protection
- [ ] Proper cleanup on failure
- [ ] StateError exceptions for I/O failures

### Testing
- [ ] One test file per module
- [ ] Shared fixtures in conftest.py
- [ ] Factory fixtures for flexibility
- [ ] Mock where imported FROM
- [ ] Async test support
- [ ] 85%+ code coverage target

### Public API
- [ ] Both sync and async entry points
- [ ] Validation before execution
- [ ] Environment variable checks
- [ ] Structured return types
- [ ] Clear error messages

### Documentation
- [ ] CLAUDE.md for developer context
- [ ] LESSONS_LEARNED.md for development history
- [ ] Docstrings on all public functions
- [ ] Type hints on all functions
- [ ] README with examples

### Security
- [ ] Sanitization of untrusted content
- [ ] URL validation if fetching external resources
- [ ] No API keys in CLI arguments
- [ ] Symlink attack prevention
- [ ] Prompt injection defense

---

## File Index for Reference

| File | Purpose |
|------|---------|
| `/Users/alejandroguillen/research-agent/pyproject.toml` | Dependencies, entry points, project metadata |
| `/Users/alejandroguillen/research-agent/CLAUDE.md` | Developer context (model for pf-intel CLAUDE.md) |
| `/Users/alejandroguillen/research-agent/LESSONS_LEARNED.md` | Development history and patterns |
| `/Users/alejandroguillen/research-agent/research_agent/__init__.py` | Public API and async wrappers |
| `/Users/alejandroguillen/research-agent/research_agent/errors.py` | Exception hierarchy |
| `/Users/alejandroguillen/research-agent/research_agent/modes.py` | Frozen dataclass config pattern |
| `/Users/alejandroguillen/research-agent/research_agent/cycle_config.py` | Secondary config pattern |
| `/Users/alejandroguillen/research-agent/research_agent/context_result.py` | Three-way result type pattern |
| `/Users/alejandroguillen/research-agent/research_agent/results.py` | Public API result types |
| `/Users/alejandroguillen/research-agent/research_agent/safe_io.py` | Atomic file writing |
| `/Users/alejandroguillen/research-agent/research_agent/sanitize.py` | Prompt injection defense |
| `/Users/alejandroguillen/research-agent/research_agent/schema.py` | YAML parsing and data model |
| `/Users/alejandroguillen/research-agent/research_agent/agent.py` | Orchestrator pattern |
| `/Users/alejandroguillen/research-agent/research_agent/cli.py` | CLI entry point |
| `/Users/alejandroguillen/research-agent/main.py` | Script entry point |
| `/Users/alejandroguillen/research-agent/tests/conftest.py` | Test fixtures and factories |
| `/Users/alejandroguillen/research-agent/tests/test_errors.py` | Exception testing pattern |

---

## Conclusion

The research-agent repository demonstrates professional Python development practices across six key dimensions. These patterns have been battle-tested through 18 development cycles and are ready to be adopted as the foundation for pf-intel's backend architecture.

The most critical patterns to implement first:
1. **Exception hierarchy** (errors.py)
2. **Frozen dataclass config** (modes.py, cycle_config.py)
3. **Module organization** (one concern per file)
4. **Public API pattern** (__init__.py with sync/async wrappers)
5. **Test structure** (conftest.py with fixtures)

Everything else follows naturally once these foundations are in place.
