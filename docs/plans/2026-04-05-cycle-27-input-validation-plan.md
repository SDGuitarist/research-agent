---
cycle: 27
title: "Input Validation & Generation Controls"
brainstorm: "docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md"
roadmap: "docs/research/2026-03-09-entropy-fixes-roadmap.md"
feed_forward:
  risk: "Vague word set heuristic misses subtler vague queries like 'tell me about technology'"
  verify_first: false
---

# Cycle 27 Plan: Input Validation & Generation Controls

**Date:** 2026-04-05
**Sessions:** 3

## Prior Phase Risk

> "The vague word set heuristic. It will catch obvious garbage ('stuff', 'what's the best way') but miss subtler vague queries like 'tell me about technology' (2 meaningful words, neither in vague set, but still too broad for useful research)."

Accepted limitation. The plan documents the exact boundary of what the heuristic catches and what it misses. No LLM-based fallback in this cycle — we ship the heuristic, measure false negatives in practice, and revisit if needed.

---

## Session 1: Idempotent Sanitization

### What exactly is changing?

**File: `research_agent/sanitize.py`** — Replace the body of `sanitize_content()`:

Current:
```python
def sanitize_content(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

New:
```python
import html

def sanitize_content(text: str) -> str:
    normalized = html.unescape(text)
    return normalized.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

One line added: `html.unescape(text)` before the existing escapes. This normalizes any pre-escaped entities back to raw characters, then re-escapes once. Result: `sanitize_content(sanitize_content(x)) == sanitize_content(x)`.

**No other files change.** Same function signature. Same module. All call sites unchanged.

### What must NOT change?

- Output for never-sanitized input: `sanitize_content("a & <b>")` must still produce `"a &amp; &lt;b&gt;"`.
- No call site changes. No import changes in consumers.
- `build_context_block()` unchanged.
- `CONTEXT_TAG` unchanged.

### Known test change: `test_ampersand_before_angle_brackets`

The existing test at `tests/test_sanitize.py:34` asserts:

```python
def test_ampersand_before_angle_brackets(self):
    result = sanitize_content("&lt;script&gt;")
    assert result == "&amp;lt;script&amp;gt;"
```

With the new unescape-then-escape approach, `"&lt;script&gt;"` will first unescape to `"<script>"`, then re-escape to `"&lt;script&gt;"`. The old behavior (`"&amp;lt;script&amp;gt;"`) treated `&lt;` as text containing a bare `&` — the new behavior correctly recognizes it as an already-escaped entity and normalizes it.

**This test must be updated** to assert `"&lt;script&gt;"` instead. This is the correct idempotent behavior — re-sanitizing already-sanitized input should be a no-op, not a corruption.

No other existing tests are affected — the other 6 tests in `test_sanitize.py` all use never-sanitized input (`<script>`, `Tom & Jerry`, `<div>`, etc.) whose behavior is unchanged.

### How will we know it worked?

1. **Idempotency invariant test:** `sanitize_content(sanitize_content(text)) == sanitize_content(text)` for:
   - Plain text: `"hello world"`
   - Ampersand: `"a & b"`
   - Angle brackets: `"<script>alert('xss')</script>"`
   - Pre-escaped: `"&amp;"`, `"&lt;"`, `"&gt;"`
   - Mixed: `"a & <b> &lt;c&gt;"`
   - Unicode: `"émoji 🎉 & stuff"`
   - Empty string: `""`
   - HTML entities we don't target: `"&nbsp;"`, `"&euro;"`, `"&#x27;"`
2. **Updated test:** `test_ampersand_before_angle_brackets` asserts `"&lt;script&gt;"` (idempotent result).
3. **All other existing `test_sanitize.py` tests pass unchanged.**
4. **Full suite:** `python3 -m pytest tests/ -q` → 948+ pass.

### Most likely way this plan is wrong?

`html.unescape()` converts ALL HTML entities (not just `&amp;`, `&lt;`, `&gt;`). If web content contains `&nbsp;` or `&#x27;`, those become literal characters. For our use case (LLM prompt building, not HTML rendering), this is correct behavior. The one known test breakage (`test_ampersand_before_angle_brackets`) is documented above — no surprises expected beyond that.

### Exact steps

1. Read `tests/test_sanitize.py` — confirm only `test_ampersand_before_angle_brackets` needs updating.
2. Edit `sanitize.py`: add `import html` at top, add `normalized = html.unescape(text)` line.
3. Update `test_ampersand_before_angle_brackets` assertion to `"&lt;script&gt;"`.
4. Add idempotency tests to `tests/test_sanitize.py`.
5. Run `python3 -m pytest tests/test_sanitize.py -v`.
6. Run `python3 -m pytest tests/ -q`.
7. Commit: `fix(27-1): make sanitize_content idempotent via unescape-then-escape`

---

## Session 2: Vague Query Detection

### What exactly is changing?

**File: `research_agent/query_validation.py`** — Add ~40 lines:

```python
VAGUE_WORDS = frozenset({
    "stuff", "things", "something", "anything", "everything", "whatever",
    "good", "bad", "best", "worst", "new", "old", "way", "ways",
    "nice", "cool", "great", "fine", "interesting",
})

MIN_MEANINGFUL_WORDS = 2

@dataclass(frozen=True)
class VagueQueryResult:
    is_valid: bool
    message: str

def check_query_vagueness(query: str) -> VagueQueryResult:
    """Pre-flight vague query check. Pure Python, no LLM call.

    Rejects queries that have fewer than MIN_MEANINGFUL_WORDS meaningful words,
    or where all meaningful words are in VAGUE_WORDS.
    """
    stripped = query.strip()
    if not stripped:
        return VagueQueryResult(False, "Query is empty. Please provide a research question.")

    words = meaningful_words(stripped)
    if len(words) < MIN_MEANINGFUL_WORDS:
        return VagueQueryResult(
            False,
            f"Query too vague — only {len(words)} meaningful word(s). "
            "Please add specific terms (e.g., 'quantum computing trends' instead of 'stuff')."
        )

    if words <= VAGUE_WORDS:
        return VagueQueryResult(
            False,
            "Query contains only generic words. "
            "Please add a specific topic (e.g., 'best Python web frameworks' instead of 'best things')."
        )

    return VagueQueryResult(True, "")
```

Key design choices:
- Uses existing `meaningful_words()` — inherits its punctuation stripping, hyphen splitting, and stop word removal.
- `words <= VAGUE_WORDS` checks if the set is a subset (all meaningful words are vague).
- Two rejection messages — one for too few words, one for all-vague words. Both suggest improvement.

**File: `research_agent/errors.py`** — Add ~5 lines:

```python
class VagueQueryError(ResearchError):
    """Raised when query is too vague to produce useful research."""
    pass
```

**File: `research_agent/agent.py`** — Add ~8 lines in `_research_async()`, before context loading (before line ~404):

```python
from .query_validation import check_query_vagueness
from .errors import VagueQueryError

# Pre-flight: reject vague queries before any LLM work
vague_check = check_query_vagueness(query)
if not vague_check.is_valid:
    raise VagueQueryError(vague_check.message)
```

**File: `research_agent/mcp_server.py`** — No changes needed. `VagueQueryError` inherits from `ResearchError`, which is already caught at `mcp_server.py:92` and converted to `ToolError` with path stripping. The user-facing message flows through cleanly.

**File: `research_agent/__init__.py`** — Do NOT export `VagueQueryError`. No external caller needs to catch it separately from `ResearchError`. The MCP server catches the base class. If a concrete caller surfaces later that needs the specific type, export then.

### What must NOT change?

- `meaningful_words()` function — used as-is, no modifications.
- `validate_query_list()` — independent function, no overlap.
- `decompose_query()` — downstream of vague check, unchanged.
- All queries with ≥2 specific meaningful words must still work.
- MCP tool interface — no parameter changes.
- CLI interface — `main.py` catches `ResearchError` already.

### How will we know it worked?

Tests for `check_query_vagueness()`:

| Input | Expected | Reason |
|-------|----------|--------|
| `""` | REJECT | Empty |
| `"   "` | REJECT | Whitespace only |
| `"?!..."` | REJECT | Punctuation only → 0 meaningful words |
| `"stuff"` | REJECT | 1 meaningful word < 2 |
| `"things"` | REJECT | 1 meaningful word < 2 |
| `"the"` | REJECT | 0 meaningful words (stop word) |
| `"what's up"` | REJECT | 0 meaningful words |
| `"AI"` | REJECT | 1 meaningful word < 2 |
| `"best way"` | REJECT | 2 meaningful words, but both in VAGUE_WORDS |
| `"good stuff"` | REJECT | 2 meaningful words, both in VAGUE_WORDS |
| `"what is the best way to"` | REJECT | meaningful = {"best", "way"}, both vague |
| `"quantum computing"` | ACCEPT | 2 meaningful words, neither vague |
| `"post-quantum"` | ACCEPT | Splits to {"post", "quantum"}, 2 words |
| `"Python best practices"` | ACCEPT | 3 words, "python" and "practices" not vague |
| `"best Python frameworks"` | ACCEPT | "python" and "frameworks" not vague |
| `"tell me about technology"` | ACCEPT | Known false negative — "technology" not in vague set |
| `"standards,"` | REJECT | 1 meaningful word after punctuation strip |

Integration test: Mock the Anthropic client, call `agent.research("stuff")`, assert `VagueQueryError` raised. Verify no API calls were made.

### Most likely way this plan is wrong?

The `VAGUE_WORDS` set may be too small (false negatives like "technology") or too large (false positives if a legitimate query uses only words in the set). The brainstorm accepted this: we ship the heuristic, monitor, and tighten later. The set is a frozen constant — easy to update.

A second risk: the import of `check_query_vagueness` in `agent.py` must happen at the top of the file (not inside the method) to follow the project's import convention. Check existing import patterns in agent.py.

### Exact steps

1. Add `VagueQueryError` to `errors.py`.
2. Add `VAGUE_WORDS`, `VagueQueryResult`, `check_query_vagueness` to `query_validation.py`.
3. Add import + vague check call to `agent.py:_research_async()`.
4. Write tests in `tests/test_query_validation.py` (unit tests for the function).
5. Write integration test in `tests/test_agent.py` (VagueQueryError raised, no API calls).
6. Run `python3 -m pytest tests/test_query_validation.py tests/test_agent.py -v`.
7. Run `python3 -m pytest tests/ -q`.
8. Commit: `feat(27-2): add vague query detection gate`

---

## Session 3: Per-Task Temperature Controls

### What exactly is changing?

**File: `research_agent/modes.py`** — Add 3 fields to `ResearchMode`:

```python
planning_temperature: float = 0.2    # Classification: decompose, relevance, context detect, refine, coverage, iterate
summarize_temperature: float = 0.5   # Chunk summarization
synthesis_temperature: float = 0.8   # Report synthesis, skeptic, critique, follow-ups
```

Add validation in `__post_init__`:
```python
for field_name in ("planning_temperature", "summarize_temperature", "synthesis_temperature"):
    val = getattr(self, field_name)
    if not (0.0 <= val <= 1.0):
        errors.append(f"{field_name} must be between 0.0 and 1.0, got {val}")
```

No changes to the three factory methods (`quick()`, `standard()`, `deep()`) — defaults apply uniformly. If we later want per-mode temperatures, we add them then.

**File: `research_agent/results.py`** — Add 3 fields to `ModeInfo`:

```python
planning_temperature: float = 0.0
summarize_temperature: float = 0.0
synthesis_temperature: float = 0.0
```

### Anthropic API call-site inventory (rebuilt from codebase)

**16 `messages.create()` / `messages.stream()` calls** across 10 modules (13 create + 3 stream):

| # | File:Line | Function | Temp tier | Notes |
|---|-----------|----------|-----------|-------|
| 1 | `decompose.py:102` | `decompose_query` | planning | Standalone, called from `agent.py:461` |
| 2 | `context.py:414` | `auto_detect_context` | planning | Standalone, called from `agent.py:411`. Already accepts `model` param. |
| 3 | `search.py:241` | `refine_query` | planning | Standalone, called from `agent.py:991,1074` |
| 4 | `relevance.py:161` | `score_source` | planning | Called via `evaluate_sources` → inner `_score` closure (line 290). Thread through `evaluate_sources`. |
| 5 | `relevance.py:435` | `generate_insufficient_data_response` | planning | Standalone, called from `agent.py:826` |
| 6 | `coverage.py:250` | `identify_coverage_gaps` | planning | Standalone, called from `agent.py:700` |
| 7 | `iterate.py:73` | `generate_refined_queries` | planning | Standalone, called from `agent.py:271` |
| 8 | `iterate.py:194` | `generate_followup_questions` | planning | Standalone, called from `agent.py:276` |
| 9 | `critique.py:205` | `evaluate_report` | planning | Classification task (scoring dimensions). Called from `agent.py:212` |
| 10 | `critique.py:280` | `critique_report_file` (contains inline `messages.create`) | planning | Classification. Not called from agent.py — called from MCP `critique_report` tool. |
| 11 | `skeptic.py:76` | `_call_skeptic` | synthesis | Private helper. Called from 4 public entry points: `run_skeptic_evidence`, `run_skeptic_timing`, `run_skeptic_frame`, `run_skeptic_combined`. Agent calls `run_deep_skeptic_pass` (line 880) and `run_skeptic_combined` (line 888). |
| 12 | `summarize.py:121` | `summarize_chunk` | summarize | Called via `summarize_content` → `_guarded_summarize` closure. Thread through `summarize_all` → `summarize_content` → `summarize_chunk`. Agent calls `summarize_all` (line 656). |
| 13 | `synthesize.py:342` | `synthesize_report` (stream) | synthesis | Quick mode single-pass. Called from `agent.py:849`. |
| 14 | `synthesize.py:458` | `synthesize_draft` (stream) | synthesis | Standard/deep draft pass. Called from `agent.py:871`. |
| 15 | `synthesize.py:689` | `synthesize_final` (stream) | synthesis | Standard/deep final pass. Called from `agent.py:903`. |
| 16 | `synthesize.py:831` | `synthesize_mini_report` (create) | synthesis | Iteration supplementary sections. Called from `agent.py:343` via `asyncio.to_thread`. |

### Plumbing: wrapper chains that need temperature threaded

Three call chains have intermediate wrappers between agent.py and the actual `messages.create()` call:

**1. Summarization chain:** `agent.py` → `summarize_all()` → `summarize_content()` → `summarize_chunk()`

- Add `temperature: float = 1.0` to `summarize_chunk()` signature, pass to `messages.create()`.
- Add `temperature: float = 1.0` to `summarize_content()` signature, forward to both `summarize_chunk()` call sites (guarded and unguarded, lines 185 and 190).
- Add `temperature: float = 1.0` to `summarize_all()` signature, forward to `summarize_content()` inside `_process` closure (line 234).
- Agent.py call site (line 656): pass `temperature=self.mode.summarize_temperature`.

**2. Skeptic chain:** `agent.py` → `run_deep_skeptic_pass()` / `run_skeptic_combined()` → individual skeptic functions → `_call_skeptic()` (4-deep from agent.py, 3 levels need the param added)

- Add `temperature: float = 1.0` to `_call_skeptic()` signature, pass to `messages.create()`.
- Add `temperature: float = 1.0` to all 4 individual skeptic functions (`run_skeptic_evidence`, `run_skeptic_timing`, `run_skeptic_frame`, `run_skeptic_combined`), forward to `_call_skeptic()`.
- Add `temperature: float = 1.0` to `run_deep_skeptic_pass()`, forward to the 3 individual skeptic calls (lines 351-352, 359).
- Agent.py call sites (lines 880, 888): pass `temperature=self.mode.synthesis_temperature`.

**3. Relevance scoring chain:** `agent.py` → `evaluate_sources()` → `score_source()` (via inner closure)

- Add `temperature: float = 1.0` to `score_source()` signature, pass to `messages.create()`.
- Add `temperature: float = 1.0` to `evaluate_sources()` signature — but `evaluate_sources` takes a `mode: ResearchMode` param, so it can read `mode.planning_temperature` directly and pass to `score_source` inside the `_score` closure. **No new param needed on `evaluate_sources`** — just use `mode.planning_temperature` internally.
- Agent.py call sites (lines 746, 800): no change needed (mode already passed).

### What agent.py passes at each call site

| agent.py line | Calls | Passes temperature as |
|---------------|-------|-----------------------|
| 411 | `auto_detect_context(self.client, query)` | `temperature=self.mode.planning_temperature` (new kwarg) |
| 461 | `decompose_query(self.client, query, ...)` | `temperature=self.mode.planning_temperature` |
| 656 | `summarize_all(self.async_client, contents, ...)` | `temperature=self.mode.summarize_temperature` |
| 700 | `identify_coverage_gaps(query, ..., client=self.async_client, ...)` | `temperature=self.mode.planning_temperature` |
| 746, 800 | `evaluate_sources(query, summaries, mode=self.mode, ...)` | No change — reads `mode.planning_temperature` internally |
| 826 | `generate_insufficient_data_response(query, ..., client=self.async_client, ...)` | `temperature=self.mode.planning_temperature` |
| 849 | `synthesize_report(self.client, query, ...)` | `temperature=self.mode.synthesis_temperature` |
| 871 | `synthesize_draft(self.client, query, ...)` | `temperature=self.mode.synthesis_temperature` |
| 880 | `run_deep_skeptic_pass(self.async_client, draft, ...)` | `temperature=self.mode.synthesis_temperature` |
| 888 | `run_skeptic_combined(self.async_client, draft, ...)` | `temperature=self.mode.synthesis_temperature` |
| 903 | `synthesize_final(self.client, query, draft, ...)` | `temperature=self.mode.synthesis_temperature` |
| 212 | `evaluate_report(client=self.client, ...)` | `temperature=self.mode.planning_temperature` |
| 271 | `generate_refined_queries(self.client, query, report, ...)` | `temperature=self.mode.planning_temperature` |
| 276 | `generate_followup_questions(self.client, query, report, ...)` | `temperature=self.mode.planning_temperature` |
| 343 | `synthesize_mini_report(...)` (via `asyncio.to_thread`) | `temperature=self.mode.synthesis_temperature` |
| 991, 1074 | `refine_query(self.client, query, ...)` | `temperature=self.mode.planning_temperature` |

### MCP server call sites (no agent.py involvement)

Two MCP tools call module functions directly without going through agent.py:

| MCP tool | Calls | Temperature handling |
|----------|-------|-----------------------|
| `critique_report` (line 174) | `critique_report_file()` → inline `messages.create` at `critique.py:280` | Uses default temp (1.0). MCP doesn't have a mode object. Acceptable — critique is a standalone tool, not part of the research pipeline. |
| `generate_followups` (line 219) | `generate_followup_questions()` at `iterate.py:194` | Uses default temp (1.0). Same reasoning. |

These MCP tools don't have access to `ResearchMode` — they use `AUTO_DETECT_MODEL` directly. The `temperature: float = 1.0` default on each function ensures MCP paths work unchanged.

### What must NOT change?

- No prompt text changes. Temperature is passed to the API, not embedded in prompts.
- No model routing changes. `planning_model`, `relevance_model`, `model` fields untouched.
- All existing test mocks must still work — the new `temperature` param defaults to 1.0 in each function signature, so callers that don't pass it get API-default behavior.
- Report output format unchanged.
- MCP tool behavior unchanged (they use defaults).

### How will we know it worked?

1. **Unit tests on modes.py:**
   - `ResearchMode.quick().planning_temperature == 0.2`
   - `ResearchMode.standard().summarize_temperature == 0.5`
   - `ResearchMode.deep().synthesis_temperature == 0.8`
   - Validation rejects `planning_temperature=-0.1` and `planning_temperature=1.5`

2. **Integration test (1 representative per temperature tier):**
   - Mock Anthropic client, run a standard research query.
   - Assert `messages.create` was called with `temperature=0.2` for the decompose call.
   - Assert `messages.create` was called with `temperature=0.5` for a summarize call.
   - Assert `messages.stream` was called with `temperature=0.8` for synthesis.

3. **ModeInfo test:** `list_modes()` returns temperature fields.

4. **Full suite:** `python3 -m pytest tests/ -q` → 948+ pass.

### Most likely way this plan is wrong?

The wrapper chains (summarize, skeptic, relevance) are 3-4 functions deep. If any intermediate wrapper has a test that mocks it at a specific call boundary, adding the `temperature` param could cause a mock signature mismatch. Mitigation: the `temperature` param defaults to 1.0 on every function, so `**kwargs` and positional-agnostic mocks survive. But keyword-explicit mocks (e.g., `mock.assert_called_with(model=..., ...)`) will need `temperature=` added.

### Exact steps

1. Add 3 temperature fields + validation to `ResearchMode` in `modes.py`.
2. Add 3 temperature fields to `ModeInfo` in `results.py`.
3. Update `list_modes()` in `__init__.py`.
4. Thread temperature through the 3 wrapper chains:
   - `summarize_all` → `summarize_content` → `summarize_chunk`: add `temperature` param at each level.
   - `run_deep_skeptic_pass` / `run_skeptic_combined` → individual skeptics → `_call_skeptic`: add `temperature` param at each level.
   - `evaluate_sources` → `score_source`: use `mode.planning_temperature` inside `evaluate_sources` closure.
5. Add `temperature` param to standalone functions: `decompose_query`, `auto_detect_context`, `refine_query`, `identify_coverage_gaps`, `generate_refined_queries`, `generate_followup_questions`, `evaluate_report`, `generate_insufficient_data_response`.
6. Add `temperature` param to synthesize.py functions: `synthesize_report`, `synthesize_draft`, `synthesize_final`, `synthesize_mini_report`.
7. Update all agent.py call sites to pass appropriate `self.mode.*_temperature`.
8. Write unit tests for mode fields and validation.
9. Write integration test verifying temperature kwarg reaches the API client.
10. Run `python3 -m pytest tests/ -q`.
11. Commit: `feat(27-3): add per-task temperature controls to ResearchMode`

---

## Plan Quality Gate

| Question | Answer |
|----------|--------|
| What exactly is changing? | 3 items: `sanitize_content()` becomes idempotent (1 line + 1 test update), vague query gate added (~40 lines in query_validation + ~8 lines in agent), 3 temperature fields on ResearchMode + routing to 16 call sites across 10 modules |
| What must NOT change? | Sanitization output for never-sanitized input. Query decomposition logic. Report format. MCP tool behavior (default temps). All 948 existing tests except `test_ampersand_before_angle_brackets`. |
| How will we know it worked? | Idempotency invariant holds. Vague queries rejected with helpful messages. Temperature kwargs reach API client (verified by mock). Full test suite passes. |
| Most likely way this plan is wrong? | (1) `html.unescape` converts unexpected HTML entities in web content — accepted, correct for LLM prompts. (2) VAGUE_WORDS set is too small for subtle cases — accepted, ship and monitor. (3) Wrapper chain plumbing (summarize 3-deep, skeptic 3-deep) may break keyword-explicit test mocks that don't expect the new `temperature` param. |

---

## Feed-Forward

- **Hardest decision:** Whether to add a `temperature` function param to every module function vs. passing the entire mode object. Chose per-param (matching Cycle 21's model routing pattern) because most modules don't need the full mode object, and adding it would increase coupling. The tradeoff is mechanical edits through 3-deep wrapper chains.

- **Rejected alternatives:** (1) Passing the entire `ResearchMode` to every function — too much coupling for a single field. (2) A global/module-level temperature constant — violates the "config on the dataclass" convention. (3) `html.escape()` for idempotency — also not idempotent. (4) LLM-based vague detection — too expensive. (5) Exporting `VagueQueryError` from `__init__.py` — no concrete caller needs it; `ResearchError` catch covers all paths.

- **Least confident:** The 3-deep wrapper chains for summarization (`summarize_all` → `summarize_content` → `summarize_chunk`) and skeptic (`run_deep_skeptic_pass` → individual agents → `_call_skeptic`). Each level needs a `temperature` param added and forwarded. The implementation is mechanical, but existing tests that mock at intermediate boundaries (e.g., mocking `summarize_chunk` inside a `summarize_content` test) may need their mock call expectations updated to include `temperature=`. The `auto_detect_context` concern from the prior plan version is resolved — it already accepts a `model` param, and `agent.py` just doesn't pass it (uses the default). Adding `temperature` follows the same pattern: add param with default, agent.py passes the value.
