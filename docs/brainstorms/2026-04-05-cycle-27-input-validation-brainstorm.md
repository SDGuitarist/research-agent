# Cycle 27 Brainstorm: Input Validation & Generation Controls

**Date:** 2026-04-05
**Cycle:** 27
**Theme:** Prevent bad data from entering the pipeline. Tune generation knobs.

## Prior Phase Risk

> "Pre-summary abstention gate placement (C30). 75% confidence — the mechanism is validated but whether it belongs in summarize.py (per-source) or synthesize.py (all sources visible) needs planning."

This is a C30 risk, not C27. No unverified assumptions block this cycle. Accepted — we proceed normally.

---

## Item 1: Vague Query Detection

### What problem does this solve?

Queries like "stuff", "what's up", "things", "tell me about it" currently flow through the entire pipeline — decomposition, search, fetch, summarize, synthesize — burning API calls and producing garbage reports. The entropy audit (#1) identified this as the highest-impact single fix because it stops noise at the source.

### Where does it live?

Two options explored:

**Option A: New function in `query_validation.py`**

- Already has `meaningful_words()`, `STOP_WORDS`, `validate_query_list()`
- Natural home for query-level validation
- Called from `agent.py` at the top of `_research_async()`, before context loading or decomposition
- Returns a validation result (pass/fail + user-facing message)

**Option B: New function in `decompose.py`**

- Decomposition already does query analysis
- Could bundle vague detection into the LLM call
- But: vague detection should be cheap (no LLM call needed) and should happen before decomposition, not during it

**Decision: Option A.** Vague detection is a pre-flight check, not an analysis step. It should be fast (pure Python, no API call) and happen before any LLM work. `query_validation.py` is the right module.

### What counts as "vague"?

The roadmap says: "reject queries with <3 meaningful words, no domain-specific terms." Let's refine:

**Rejection criteria (all must fail for rejection — any passing = allowed):**

1. **Too few meaningful words:** After stripping stop words and punctuation, fewer than 2 meaningful words remain. Examples: "stuff" (1 word), "what's up" (0 meaningful), "the and or" (0 meaningful).

2. **No specificity signal:** The query has words but they're all generic. This is harder to define without an LLM. Options:
   - **Hard-coded generic word list:** ["stuff", "things", "something", "anything", "everything", "it", "whatever"]. Simple, fast, but incomplete.
   - **LLM-based classification:** Accurate but defeats the purpose (we're trying to avoid wasting API calls).
   - **Heuristic: meaningful words exist but total query is ≤3 words with no nouns/proper nouns.** Fragile — requires POS tagging.

**Decision: Keep it simple.** Use meaningful word count (≥2) as the primary gate. Add a small frozen set of "always reject" patterns for common garbage queries. No LLM, no POS tagging. We can tighten later if garbage queries still slip through.

### Edge cases to test

| Query | Expected | Why |
|-------|----------|-----|
| "stuff" | REJECT | 1 meaningful word, generic |
| "things" | REJECT | 1 meaningful word, generic |
| "what's up" | REJECT | 0 meaningful words (all stop words) |
| "the" | REJECT | 0 meaningful words |
| "" | REJECT | Empty |
| "   " | REJECT | Whitespace only |
| "?!..." | REJECT | Punctuation only |
| "AI" | REJECT | 1 meaningful word (borderline but too vague for research) |
| "quantum computing" | ACCEPT | 2 meaningful words, specific domain |
| "post-quantum" | ACCEPT | Hyphenated splits to 2 words: "post", "quantum" (per `meaningful_words()` behavior) |
| "standards," | ACCEPT | Punctuation stripped → "standards" = 1 word → REJECT? Actually this is borderline. Single-word queries like "standards" are vague without context. |
| "Python best practices" | ACCEPT | 3 meaningful words |
| "What is the best way to" | REJECT | After stop words: "best", "way" = 2 meaningful words → ACCEPT. Hmm — "best way" is vague but passes word count. |

**Insight from edge cases:** Pure word count misses "what is the best way to" (2 meaningful words but no topic). We need a minimum meaningful word count of **2** AND at least one word must be **4+ characters** (filters out queries that are all small filler words like "best", "way", "new", "old").

Wait — "best way" fails the 4-char rule ("best" = 4 chars, passes). Let me reconsider. The real signal is: does the query name a *topic*? "Best way" doesn't. "Best way to learn Python" does.

**Revised rule:** ≥2 meaningful words AND ≥1 meaningful word with 4+ characters that isn't in a "generic adjective" list. This is getting complex. Let me step back.

**Simplest viable rule:**
1. Strip stop words and punctuation using existing `meaningful_words()`
2. Require ≥2 meaningful words remaining
3. Reject if ALL remaining words are in a small "vague words" set: {"stuff", "things", "something", "anything", "everything", "whatever", "good", "bad", "best", "worst", "new", "old", "way", "ways"}

This handles the edge cases:
- "what is the best way to" → meaningful = {"best", "way"} → both in vague set → REJECT
- "best Python frameworks" → meaningful = {"best", "python", "frameworks"} → "python" not vague → ACCEPT
- "quantum computing" → neither word vague → ACCEPT

### Interface

```python
@dataclass(frozen=True)
class VagueQueryResult:
    is_valid: bool
    message: str  # User-facing rejection reason, empty if valid

def check_query_vagueness(query: str) -> VagueQueryResult:
    """Pre-flight check for vague/meaningless queries. No LLM call."""
```

Called from `agent.py:_research_async()` before context loading. On rejection, raise a `VagueQueryError` (new exception in `errors.py`) with the user-facing message.

### What about the MCP server?

The MCP `research` tool also calls into the agent. The vague check in `_research_async()` covers both CLI and MCP paths. The MCP tool should catch `VagueQueryError` and return a helpful message instead of a stack trace.

---

## Item 2: Idempotent Sanitization

### What problem does this solve?

`sanitize_content()` in `sanitize.py` does `text.replace("&", "&amp;")`. This is not idempotent: calling it twice produces `&amp;amp;`. The project has had multiple double-sanitization bugs (Cycles 19, 24, 25) all traced to this root cause. The "sanitize at boundary" convention mitigates it but doesn't eliminate the footgun.

### Options

**Option A: Use `html.escape()`**

Python's `html.escape()` does the same three replacements (`&`, `<`, `>`) plus `"` and `'`. It is also NOT idempotent — `html.escape("&amp;")` → `"&amp;amp;"`. So this doesn't solve the problem, just swaps one non-idempotent function for another. **Rejected.**

Wait — let me verify. `html.escape("&amp;")` → `"&amp;amp;"`. Yes, confirmed. `html.escape` is not idempotent either. The entropy audit suggestion was wrong on this specific point.

**Option B: Check-before-escape**

Before replacing `&`, check if it's already part of an entity (`&amp;`, `&lt;`, `&gt;`). Only escape bare `&`.

```python
import re

_ALREADY_ESCAPED = re.compile(r"&(amp|lt|gt);")

def sanitize_content(text: str) -> str:
    # First, un-escape any existing entities to normalize
    # Then re-escape everything once
    ...
```

This is complex and fragile. If content contains literal `&amp;` that should be preserved (e.g., someone writing about HTML entities), we'd corrupt it. **Rejected.**

**Option C: Unescape-then-escape (normalize)**

```python
import html

def sanitize_content(text: str) -> str:
    # Normalize: unescape any existing entities
    normalized = html.unescape(text)
    # Then escape once
    return normalized.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

`html.unescape("&amp;amp;")` → `"&amp;"` → `html.unescape` again → `"&"`. Wait, `html.unescape` only does one pass. So `html.unescape("&amp;amp;")` → `"&amp;"`. That's still an entity. Need a loop? No — one pass of unescape + one pass of escape is sufficient because:
- Input never sanitized: `"a & b"` → unescape → `"a & b"` → escape → `"a &amp; b"` ✓
- Input already sanitized once: `"a &amp; b"` → unescape → `"a & b"` → escape → `"a &amp; b"` ✓
- Input double-sanitized: `"a &amp;amp; b"` → unescape → `"a &amp; b"` → escape → `"a &amp;amp; b"` ✗ (still double-escaped)

So Option C handles single-sanitized idempotently but NOT double-sanitized. That's fine — double-sanitized input is the *bug we're preventing*, not input we expect to receive.

**But wait:** `html.unescape` unescapes ALL HTML entities, not just our three. If content contains `&nbsp;`, `&#x27;`, etc., unescape would convert them to literal characters, and our escape would then only re-escape `&`, `<`, `>`. This changes the output for content with HTML entities we don't care about. Example: `"price: &euro;50"` → unescape → `"price: €50"` → escape → `"price: €50"`. The `€` passes through unescaped. Is that a problem? For prompt injection defense, we only care about `<`, `>`, `&` (XML delimiters). Other entities becoming literal characters is fine — they can't break XML boundaries.

**Decision: Option C.** Unescape-then-escape. It's simple, idempotent for the case we care about (single-sanitized input), and doesn't change behavior for never-sanitized input. The only behavioral change is for content containing pre-existing HTML entities like `&nbsp;` — these become literal characters, which is actually more correct for our use case (we're not rendering HTML, we're building LLM prompts).

### Testing the idempotency invariant

The roadmap's acceptance criterion is: `sanitize_content(sanitize_content(text)) == sanitize_content(text)` for all inputs.

Test cases:
- Plain text: `"hello world"` → idempotent ✓
- Ampersand: `"a & b"` → `"a &amp; b"` → `"a &amp; b"` ✓
- Angle brackets: `"<script>"` → `"&lt;script&gt;"` → `"&lt;script&gt;"` ✓
- Pre-escaped: `"&amp;"` → `"&amp;"` → `"&amp;"` ✓
- Mixed: `"a & <b> &lt;c&gt;"` → verify idempotent ✓
- Unicode: `"émoji 🎉 & stuff"` → verify ✓
- Empty string: `""` → `""` ✓

### Interface change?

None. Same function signature, same module. The only change is internal implementation. All existing call sites work unchanged. All existing tests should pass (behavior only changes for double-call scenarios, which were bugs).

### Risk

If any existing code *depends* on the current non-idempotent behavior (unlikely but possible), this change would alter output. Mitigation: run full test suite. The 948 tests are the safety net.

---

## Item 3: Per-Task Temperature Controls

### What problem does this solve?

All `messages.create()` calls currently use the API default temperature. The epistemic calibration study found that temperature mainly affects stylistic exploration, not epistemic behavior (§3.2). But different tasks have different needs:
- **Classification tasks** (decomposition, relevance scoring, validation): Need stability. Low temperature (0.2–0.3).
- **Summarization tasks** (chunk summarization): Need some variety to avoid mechanical output. Mid temperature (0.5).
- **Creative/adversarial tasks** (skeptic checks, synthesis): Benefit from higher temperature (0.7–1.0).

### How does this follow the Cycle 21 pattern?

Cycle 21 added `planning_model` and `relevance_model` to `ResearchMode`. Temperature follows the same approach:

1. Add fields to the frozen `ResearchMode` dataclass
2. Route each call site to the appropriate field
3. Pass the value to `messages.create(temperature=...)`

### What fields to add?

The roadmap says `temperature`, `planning_temperature`, `synthesis_temperature`. Let me map the ~15 call sites to categories:

| Call site | Module | Task type | Temperature field |
|-----------|--------|-----------|-------------------|
| `decompose_query` | decompose.py | Classification | `planning_temperature` |
| `auto_detect_context` | context.py | Classification | `planning_temperature` |
| `_assess_relevance` (sync) | relevance.py | Classification | `planning_temperature` |
| `evaluate_sources` (async) | relevance.py | Classification | `planning_temperature` |
| `refine_query` | search.py | Classification | `planning_temperature` |
| `_identify_coverage_gaps` | coverage.py | Classification | `planning_temperature` |
| `_identify_topics` | iterate.py | Classification | `planning_temperature` |
| `_evaluate_iteration_value` | iterate.py | Classification | `planning_temperature` |
| `generate_followups` | critique.py | Creative | `synthesis_temperature` |
| `_critique_report_impl` | critique.py | Adversarial | `synthesis_temperature` |
| `_verify_evidence` (skeptic) | skeptic.py | Adversarial | `synthesis_temperature` |
| `_summarize_chunk` | summarize.py | Summarization | `summarize_temperature` |
| `synthesize_final` | synthesize.py | Creative | `synthesis_temperature` |

That's 4 categories but the roadmap only lists 3 fields. Summarization is a distinct category (mid-temp). Options:

**Option A: 3 fields** — `planning_temperature` (0.2), `summarize_temperature` (0.5), `synthesis_temperature` (0.8)

**Option B: 4 fields** — add `adversarial_temperature` for skeptic. But skeptic and synthesis both benefit from higher temperature for different reasons. Keeping them together is simpler.

**Decision: Option A with 3 fields.** Skeptic and critique use `synthesis_temperature` since they all benefit from creative/adversarial thinking. If we later need to separate skeptic, we add a field then (YAGNI).

### Default values

| Field | Default | Rationale |
|-------|---------|-----------|
| `planning_temperature` | 0.2 | Low for stable classification (study §3.2) |
| `summarize_temperature` | 0.5 | Mid for natural language generation without hallucination |
| `synthesis_temperature` | 0.8 | Higher for creative synthesis and adversarial thinking |

### How to pass temperature to call sites?

Each `messages.create()` call needs `temperature=self.mode.<field>`. But not all call sites have access to the mode object:

- `decompose.py`: Takes `model` param → add `temperature` param
- `context.py`: Uses `AUTO_DETECT_MODEL` directly → needs temperature param or use a constant
- `relevance.py`: Takes `model` param → add `temperature` param
- `search.py`: Takes `model` param → add `temperature` param
- `coverage.py`: Takes mode or model → check
- `iterate.py`: Uses `DEFAULT_MODEL` → needs param
- `critique.py`: Takes `model` param → add `temperature` param
- `skeptic.py`: Takes `model` param → add `temperature` param
- `summarize.py`: Takes `model` param → add `temperature` param
- `synthesize.py`: Has access to mode → use `self.mode.synthesis_temperature`

The pattern from Cycle 21: add a `temperature` parameter alongside the existing `model` parameter at each call site. The agent passes `self.mode.planning_temperature` or `self.mode.synthesis_temperature` as appropriate.

### Validation

Add to `__post_init__`:
```python
for field in ("planning_temperature", "summarize_temperature", "synthesis_temperature"):
    val = getattr(self, field)
    if not (0.0 <= val <= 1.0):
        errors.append(f"{field} must be between 0.0 and 1.0, got {val}")
```

### Testing

- Unit: Verify temperature fields on all three mode presets
- Unit: Verify validation rejects out-of-range temperatures
- Integration: Verify temperature is passed to `messages.create()` (mock the client, check kwargs)
- **NOT A/B testing** — the study says temperature is secondary to prompt design. We set reasonable defaults and ship. A/B testing would be testing noise.

### ModeInfo update

`results.py` has a `ModeInfo` dataclass that reports model routing. Add temperature fields for agent/MCP visibility. Follow the same pattern as `planning_model` and `relevance_model`.

---

## Cross-Cutting Concerns

### Ordering

The roadmap says: vague query detection → idempotent sanitization → temperature. But these three items are independent — no code dependencies between them. We could implement in any order.

**Recommended order:**
1. **Idempotent sanitization** — smallest change (~30 lines), eliminates a standing footgun, makes subsequent work safer
2. **Vague query detection** — new feature (~60 lines), uses existing `meaningful_words()` from `query_validation.py`
3. **Per-task temperature** — touches the most files (~15 call sites) but is mechanical once fields are defined

### Session breakdown

- **Session 1:** Idempotent sanitization (sanitize.py change + comprehensive tests)
- **Session 2:** Vague query detection (query_validation.py + agent.py + errors.py + MCP handler + tests)
- **Session 3:** Per-task temperature (modes.py + all call sites + results.py + tests)

### What must NOT change

- Existing sanitization behavior for never-sanitized input (only double-call behavior changes)
- Query decomposition logic (vague check is upstream, decompose is downstream)
- Report output format
- MCP tool interfaces (except adding temperature to ModeInfo output)
- Any module's public API signatures beyond adding optional parameters

---

## Feed-Forward

- **Hardest decision:** How to define "vague" without an LLM call. Pure word count misses queries like "what is the best way to" that have enough words but no topic. Settled on meaningful word count + vague word set, but this is a heuristic that will have false negatives. The alternative (LLM-based classification) defeats the purpose of saving API calls.

- **Rejected alternatives:** (1) `html.escape()` for idempotent sanitization — also not idempotent, just moves the problem. (2) Regex-based "already escaped" detection — fragile and corrupts content with literal entity strings. (3) Four temperature fields (separate adversarial) — YAGNI, skeptic and synthesis share the same need for creative exploration. (4) LLM-based vague query detection — too expensive for a pre-flight check.

- **Least confident:** The vague word set heuristic. It will catch obvious garbage ("stuff", "what's the best way") but miss subtler vague queries like "tell me about technology" (2 meaningful words, neither in vague set, but still too broad for useful research). We may need to revisit with a lightweight LLM check in a future cycle if false negatives are a problem. For now, catching the obvious cases is a significant improvement over catching nothing.
