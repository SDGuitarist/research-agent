# Research Agent Patterns Analysis — Document Index

**Date Created:** 2026-02-16
**Purpose:** Extract and document patterns for pf-intel backend development
**Total Analysis:** 1,951 lines across 2 comprehensive documents

---

## Documents

### 1. Primary Reference: Backend Patterns Analysis

**File:** `2026-02-16-pf-intel-backend-patterns-analysis.md` (1,374 lines)

**Purpose:** Comprehensive, detailed analysis of all architectural patterns in research-agent with code examples and recommendations for pf-intel.

**Sections:**

1. **Executive Summary** — 6 key pattern areas
2. **Project Structure & Module Organization** — Directory layout, principles, recommendations
3. **Error Handling Patterns** — Exception hierarchy, specific exceptions, three-layer async handling
4. **Frozen Dataclass Configuration** — Design decisions, factory methods, validation
5. **Result Types & Three-Way Pattern** — ContextResult, SchemaResult, public API types
6. **Data Flow & Pipeline Pattern** — Typed dataclass pipeline, orchestration
7. **Atomic File Writing Pattern** — Safe state persistence, safety features
8. **Testing Patterns** — Test structure, fixtures, mocking rule, async testing
9. **Public API Pattern** — Entry points, CLI integration, pyproject.toml
10. **Special Patterns** — Sanitization, fallback chains, concurrency with semaphore
11. **CLAUDE.md & Developer Context** — Project instructions, development history

**File Index:**
- Maps 16 key files with full paths and code excerpts
- Cross-references to actual research-agent implementation

**When to Use:**
- Deep understanding of why patterns exist
- Learning the reasoning behind each design decision
- Finding complete code examples for reference
- Understanding trade-offs and design considerations

---

### 2. Quick Reference: Developer Cheat Sheet

**File:** `2026-02-16-pf-intel-quick-reference.md` (577 lines)

**Purpose:** Condensed, copy-paste-ready templates for implementing patterns quickly.

**Sections:**

1. **Exception Hierarchy Template** — Ready to copy to `pf_intel/errors.py`
2. **Frozen Dataclass Config Template** — Ready to copy to `pf_intel/config.py`
3. **Three-Way Result Type Template** — Status enum pattern
4. **Atomic File Writing Template** — Copy from research-agent (no changes)
5. **Public API Template** — Sync/async entry points, __init__.py
6. **Test Fixture Template** — conftest.py structure, mock factories
7. **Data Type Pipeline Template** — Multi-stage dataclass pattern
8. **Module Organization Checklist** — Directory structure with responsibilities
9. **Concurrency Pattern** — Semaphore + asyncio.gather if needed
10. **CLAUDE.md Template** — Project context file
11. **Implementation Checklist** — 20 items to verify pattern compliance
12. **Quick Lookup Table** — "How do I..." reference
13. **Files to Copy Directly** — No adaptation needed

**When to Use:**
- Getting started quickly with a pattern
- Copy-pasting boilerplate code
- Quick reference during implementation
- Team onboarding and consistency

---

## Quick Navigation

### By Topic

**Error Handling:**
- Primary: Section 3 (Backend Patterns Analysis)
- Quick: Section 1 (Quick Reference)
- Code file: `/Users/alejandroguillen/research-agent/research_agent/errors.py`

**Configuration:**
- Primary: Section 4 (Backend Patterns Analysis)
- Quick: Section 2 (Quick Reference)
- Code files:
  - `/Users/alejandroguillen/research-agent/research_agent/modes.py`
  - `/Users/alejandroguillen/research-agent/research_agent/cycle_config.py`

**Data Types:**
- Primary: Section 5 (Backend Patterns Analysis)
- Quick: Section 3 & 7 (Quick Reference)
- Code files:
  - `/Users/alejandroguillen/research-agent/research_agent/context_result.py`
  - `/Users/alejandroguillen/research-agent/research_agent/results.py`
  - `/Users/alejandroguillen/research-agent/research_agent/schema.py`

**File I/O:**
- Primary: Section 7 (Backend Patterns Analysis)
- Quick: Section 4 (Quick Reference)
- Code file: `/Users/alejandroguillen/research-agent/research_agent/safe_io.py`

**Testing:**
- Primary: Section 8 (Backend Patterns Analysis)
- Quick: Section 6 (Quick Reference)
- Code file: `/Users/alejandroguillen/research-agent/tests/conftest.py`

**Public API:**
- Primary: Section 9 (Backend Patterns Analysis)
- Quick: Section 5 (Quick Reference)
- Code files:
  - `/Users/alejandroguillen/research-agent/research_agent/__init__.py`
  - `/Users/alejandroguillen/research-agent/research_agent/cli.py`

**Module Organization:**
- Primary: Section 2 (Backend Patterns Analysis)
- Quick: Section 8 (Quick Reference)

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total lines of analysis | 1,951 |
| Primary document length | 1,374 lines |
| Quick reference length | 577 lines |
| Code examples provided | 50+ |
| Research-agent files referenced | 16 |
| Total test count (research-agent) | 558 |
| Development cycles analyzed | 18 |
| Sections in primary document | 11 |
| Templates in quick reference | 10 |
| Implementation checklist items | 20 |
| Quick lookup questions answered | 10 |

---

## Implementation Roadmap

### Phase 1: Foundation (Patterns 1-3)
**Duration:** 1-2 days
**Patterns:**
1. Exception hierarchy (`errors.py`)
2. Frozen dataclass config (`config.py`)
3. Module organization (one file per concern)

**Files to create:**
```
pf_intel/
├── errors.py              # Copy template from Section 1
├── config.py              # Copy template from Section 2
├── __init__.py            # Stub entry point
└── predictor.py           # Stub orchestrator
```

### Phase 2: Core Pipeline (Patterns 4-5)
**Duration:** 2-3 days
**Patterns:**
4. Result types (three-way pattern)
5. Data flow pipeline (typed dataclasses)

**Files to create:**
```
pf_intel/
├── results.py             # Result types
├── validation.py          # Stage 1
├── enrichment.py          # Stage 2
└── model_interface.py     # Stage 3
```

### Phase 3: Infrastructure (Patterns 6-7)
**Duration:** 1-2 days
**Patterns:**
6. File I/O (atomic writes)
7. Testing structure

**Files to create:**
```
pf_intel/
├── safe_io.py             # Copy from research-agent

tests/
├── conftest.py            # Copy template from Section 6
├── test_errors.py         # Test exceptions
├── test_config.py         # Test config
└── test_predictor.py      # Test orchestrator
```

### Phase 4: Public API (Patterns 8-9)
**Duration:** 1 day
**Patterns:**
8. Public API with sync/async
9. CLI entry point

**Files to create:**
```
pf_intel/
├── __init__.py            # Copy template from Section 5
├── cli.py                 # CLI argument parsing
└── main.py                # Minimal entry point

pyproject.toml             # Configure [project.scripts]
```

### Phase 5: Documentation (Patterns 10-11)
**Duration:** 1-2 days
**Patterns:**
10. CLAUDE.md project context
11. LESSONS_LEARNED.md development history

**Files to create:**
```
├── CLAUDE.md              # Copy template from Section 10
├── LESSONS_LEARNED.md     # Development log
├── README.md              # Usage guide
└── docs/                  # Architecture docs
```

---

## Files to Reference

### From research-agent (Source of Patterns)

| File | Purpose | Lines | Copy To |
|------|---------|-------|---------|
| `research_agent/errors.py` | Exception hierarchy | 46 | `pf_intel/errors.py` (adapt names) |
| `research_agent/modes.py` | Config pattern | 200+ | Reference for `pf_intel/config.py` |
| `research_agent/cycle_config.py` | Secondary config | 47 | Reference for additional configs |
| `research_agent/context_result.py` | Three-way result type | 69 | Reference for `pf_intel/results.py` |
| `research_agent/results.py` | Public API types | 34 | Reference for `pf_intel/results.py` |
| `research_agent/safe_io.py` | Atomic writes | 50 | `pf_intel/safe_io.py` (no changes) |
| `research_agent/sanitize.py` | Injection defense | 12 | `pf_intel/sanitize.py` (if needed) |
| `research_agent/__init__.py` | Public API | 100+ | Reference for `pf_intel/__init__.py` |
| `research_agent/cli.py` | CLI pattern | 300+ | Reference for `pf_intel/cli.py` |
| `tests/conftest.py` | Test fixtures | 294 | Reference for `pf_intel/tests/conftest.py` |
| `CLAUDE.md` | Context file | 70 | Reference for `pf_intel/CLAUDE.md` |
| `LESSONS_LEARNED.md` | Development log | 385 | Reference for `pf_intel/LESSONS_LEARNED.md` |

### Analysis Documents (This Folder)

| File | Purpose | Length |
|------|---------|--------|
| `2026-02-16-pf-intel-backend-patterns-analysis.md` | Complete pattern reference | 1,374 lines |
| `2026-02-16-pf-intel-quick-reference.md` | Copy-paste templates | 577 lines |
| `INDEX.md` (this file) | Navigation guide | 300+ lines |

---

## Key Takeaways

### Top 5 Most Important Patterns

1. **Exception Hierarchy** — Foundation for error handling across the system
   - Never bare `except Exception`
   - Accumulate errors before raising
   - Specific exceptions for specific failures

2. **Frozen Dataclass Config** — Prevents mutations and centralizes defaults
   - `@dataclass(frozen=True)`
   - `__post_init__` validation
   - Factory methods for presets

3. **Three-Way Result Types** — Replaces Optional with explicit states
   - Status enums (LOADED, NOT_FOUND, FAILED)
   - Factory methods (loaded(), not_found(), failed())
   - Boolean conversion for simple checks

4. **Module Organization** — One file per concern, clear dependencies
   - search.py only searches
   - fetch.py only fetches
   - extract.py only extracts
   - agent.py coordinates (no business logic)

5. **Atomic File Writing** — Prevents state corruption
   - Write to temp file
   - Atomic rename
   - Cleanup on failure

### Most Common Mistakes to Avoid

1. ~~`except Exception:`~~ → Use specific exception types
2. ~~`Optional[str]` return~~ → Use three-way result type
3. ~~Mutable config~~ → Use frozen dataclasses
4. ~~Bare `f.write()`~~ → Use `atomic_write()`
5. ~~Multiple concerns in one file~~ → One file per concern

### Pattern Adoption Priority

**Must have (day 1):**
- Exception hierarchy
- Frozen config
- Module organization

**Should have (week 1):**
- Result types
- Public API
- Test structure

**Nice to have (ongoing):**
- Atomic writes
- Sanitization
- Concurrency patterns

---

## References & Links

### Research-Agent Source Files
All analysis references the actual research-agent codebase:
- Location: `/Users/alejandroguillen/research-agent/`
- Repository: https://github.com/SDGuitarist/research-agent
- Version analyzed: 0.18.0

### Document Links
- Full analysis: `2026-02-16-pf-intel-backend-patterns-analysis.md`
- Quick reference: `2026-02-16-pf-intel-quick-reference.md`
- Project CLAUDE.md: `/Users/alejandroguillen/research-agent/CLAUDE.md`
- Project LESSONS_LEARNED.md: `/Users/alejandroguillen/research-agent/LESSONS_LEARNED.md`

### Related Documentation
- `/Users/alejandroguillen/research-agent/README.md` — How to run research-agent
- `/Users/alejandroguillen/research-agent/FAILURE_MODES_CATALOG.md` — Known failure modes
- `/Users/alejandroguillen/research-agent/docs/relevance-scoring.md` — Advanced pattern

---

## Document Maintenance

**Last Updated:** 2026-02-16
**Created By:** Repository Research Analysis
**Status:** Complete
**Next Review:** When pf-intel backend implementation begins

**How to Use These Documents:**
1. Start with Quick Reference for immediate templates
2. Reference Backend Patterns Analysis for detailed explanations
3. Check the source files in research-agent for actual implementations
4. Ask questions in the code review phase about pattern compliance

**Feedback or Updates:**
If you discover a pattern is unclear or missing, add it to this INDEX and the relevant primary document.

---

## Quick Start Checklist

- [ ] Read the Executive Summary in Backend Patterns Analysis
- [ ] Skim the Quick Reference templates
- [ ] Copy Exception Hierarchy template to `pf_intel/errors.py`
- [ ] Copy Config template to `pf_intel/config.py`
- [ ] Set up conftest.py with fixtures
- [ ] Create CLAUDE.md project context
- [ ] Begin implementation with Phase 1 (Foundation)
- [ ] Validate against Implementation Checklist (section 11)
- [ ] Reference research-agent files throughout

**Total time to understand all patterns: 2-3 hours**
**Time to implement foundation (Phase 1): 1-2 days**
