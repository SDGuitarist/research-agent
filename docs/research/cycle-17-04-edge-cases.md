# Cycle 17-04: Edge Case Analysis

**Date:** 2026-02-12
**Type:** Research (no code, no planning)
**Scope:** Eight specific edge cases derived from codebase architecture (17-01) and failure modes (17-03)
**Method:** For each edge case: what should happen, what would actually happen in the current codebase, what needs to be built

---

## Edge Case 1: Gap Schema Is Empty (Brand New Property, Nothing Populated)

A user creates a gap schema for a property they've never researched. Every category has `status: unknown`, no `last_verified`, no findings, no dependencies. The schema is structurally valid but contains zero intelligence.

### What should happen

The system should treat this as a "full discovery" run. Every gap is equally important because nothing is known. The research pipeline should:

1. Recognize the empty schema as valid (not malformed)
2. Prioritize gaps by structural importance rather than staleness (since nothing is stale — everything is simply unknown)
3. Select a manageable subset per run (you can't research 50 unknowns in one pass)
4. After the run, update the gaps that were researched with `status: verified`, `last_verified: <timestamp>`, and populated findings
5. Leave un-researched gaps as `unknown` for the next cycle

### What would actually happen in the current codebase

Nothing useful. The current codebase has no gap schema support at all (17-01, Section 1: "No structured data parsing — no YAML, no JSON, no status flags"). `context.py` reads a single markdown file and slices it by `##` headings. A YAML block inside that file would be passed as raw text into the synthesis prompt — the LLM would see it but wouldn't process it programmatically.

More specifically:

- **No schema parser exists.** An empty schema file would either be ignored (if it's a separate file that nothing reads) or passed as opaque text (if embedded in `research_context.md`).
- **No prioritization logic exists.** The pipeline processes a single query per run. It doesn't select gaps, rank them, or decide what to research next.
- **No state update exists.** After a run completes, nothing writes back to any schema file. Results go to a markdown report and that's it (17-01, Section 7: "No persistent state between runs").

### What needs to be built

1. **Schema parser** — reads and validates the gap schema structure. Must distinguish between "schema exists but is empty" (valid state) and "schema file is missing" (different valid state) and "schema file is malformed" (error state). References F2.1 from 17-03.
2. **Empty-schema prioritizer** — when all gaps are `unknown`, falls back to a priority heuristic that doesn't depend on staleness. Options: user-defined priority field, category importance ranking, or simple round-robin.
3. **Gap selection logic** — given a set of gaps, selects which ones to research this cycle. Needs a `max_gaps_per_run` parameter to prevent overload.
4. **State writer** — after a successful run, writes updated gap statuses back to the schema file. Must use atomic writes (17-03, F4.4 recommendation).

---

## Edge Case 2: Gap Schema Is Fully Populated (Everything Known)

Every gap has `status: verified`, a recent `last_verified` timestamp, and populated findings. There is nothing unknown and nothing stale.

### What should happen

The system should recognize that no gaps need active research and communicate this clearly. Possible behaviors:

1. **Skip research, report status only** — output a brief summary: "All 47 gaps verified as of [dates]. Next staleness check will flag gaps after [earliest TTL expiry]."
2. **Suggest deepening** — "All gaps have baseline intelligence. Consider running a deep-mode pass on [highest-value gaps] to enrich findings."
3. **Run anyway if explicitly requested** — if the user provides a query, run it regardless of gap status. The schema informs but shouldn't block.

What should NOT happen: running a full research cycle and re-verifying everything. That wastes API costs and produces reports full of "no change" findings.

### What would actually happen in the current codebase

The pipeline would run normally because it doesn't know about gap schemas. The user's query drives everything. If they ask "research competitor X," the agent searches, fetches, synthesizes — completely unaware that everything about competitor X is already known and verified.

There's no mechanism to short-circuit a run based on existing intelligence.

### What needs to be built

1. **Pre-research check** — before entering the search pipeline, consult the gap schema. If all relevant gaps are verified and fresh, surface this to the user.
2. **Relevance gate extension** — the existing relevance gate (17-01, Seam G: `_evaluate_and_synthesize` returns `insufficient_data`, `short_report`, or `full_report`) could gain a fourth decision: `already_covered`. This fits the existing three-way branch pattern.
3. **Cost-awareness** — display estimated cost and say "your schema shows this is already covered — run anyway?" before proceeding. Aligns with the existing `--cost` flag in main.py.

---

## Edge Case 3: Staleness Rules Flip 20 Categories to STALE Simultaneously

A user hasn't run research in 60 days. A staleness check runs and 20 of 50 gaps exceed their TTL. All 20 flip to `stale` at once.

### What should happen

The system should NOT attempt to re-research all 20 stale gaps in a single run. That would overwhelm the pipeline (token budget, API costs, source relevance dilution). Instead:

1. **Batch and prioritize** — rank the 20 stale gaps by importance (RICE score, dependency position, time-since-last-verified). Select the top N for this run.
2. **Report the full staleness picture** — tell the user "20 gaps are stale. Researching top 5 this cycle. Remaining 15 will be addressed in subsequent runs."
3. **Prevent cascade amplification** — if stale gap A blocks gap B, don't also flip B to stale unless B's own TTL has expired. Staleness is about the gap's own freshness, not its dependencies' freshness. This directly addresses F4.1 from 17-03.
4. **Audit trail** — log which gaps were flipped, when, and why (TTL value, last_verified date, calculation).

### What would actually happen in the current codebase

Nothing. No staleness detection exists. No timestamps are stored. No automatic status flipping. The pipeline runs when the user manually invokes it and processes exactly one query with no awareness of what was researched before.

If someone built staleness detection naively (flip all expired gaps, trigger re-research for all), the most likely outcome is the failure cascade described in F4.1: 20 stale gaps → 20 research queries → API rate limits → partial results → corrupted baseline states.

### What needs to be built

1. **Per-gap TTL configuration** — not one global TTL. Different gap categories need different freshness windows. Founding dates: never stale. Pricing: 14-day TTL. Team composition: 90-day TTL. Addresses F4.2 from 17-03.
2. **Batch size limiter** — `max_stale_per_run` parameter. Hard cap on how many stale gaps get re-researched in one cycle.
3. **Staleness-only cascade rule** — a gap's status flips to stale based on its own `last_verified` vs its own TTL. Dependency status is tracked separately (a gap can be "fresh but blocked by stale dependency"). This prevents the cascade bomb.
4. **Staleness audit log** — append-only log of flip events. Enables debugging and undo.
5. **Priority-aware batch selection** — when N gaps are stale and only M can be processed, select M by priority score, not by arbitrary order.

---

## Edge Case 4: Google Drive Is Unreachable or Returns Auth Errors

The pipeline starts, attempts to load context from Google Drive, and gets either a network timeout, a 403 (permission denied), or a 401 (token expired).

### What should happen

The system must distinguish between three situations and handle each differently:

| Situation | What it means | Correct response |
|-----------|---------------|-----------------|
| No Drive doc configured | User doesn't use Drive for context | Run without context (current behavior for missing file) |
| Drive doc configured but API fails | Temporary infrastructure problem | Retry once, then warn user and offer to proceed without context |
| Drive doc configured but auth expired | User action required | Halt, tell user to re-authenticate, do not proceed with stale/missing context |

The critical principle: **"failed to load" must never be silently treated as "nothing to load."** This is the core of F1.2 from 17-03 — the pipeline currently returns `None` for both "no file" and "file read failed," and callers treat them identically.

### What would actually happen in the current codebase

`context.py:load_full_context()` catches `OSError` on line 43 and returns `None`. Google API exceptions (`google.auth.exceptions.RefreshError`, `googleapiclient.errors.HttpError`) are NOT `OSError` subclasses. They would propagate as unhandled exceptions and crash the pipeline with a traceback.

The crash is actually the better outcome compared to silent `None` return — at least the user knows something went wrong. The dangerous scenario would be if someone adds a broad `except Exception` to "fix" the crash. That would silently swallow the auth error and run the pipeline without context, producing reports that ignore the user's business positioning. The user might not notice for multiple runs.

### What needs to be built

1. **`ContextError` exception type** — added to `errors.py`. Subclasses: `ContextNotConfiguredError` (not an error, just a state), `ContextLoadError` (transient failure, retry-able), `ContextAuthError` (user action required). Addresses F5.3 from 17-03.
2. **Retry with backoff for transient failures** — the existing pattern in `_call_skeptic()` (skeptic.py) does 1 retry on rate limit/timeout. Same pattern should apply to Drive loading.
3. **Context loading result type** — instead of returning `str | None`, return a result object that carries both the content and the loading status. The pipeline can then branch on status, not on null-checking.
4. **Auth error user messaging** — clear, actionable message: "Google Drive authentication expired. Run `research-agent auth --refresh` to re-authenticate." Not a stack trace.

---

## Edge Case 5: Master Doc Format Changes (Sections Renamed, Reordered, Deleted)

The user (or a collaborator) edits the master context document in Google Drive. They rename "Target Market" to "Ideal Customer Profile," delete "Competitive Position," reorder sections, or add new ones that the system doesn't know about.

### What should happen

1. **Renamed sections** — the system should warn that expected sections are missing and show what sections it found. It should NOT silently proceed with partial context. Offer a mapping: "I found 'Ideal Customer Profile' but expected 'Target Market.' Are these the same?"
2. **Deleted sections** — warn clearly: "Section 'Competitive Position' not found in the master doc. This affects synthesis quality. Sections found: [list]."
3. **Reordered sections** — this should not matter. The system should match sections by heading text, not by position. The current `_extract_sections()` already does this (17-01, Section 1: "case-insensitive substring matching").
4. **New unknown sections** — ignore them by default (they weren't in the expected set). Optionally log them so the user knows they exist but aren't being used.

### What would actually happen in the current codebase

`_extract_sections()` in context.py does case-insensitive substring matching against hardcoded section name lists:

```python
_SEARCH_SECTIONS = ["Two Brands, One Operator", "Target Market",
                    "Search & Research Parameters", "Research Matching Criteria"]
_SYNTHESIS_SECTIONS = ["Two Brands, One Operator", "How the Brands Work Together",
                       "Target Market", "Key Differentiators", "Competitive Position"]
```

If "Target Market" is renamed to "Ideal Customer Profile":
- `_extract_sections()` won't match it (substring "Target Market" doesn't appear in "Ideal Customer Profile")
- That section's content is silently dropped from the context slice
- The pipeline continues with reduced context
- The user gets a report that ignores their target market positioning but has no indication that this happened

If "Competitive Position" is deleted:
- Same silent drop. `_extract_sections()` simply doesn't find it and returns everything else.

If sections are reordered:
- No problem. The parser is order-independent.

The failure mode is **silent context degradation** — the most dangerous kind because the user doesn't know what they're missing.

### What needs to be built

1. **Section validation with warnings** — after extracting sections, compare found vs. expected. If expected sections are missing, emit a warning (not just a log message — something the user sees in the output).
2. **Fuzzy section matching** — instead of exact substring match, use edit distance or semantic similarity to catch renames. "Target Market" → "Ideal Customer Profile" won't match by substring but might match by embedding similarity. Complexity tradeoff: simple Levenshtein distance catches typos but not semantic renames. LLM-based matching is accurate but adds cost and latency.
3. **Section manifest** — a small config that maps expected section names to their purpose. If the user renames a section, they update the manifest rather than modifying code. Stored alongside the gap schema.
4. **Validation on load, not on use** — check section completeness when loading context, not when building the synthesis prompt. Early detection means the user can fix the document before a costly research run.

---

## Edge Case 6: Gap Schema Has Circular Dependencies or Conflicting Status Flags

Gap A says it `blocks` Gap B. Gap B says it `blocks` Gap A. Or: Gap C has `status: verified` and `status: stale` in different fields, or `status: verified` with `last_verified: null`.

### What should happen

**Circular dependencies:**
1. Detect cycles during schema validation (before any research runs)
2. Report the cycle clearly: "Circular dependency detected: Gap A → Gap B → Gap A. Remove one of these dependency links."
3. Do not silently skip cycled gaps (this is the Kahn's algorithm failure described in F2.2 from 17-03)
4. Optionally: proceed with research but ignore the dependency ordering for cycled gaps (treat them as independent)

**Conflicting status flags:**
1. Define a single canonical `status` field. No separate fields that can contradict.
2. Validate internal consistency: `status: verified` requires `last_verified` to be non-null. `status: unknown` requires `last_verified` to be null. Violations are schema errors.
3. If conflicting state is detected, fail loudly with a specific error message rather than picking one value silently.

### What would actually happen in the current codebase

Nothing — no gap schema, no dependency graph, no status fields. But this is worth analyzing because it's a design-time decision that prevents runtime bugs.

If someone built gap schema support naively:
- **Circular dependencies with Kahn's algorithm** — cycled nodes never get added to the sorted output. They're silently dropped. The user's highest-priority gaps might vanish from the research queue with no indication.
- **Conflicting status flags** — depends on which field is checked. If code checks `status` and finds `verified`, it skips the gap. If code checks `last_verified` and finds `null`, it thinks the gap was never verified. Different code paths produce contradictory behavior.

### What needs to be built

1. **Cycle detection in schema validation** — use DFS-based cycle detection (more informative than Kahn's because it can report which nodes form the cycle). Run during schema load, not during prioritization.
2. **Schema validation rules** — a set of consistency checks:
   - `status: verified` → `last_verified` must be a valid timestamp
   - `status: unknown` → `last_verified` must be null
   - `status: stale` → `last_verified` must exist and be older than TTL
   - No self-references in `blocks`/`blocked_by`
   - All referenced gap IDs must exist in the schema
3. **`SchemaError` with structured details** — not just "schema invalid" but "gap 'pricing' has status 'verified' but last_verified is null; gap 'team' blocks itself." Addresses the "fail loudly" principle from F2.1 in 17-03.
4. **Repair suggestions** — for common issues (cycles, missing timestamps), suggest the fix: "To resolve: set last_verified for gap 'pricing' or change status to 'unknown'."

---

## Edge Case 7: Research Cycle Finds Nothing New (All Searches Return No Results)

The pipeline runs a research cycle targeting stale or unknown gaps. Search APIs return zero relevant results. No new pages to fetch, no new content to extract. The research cycle completes with nothing to report.

### What should happen

1. **Don't produce an empty report.** A blank or near-empty report is confusing and wastes the user's time opening it.
2. **Update gap metadata accurately** — the gap was checked, even though nothing was found. Update `last_checked: <timestamp>` (distinct from `last_verified` — checked means we looked, verified means we found something). This prevents infinite re-research loops (F4.6 from 17-03).
3. **Report the absence** — tell the user: "Researched 5 gaps. No new public information found for: [gap list]. These gaps will not be marked stale for another [TTL] days."
4. **Suggest alternative search strategies** — "No results for 'competitor X executive team' via web search. Consider: LinkedIn search, company 'About Us' page direct fetch, or press release archives."
5. **Don't corrupt the baseline** — if a delta-style output is in use, "no new findings" should NOT produce a delta that says "everything was removed." The baseline remains unchanged.

### What would actually happen in the current codebase

The pipeline has a relevance gate (17-01, Seam G). After search and summarization, `evaluate_sources()` scores summaries and returns a decision. If no summaries pass the relevance threshold, the decision is `insufficient_data`. The pipeline then:

1. Returns an early explanation: "I couldn't find enough relevant information to generate a reliable report" (agent.py, `_evaluate_and_synthesize`)
2. Does NOT save a report (auto-save only triggers on successful synthesis)
3. Does NOT update any state (no state exists to update)

So the existing behavior is partially correct — it doesn't produce an empty report. But it frames the outcome as a failure ("couldn't find enough") rather than a valid intelligence result ("nothing new exists publicly"). And it doesn't record that the search was attempted, so the next run would try the same search again.

### What needs to be built

1. **Distinguish "nothing found" from "search failed"** — `insufficient_data` currently covers both. A search that returns zero results is different from a search that errors out. The relevance gate needs a fourth decision: `no_new_findings` (searched successfully, found nothing relevant).
2. **`last_checked` timestamp** — separate from `last_verified`. Updated whenever a gap is researched, regardless of outcome. This is the key to preventing re-research loops.
3. **Null-result reporting** — a lightweight output format for "searched but found nothing." Not a full report, but a log entry with: gaps searched, queries used, result count, timestamp.
4. **Search strategy suggestions** — when web search returns nothing, suggest alternative approaches. Could be hardcoded per gap category or LLM-generated.

---

## Edge Case 8: Multiple Properties Researched in Same Cycle

The user manages three properties (companies/brands). They want to research all three in a single cycle rather than running three separate invocations.

### What should happen

1. **Isolated context per property** — each property has its own gap schema, its own context document, its own baseline state. Research for Property A must not leak into Property B's context or findings.
2. **Shared search infrastructure** — the search APIs, fetch infrastructure, and LLM clients can be shared across properties. No need to re-initialize per property.
3. **Cross-property intelligence** — if Property A and Property B share a competitor, findings about that competitor from Property A's research should be available to Property B's synthesis. This is a significant design decision: shared intelligence vs. strict isolation.
4. **Per-property cost tracking** — the user should see costs broken down by property, not a single aggregate.
5. **Parallel or sequential execution** — properties should be researchable in parallel (independent search queries) but synthesized with awareness of shared context. Order of execution shouldn't affect results.
6. **Failure isolation** — if Property A's research fails (search error, context load failure), Properties B and C should still complete.

### What would actually happen in the current codebase

The pipeline processes exactly one query per invocation. `ResearchAgent` is initialized once, runs one pipeline, and produces one report. The `research_context.md` file is loaded once and contains context for a single business entity.

To research three properties today, the user would:
1. Edit `research_context.md` to contain Property A's context
2. Run `python3 main.py --standard "research property A"`
3. Edit `research_context.md` to contain Property B's context
4. Run `python3 main.py --standard "research property B"`
5. Repeat for Property C

This is error-prone (user might forget to swap context), slow (sequential), and loses cross-property intelligence entirely.

### What needs to be built

1. **Multi-property configuration** — a config that maps property names to their context sources (Drive doc ID, gap schema path, baseline path). The user invokes `research-agent --properties A,B,C` instead of running three times.
2. **Property-scoped context loading** — `context.py` refactored to accept a property identifier and load the correct context document. Each property gets its own context loader instance or parameterized call.
3. **Property-scoped state** — gap schemas, baselines, staleness timestamps all namespaced by property. Directory structure like `state/property-a/schema.yaml`, `state/property-b/schema.yaml`.
4. **Execution orchestrator** — a layer above `ResearchAgent` that iterates over properties, managing which ones to research and in what order. Could be sequential (simpler) or parallel (faster but needs concurrency control for shared API clients).
5. **Cross-property deduplication** — if Properties A and B both need to research "Competitor X," the search/fetch/extract should happen once. The summarization and synthesis happen per-property with that property's context.
6. **Per-property error boundaries** — wrap each property's research in its own try/except so a failure in one doesn't abort all.

---

## Cross-Cutting Observations

### Pattern: The "Missing vs. Failed vs. Empty" Distinction

Multiple edge cases expose the same underlying gap: the current codebase treats absence as a single state, but the new features require at least three:

| State | Meaning | Example | Correct response |
|-------|---------|---------|-----------------|
| **Not configured** | User hasn't set this up | No Drive doc URL in config | Proceed without it (current behavior) |
| **Configured but empty** | Set up but no data yet | Empty gap schema | Treat as valid starting state |
| **Configured but failed** | Set up, has data, can't reach it | Drive auth expired | Warn user, don't proceed silently |

The current `None` return from context loaders conflates all three. Every new feature (gap schema, Drive loading, baselines) needs this three-way distinction.

### Pattern: Batch Size as Safety Valve

Edge cases 1, 3, and 8 all converge on the same solution: a configurable limit on how much work a single cycle does. Whether it's "how many unknown gaps to research," "how many stale gaps to re-research," or "how many properties to process," the answer is always "not everything at once."

This suggests a top-level `CycleConfig` that controls:
- `max_gaps_per_run` — limits gap processing (edge cases 1, 3)
- `max_properties_per_run` — limits property processing (edge case 8)
- `max_tokens_per_prompt` — limits context stuffing (relates to F5.2 from 17-03)

### Pattern: Audit Trail as Debugging Foundation

Edge cases 3, 6, and 7 all need an audit trail to be debuggable. "Why is this gap stale?" "Why was this gap skipped?" "Why did the last run find nothing?" Without a log of decisions, the user is left guessing.

The current pipeline prints progress to stdout and saves a final report. There's no structured log of decisions made during the run. A decision log — append-only, per-run, recording what was attempted and why — would address debugging needs across all edge cases.

### What Does NOT Need to Be Built (Yet)

Some complexity can be deferred:

- **Fuzzy section matching (Edge Case 5)** — start with exact matching plus clear warnings. Fuzzy matching adds complexity and false-match risk. Solve it with documentation first ("don't rename sections without updating the manifest").
- **Cross-property intelligence sharing (Edge Case 8)** — start with strict isolation per property. Shared intelligence is a feature, not a prerequisite. Users can manually cross-reference reports.
- **LLM-powered search strategy suggestions (Edge Case 7)** — start with hardcoded suggestions per gap category. LLM-generated suggestions add cost and unpredictability.
- **Automatic cycle scheduling** — all edge cases assume manual invocation. Automated scheduling (cron-style) adds race condition risks (F4.3 from 17-03) and should come later.
