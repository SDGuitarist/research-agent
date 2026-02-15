# Cycle 17-01: Codebase Architecture Analysis (Code-Only)

**Date:** February 12, 2026
**Scope:** agent.py, synthesize.py, skeptic.py, context.py, modes.py
**Method:** Source code reading only — no spec references
**Purpose:** Map how the current architecture handles context loading, report generation, and mode routing. Identify extension points and seams.

---

## 1. Context Loading (context.py — 101 lines)

### Mechanism

A single file (`research_context.md`) is the only context source. Three public loaders slice it differently:

| Function | What it returns | Sections included |
|---|---|---|
| `load_full_context()` | Entire file as string, or None | Everything |
| `load_search_context()` | Filtered slice | "Two Brands, One Operator", "Target Market", "Search & Research Parameters", "Research Matching Criteria" |
| `load_synthesis_context()` | Filtered slice | "Two Brands, One Operator", "How the Brands Work Together", "Target Market", "Key Differentiators", "Competitive Position" |

Filtering uses `_extract_sections()` — a generic `##`-heading parser that does case-insensitive substring matching. It keeps everything before the first `##` (file header) plus any matching sections.

### Where each loader is called

- `load_full_context()` → called in `agent.py:_evaluate_and_synthesize()` for quick mode, passed to `synthesize_report()` as `business_context`
- `load_synthesis_context()` → called in `agent.py:_evaluate_and_synthesize()` for standard/deep, passed to skeptic and `synthesize_final()`
- `load_search_context()` → **defined but never called from agent.py**. Exists as dead code or a future hook.

### Constraints

- Single-file only. No multi-document loading.
- No structured data parsing (no YAML, no tables, no status flags).
- File path is configurable via parameter but defaults to `research_context.md` in working directory.
- Returns `None` on missing file — callers handle this gracefully.

---

## 2. Mode Routing (modes.py — 168 lines)

### ResearchMode dataclass

Frozen (immutable) dataclass. All behavioral parameters for a research run live here:

```
name, max_sources, search_passes, word_target, max_tokens, auto_save,
synthesis_instructions, pass1_sources, pass2_sources,
min_sources_full_report, min_sources_short_report, relevance_cutoff,
decompose, cost_estimate
```

### Three modes

| Mode | Sources | Tokens | Decompose | Auto-save | Cost |
|---|---|---|---|---|---|
| quick | 4 | 600 | No | No | ~$0.12 |
| standard | 10 | 3000 | Yes | Yes | ~$0.35 |
| deep | 12 | 8000 | Yes | Yes | ~$0.85 |

### Dispatch path

`from_name(str)` maps string → factory classmethod. The agent dispatches on `self.mode.name`:

```python
# agent.py:_research_async()
if is_deep:
    return await self._research_deep(...)
else:
    return await self._research_with_refinement(...)
```

Quick and standard share `_research_with_refinement()`. They diverge inside `_evaluate_and_synthesize()` where quick gets single-pass synthesis and standard gets draft→skeptic→final.

### Validation

`__post_init__` validates all fields. Invalid configs raise `ValueError` at construction time — fast failure.

---

## 3. Report Generation (synthesize.py — 551 lines)

### Three synthesis functions

| Function | Sections produced | Business context? | Skeptic input? | Used by |
|---|---|---|---|---|
| `synthesize_report()` | All in one pass | Yes | No | Quick |
| `synthesize_draft()` | 1-8 (factual) | No (intentional) | No | Standard, Deep |
| `synthesize_final()` | 9-12/13 (analytical) | Yes | Yes | Standard, Deep |

### Section structure (hardcoded in prompts)

**Draft (sections 1-8):**
1. Executive Summary
2. Company Overview
3. Service Portfolio
4. Marketing Positioning
5. Messaging Theme Analysis
6. Buyer Psychology
7. Content & Marketing Tactics
8. Business Model Analysis

**Final (sections 9-12/13, adapts based on skeptic):**
9. Competitive Implications
10. Positioning Advice
11. Adversarial Analysis (only if skeptic findings exist)
12. Limitations & Gaps
13. Sources

### Prompt architecture (consistent across all three functions)

- System prompt: warns about prompt injection in `<sources>`, tells model to ignore instructions inside source content
- User prompt structure: `<query>` + optional `<business_context>` + `<sources>` + `<instructions>`
- Business context explicitly marked as trusted in system prompt; sources are not
- All user-provided and external content sanitized via `sanitize_content()` before inclusion

### Key details

- All three functions stream to stdout via `client.messages.stream`
- `synthesize_final()` concatenates: `draft + "\n\n" + final_sections` — the full report is built by string concatenation, not by a single LLM call
- `_build_sources_context()` groups summaries by URL, deduplicates via exact-match normalization, formats as XML `<source>` blocks
- `BALANCE_INSTRUCTION` appended to all synthesis prompts — catches comparison queries
- Limited-sources handling: disclaimer prepended, instructions tell model to write shorter
- `synthesize_draft()` deliberately excludes business context to keep factual sections "uncolored"

---

## 4. Skeptic Pass (skeptic.py — 360 lines)

### Data model

```python
@dataclass
class SkepticFinding:
    lens: str           # "evidence_alignment" | "timing_stakes" | "strategic_frame" | "combined"
    checklist: str      # Markdown checklist with severity ratings
    critical_count: int
    concern_count: int
```

### Three individual lenses

| Lens | Function | What it checks |
|---|---|---|
| Evidence Alignment | `run_skeptic_evidence()` | Claims vs. source support. Tags as SUPPORTED/INFERRED/UNSUPPORTED |
| Timing & Stakes | `run_skeptic_timing()` | Time-sensitive dynamics, cost of waiting vs acting |
| Strategic Frame | `run_skeptic_frame()` | Whether the analysis solves the right problem. "Break the Trolley" |

### Two orchestration modes

- **Standard:** `run_skeptic_combined()` — all 3 lenses in one LLM call, one `SkepticFinding` output
- **Deep:** `run_deep_skeptic_pass()` — 3 sequential calls. Each receives prior findings:
  ```
  evidence (no priors) → timing (sees evidence) → frame (sees evidence + timing)
  ```

### Shared infrastructure

- `_call_skeptic()` — wraps API call with 1 retry on rate limit/timeout, parses response into `SkepticFinding`
- `_build_context_block()` — optional business context XML
- `_build_prior_block()` — optional prior findings XML (deep mode chaining)
- `_count_severity()` — simple string counting for "critical finding" and "[concern]"
- Shared system prompt `_ADVERSARIAL_SYSTEM` used by all skeptic functions

### Failure handling

In `agent.py`, `SkepticError` is caught and the pipeline continues without adversarial analysis — `findings = []`, and `synthesize_final` skips Section 11.

---

## 5. Agent Orchestration (agent.py — 644 lines)

### ResearchAgent class

- `__slots__` enforced: `_client`, `_async_client`, `_start_time`, `mode`, `max_sources`, `summarize_model`, `synthesize_model`
- Both sync and async Anthropic clients stored as private attributes
- `research()` (sync) wraps `_research_async()` via `asyncio.run()`, with guard against nested event loops
- `__repr__` explicitly excludes API keys

### Pipeline architecture

Two pipeline shapes, selected by mode:

**`_research_with_refinement()` (quick + standard):**
```
search pass 1 (original query)
  → sub-query searches (if complex decomposition)
  → refine query from snippets
  → search pass 2 (refined query)
  → combine results
  → split prefetched vs needs-fetch
  → fetch → extract → cascade recover
  → summarize
  → _evaluate_and_synthesize()
```

**`_research_deep()` (deep):**
```
search pass 1 (original query)
  → sub-query searches (if complex decomposition)
  → fetch → extract → cascade recover → summarize (FULL processing between passes)
  → refine query from summaries (not snippets)
  → search pass 2 (refined query)
  → fetch → extract → cascade recover → summarize pass 2
  → merge all summaries
  → _evaluate_and_synthesize()
```

Key difference: deep mode does full fetch/extract/summarize between search passes, refining from full summaries rather than snippets.

### Convergence point: `_evaluate_and_synthesize()`

Both pipelines converge here. This method handles:

1. **Relevance gate** — `evaluate_sources()` scores and filters summaries, returns decision
2. **Insufficient data branch** — early return with explanation
3. **Quick mode branch** — `load_full_context()` → `synthesize_report()` (single pass)
4. **Standard/deep branch:**
   - `synthesize_draft()` (sections 1-8, no context)
   - `load_synthesis_context()` → skeptic pass (combined or 3-pass based on mode)
   - `synthesize_final()` (sections 9+, with context + skeptic findings)

### Reusable static methods

| Method | What it does |
|---|---|
| `_split_prefetched()` | Separates Tavily raw_content results from those needing HTTP fetch |
| `_search_sub_queries()` | Parallel sub-query searching with `Semaphore(2)` cap, deduplication |
| `_recover_failed_urls()` | Cascade fallback (Jina → Tavily Extract → snippet) for failed fetches |

---

## 6. Extension Points and Seams

### Seam A: Mode registration (modes.py)

**How:** Add a new `@classmethod` factory (e.g., `ResearchMode.intelligence()`), register in `from_name()`.
**What it controls:** Source counts, token budget, synthesis instructions, decomposition, relevance thresholds.
**Limitation:** The mode only parameterizes behavior within the existing pipeline shapes. It can't change the pipeline *structure* — that's controlled by the `if/else` in `agent.py`.

### Seam B: Pipeline dispatch (agent.py:_research_async, line 190)

**How:** Add a new branch: `if self.mode.name == "new_mode": return await self._new_pipeline(...)`.
**What it enables:** A fundamentally different pipeline shape (different stage ordering, different context loading timing, different output format).
**Current state:** Two branches — `is_deep` and `else`. Quick and standard share one branch.

### Seam C: Context section sets (context.py)

**How:** Add a new section set (e.g., `_INTELLIGENCE_SECTIONS`) and a new `load_*_context()` function.
**What it enables:** Different context slices for different pipeline stages.
**Limitation:** Only works with a single file. Multi-document loading would need structural changes to context.py.

### Seam D: Unused loader — `load_search_context()`

**What:** Exists in context.py but is never called from agent.py. The decomposition step receives no business context.
**Opportunity:** Ready-made injection point. Could be wired into decompose_query() or a new pre-search stage with zero new code in context.py.

### Seam E: Skeptic lens addition (skeptic.py)

**How:** Add a new `run_skeptic_*()` function following the existing pattern (sanitize, build context/prior blocks, call `_call_skeptic()`). Add it to `run_deep_skeptic_pass()`.
**Limitation:** `run_skeptic_combined()` would also need its prompt updated to include the new lens.

### Seam F: Synthesis function addition (synthesize.py)

**How:** Add a new `synthesize_*()` function alongside existing ones. Reuse `_build_sources_context()`, streaming pattern, sanitization, and system prompt pattern.
**What it enables:** A different output format (different section structure, different prompt instructions) without touching existing functions.

### Seam G: Relevance gate decisions (agent.py:_evaluate_and_synthesize)

**How:** The evaluation returns `{"decision": "insufficient_data" | "short_report" | "full_report"}`. New decision values could trigger new branches.
**Current state:** Three-way branch with clean separation.

---

## 7. Architectural Characteristics

### Strengths

- **Additive design:** Each cycle (1-16) added new stages without modifying downstream modules. Cascade, decomposition, skeptic — all layered on top.
- **Context isolation:** Draft synthesis deliberately excludes business context. Factual and analytical sections are generated separately to prevent context bleeding.
- **Graceful degradation:** Skeptic failure → skip section. Cascade failure → snippet fallback. Pass 2 failure → use pass 1 results. Search engine failure → DuckDuckGo fallback.
- **Security discipline:** `__slots__`, private API clients, sanitize everywhere, XML boundaries, system prompt injection defense.
- **Frozen mode configs:** Immutable dataclass prevents accidental mutation during pipeline execution.

### Rigidities

- **Pipeline shape is string-matched:** `if is_deep` / `if self.mode.name == "quick"` — no polymorphism, no strategy pattern. Adding modes that need new pipeline shapes means adding more string-comparison branches.
- **Section structure lives in prompts:** No data structure controls which sections get generated. Changing the output format means writing new prompt strings.
- **Single-file context:** `research_context.md` is the only external input besides the query. No multi-document, no structured data, no external API integration for context.
- **No persistent state:** Each run starts fresh. No tracking of what was searched before, what was found, or what changed.
- **Synthesis is string concatenation:** `draft + "\n\n" + result` — the final report is stitched together as a string, not assembled from structured parts.

### Unused/underutilized code

- `load_search_context()` — defined, tested (presumably), never called from agent.py
- `_deduplicate_summaries()` — only used inside `_build_sources_context()`, exact-match only

---

## 8. Summary: What the Architecture Is Built For vs. What It Could Become

**Built for:** Taking a free-text query, searching the web, and producing a structured competitor research report with adversarial review. Stateless, query-driven, single-run.

**Extension surface for something different:**

| Capability | Current support | What's needed |
|---|---|---|
| New mode with same pipeline shape | Full (just add ResearchMode classmethod) | Nothing |
| New mode with different pipeline shape | Partial (dispatch seam exists) | New `_research_*()` method + branch |
| New context sources | Minimal (single-file only) | Multi-document loader |
| Structured context (tables, status flags) | None | Parser for structured data |
| Different output format | Partial (synthesis_instructions is a string) | New synthesis function |
| Persistent state between runs | None | State management layer |
| New skeptic lenses | Full (follow existing pattern) | New function + update orchestrators |
| Pre-search context loading | Seam exists (unused `load_search_context`) | Wire it in |
