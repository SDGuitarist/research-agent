# Cycle 17-03: Failure Mode Analysis for Planned Features

**Date:** 2026-02-12
**Type:** Research (no code, no planning)
**Scope:** Risk analysis for Google Drive loading, gap schema parsing, delta-only output, staleness detection
**Method:** Cross-referencing codebase architecture (17-01) with best practices research (17-02) to identify highest-risk failure modes

---

## Severity Key

| Rating | Meaning |
|--------|---------|
| **CRITICAL** | Data loss, corrupted state, or silent wrong results — hard to detect and recover from |
| **HIGH** | Pipeline failure or degraded output — noticeable but recoverable |
| **MEDIUM** | Reduced quality or added latency — annoying but functional |
| **LOW** | Edge case or cosmetic — unlikely or minor impact |

---

## 1. Google Drive Document Loading as Context Source

### Current Architecture Constraints

`context.py` is a 101-line module that reads a single local file synchronously via `Path.read_text()`. Returns `None` on failure. Callers handle `None` gracefully — the pipeline continues without personalization. No network IO, no authentication, no retries, no caching. The entire context loading path is fast and deterministic.

Adding Google Drive breaks every one of these assumptions.

### Failure Modes

#### F1.1 — Context Window Overflow from Large Documents
**Severity: CRITICAL** | Likelihood: High

Google Docs can be arbitrarily large. A 30-page strategy document is ~15K-25K tokens. The current architecture passes context directly into synthesis prompts with no truncation — `synthesize_report()` and `synthesize_final()` insert the full `business_context` string into the user prompt (synthesize.py:80+). The system prompt, query, sources, and instructions already consume significant context budget.

**Why it's critical:** There's no token budget enforcement anywhere in the current pipeline. Overflowing the context window causes either API errors (hard failure) or, worse, the model silently drops content from the middle of the prompt (soft failure with wrong results). The user won't know their business context was truncated.

**Specific risk in this codebase:** `synthesize_final()` already concatenates draft (sections 1-8) + skeptic findings + business context + sources + instructions. Adding a large Drive doc to `business_context` pushes this call closest to the limit.

#### F1.2 — OAuth Token Expiry Mid-Pipeline
**Severity: HIGH** | Likelihood: Medium

Google OAuth access tokens expire after 1 hour. The research pipeline for deep mode takes several minutes. If a user starts a deep research run and the token expires between context loads (context is loaded at multiple points — once for quick mode, separately for synthesis and skeptic in standard/deep), the second load fails while the first succeeded.

**Why it's dangerous:** The pipeline would have partial context — draft synthesis worked fine but final synthesis gets `None` context. This is an inconsistency the current error handling doesn't account for. The `None` return from `load_synthesis_context()` is treated as "no context file exists" which is a different situation from "context exists but I can't reach it right now."

#### F1.3 — API Rate Limits on Repeated Runs
**Severity: MEDIUM** | Likelihood: Medium

Google Drive API quota is 12,000 queries/100 seconds (per-user). Seems generous, but: if every `load_*_context()` call hits the API (no caching), and the user runs multiple quick research queries in a session, rate limits become reachable. More importantly, rate limit errors from Google Drive would be a new error class — the current `errors.py` hierarchy has no `ContextError`.

**Current handling gap:** `load_full_context()` catches `OSError` (line 43 of context.py). Google API errors are `google.auth.exceptions.*` and `googleapiclient.errors.HttpError` — completely different exception families. These would propagate as unhandled exceptions and crash the pipeline.

#### F1.4 — Rich Text → Markdown Conversion Fidelity
**Severity: MEDIUM** | Likelihood: High

Google Docs aren't markdown. They contain comments, suggestion mode edits, images, tables, headers with different levels, embedded drawings, and smart chips. The current `_extract_sections()` parser (context.py:48) relies on `## ` prefix matching for section detection. If the Google Docs → markdown converter produces different heading formats (ATX vs Setext, different levels), the section slicer breaks silently — returning either empty content or the entire unfiltered document.

**Silent failure path:** `_extract_sections()` returns the file header (everything before first `##`) if no sections match. The pipeline continues with partial/wrong context rather than failing. The user sees a report that ignores their competitive position, differentiators, etc. — but doesn't know why.

#### F1.5 — Latency Shift from Synchronous to Asynchronous
**Severity: LOW** | Likelihood: Certain

Local file read: <1ms. Google Drive API call: 200-2000ms. The current pipeline calls context loaders synchronously inside `_evaluate_and_synthesize()`. This blocks the event loop (already wrapped in `asyncio.to_thread` for synthesis, but context loading itself isn't async). For standard/deep mode, context is loaded twice (full + synthesis slice), so the added latency doubles.

Not a correctness issue, but changes the UX feel of the pipeline.

#### F1.6 — Document Permission Changes Between Runs
**Severity: MEDIUM** | Likelihood: Low

A document that was accessible for yesterday's research run might have its sharing settings changed today. Unlike a local file (deterministic existence check), Drive permissions are externally mutable. The failure mode: a "compare with last week's findings" workflow silently loses context because the source document was unshared.

---

## 2. Structured Gap Schema Parsing and Prioritization

### Current Architecture Constraints

The current context system is plain text only. `_extract_sections()` does line-by-line `##` prefix matching. No YAML parser, no JSON parser, no structured data extraction. The closest thing to structured data is the hardcoded section structure in synthesis prompts — but that's output structure, not input structure.

### Failure Modes

#### F2.1 — Malformed Schema Crashes the Pipeline
**Severity: CRITICAL** | Likelihood: High

YAML parsing is notoriously fragile. A single indentation error, a missing colon, or an unquoted string containing `:` breaks the entire parse. If the gap schema lives inside `research_context.md` (mixed with prose), the boundary detection between prose and YAML is another failure point.

**Specific risk:** Users (especially non-developers) editing a YAML schema in a markdown file will introduce parse errors. The current architecture has no validation layer — `context.py` just calls `Path.read_text()`. Adding YAML parsing means adding a new exception class (`SchemaError`?) and deciding: does a schema parse failure abort the pipeline, or does it degrade to "no schema" mode?

**The wrong answer is silent degradation.** If the schema exists but can't be parsed, the user should know. This is different from "no schema file exists."

#### F2.2 — Circular Dependencies in Gap DAG
**Severity: HIGH** | Likelihood: Medium

If gaps have `blocks`/`blocked_by` fields (as recommended in 17-02 best practices), cycles are possible: Gap A blocks Gap B, Gap B blocks Gap A. Topological sort (Kahn's algorithm) fails on cycles — it simply doesn't process the cycled nodes. If not detected, cycled gaps would be silently dropped from the prioritized list.

**Current architecture gap:** Nothing in the codebase does graph processing. This is a completely new capability with new failure modes that don't map to any existing error handling pattern.

#### F2.3 — Priority Calculation Edge Cases
**Severity: MEDIUM** | Likelihood: Medium

RICE scoring: `(Reach x Impact x Confidence) / Effort`. If `Effort = 0`, division by zero. If any field is missing, the calculation fails or produces `None` comparisons. If fields are strings instead of numbers ("high" instead of 3), type errors.

**Compound risk:** The LLM will be consuming these priority scores. If some gaps have scores and others don't (partial schema), the LLM might over-weight the scored gaps simply because they have explicit numbers, even if the unscored gaps are more important.

#### F2.4 — Schema Size Exceeds Context Budget
**Severity: HIGH** | Likelihood: Medium

A comprehensive gap schema with 50+ gaps, each with dependencies, sub-tasks, and metadata, could easily reach 5K-10K tokens. This competes directly with source summaries for context window space. The current pipeline passes all context and all sources into synthesis prompts — there's no budget allocation or priority-based pruning.

**Interaction with F1.1:** If both Drive documents AND gap schemas are loaded, the combined context payload could be 20K+ tokens before any research sources are added. The synthesis prompt would be dominated by context, starving the model of source material.

#### F2.5 — Schema Version Mismatch
**Severity: MEDIUM** | Likelihood: Low (at first), High (over time)

The best practices research (17-02) explicitly recommends a `version` field in schemas. If the schema format evolves (adding fields, renaming fields, changing status values), old schema files processed by new code — or vice versa — produce unpredictable results. Without explicit version checking and migration logic, this is a time bomb.

#### F2.6 — LLM Misinterprets Structured Data in Prompt
**Severity: MEDIUM** | Likelihood: Medium

The current architecture passes context as prose inside `<business_context>` XML tags. Embedding YAML or JSON structures inside a prompt alongside prose instructions creates ambiguity. The LLM might try to "complete" the YAML, treat status fields as instructions ("status: blocked" → the model thinks it should stop), or ignore the structure entirely and treat it as narrative.

**Specific risk with this codebase's security model:** `sanitize_content()` strips potential prompt injection from sources, but the gap schema is "trusted" context. If the schema contains user-authored text fields (gap descriptions, notes), those become trusted injection vectors.

---

## 3. Delta-Only Intelligence Briefing Output

### Current Architecture Constraints

Every run generates a complete report from scratch. `synthesize_report()`, `synthesize_draft()`, and `synthesize_final()` produce full markdown strings. The final report is built by string concatenation: `draft + "\n\n" + final_sections`. No state is saved between runs. No concept of "previous findings" or "what changed."

### Failure Modes

#### F3.1 — No Baseline on First Run (Bootstrap Problem)
**Severity: MEDIUM** | Likelihood: Certain (once)

The first run has no "before" state to compare against. Every finding is "new." If the delta output format is designed for changes, the first run either needs a special case (full report mode) or produces a misleading "everything is new" delta. The spec needs to define this behavior explicitly.

**Architectural decision:** Does the first run save state for future deltas, generate a full report, or both? This affects whether the output format is always delta or conditionally full/delta.

#### F3.2 — Semantic Diff Accuracy
**Severity: CRITICAL** | Likelihood: High

Comparing two LLM-generated reports for meaningful differences is fundamentally hard. String-level diff catches rewording without substance change (false positive). Semantic comparison misses subtle but important phrasing shifts (false negative). The LLM might rephrase "Company X has 50 employees" as "X employs approximately 50 people" — is that a change?

**Why it's critical:** False deltas erode trust. If the briefing says "NEW: Company X has ~50 employees" when that was already known, the user stops reading deltas carefully. Then they miss a real change.

**The current codebase has no diffing capability whatsoever.** This is entirely new logic. The closest analog is `_deduplicate_summaries()` in `synthesize.py`, which does exact URL matching — much simpler than semantic diffing.

#### F3.3 — Baseline State Corruption
**Severity: CRITICAL** | Likelihood: Low but catastrophic

If the saved "before" state gets corrupted (partial write, disk error, manual edit), every subsequent delta is wrong. Changes that were already reported get re-reported. Changes that were captured in the corrupted baseline are lost.

**No recovery path exists.** The current architecture has no checksumming, no backup states, no integrity verification. A corrupted baseline silently produces bad deltas indefinitely.

#### F3.4 — Context Window Doubling
**Severity: HIGH** | Likelihood: Certain

To generate a delta, the prompt needs both the previous state AND the new findings. This roughly doubles the context requirement for synthesis. Combined with F1.1 (Drive doc overflow) and F2.4 (schema size), the synthesis prompt could far exceed the model's effective context window.

**Specific risk:** `synthesize_final()` already receives: query + draft (sections 1-8, potentially 3K+ tokens) + skeptic findings + business context + sources + instructions. Adding "previous report state" as another input could push this past 100K tokens for deep mode.

#### F3.5 — Conditional Section Structure Breaks Diff
**Severity: HIGH** | Likelihood: Medium

The current report structure is not fixed. Section 11 (Adversarial Analysis) only exists if skeptic findings exist (synthesize.py and agent.py:366-386 — `SkepticError` → `findings = []` → section 11 skipped). If run A had skeptic findings and run B didn't (or vice versa), the section numbering shifts. A naive positional diff would compare the wrong sections.

**Broader issue:** If the new intelligence mode has a different section structure than the existing modes, delta comparison across mode changes is meaningless.

#### F3.6 — Stale Baseline from Failed Runs
**Severity: MEDIUM** | Likelihood: Medium

If a research run fails partway through (search error, API timeout, rate limit), should the partial results update the baseline? If yes: the baseline contains incomplete data, and the next successful run shows false deltas. If no: the user re-runs, and the delta includes changes that were already partially reported in the failed run's output.

**The current architecture has no concept of "run success/failure" as a persistent state.** Each run is fire-and-forget.

---

## 4. Staleness Detection with Automatic Status Flipping

### Current Architecture Constraints

No persistent state between runs. No timestamps on findings. No concept of "age" or "freshness." The `ResearchMode` dataclass is frozen (immutable) and contains no temporal parameters. The pipeline has no scheduled execution — it runs on-demand only.

### Failure Modes

#### F4.1 — Cascading Status Flips Through Dependency Graph
**Severity: CRITICAL** | Likelihood: Medium

If gap A depends on gap B, and B is flipped to "stale," should A also flip? If yes, a single stale gap can cascade through the entire dependency graph, flipping dozens of gaps to stale simultaneously. This is especially dangerous if the cascade triggers re-research for all flipped gaps — the system could attempt to re-research everything at once.

**Worst case:** A root-level gap (many dependents) goes stale → cascade flips 80% of gaps → next run tries to re-research all of them → API rate limits hit → partial results → baseline corruption (F3.3).

#### F4.2 — One-Size-Fits-All TTL Produces Wrong Results
**Severity: HIGH** | Likelihood: High

Different types of intelligence have vastly different freshness requirements. A competitor's founding date never goes stale. Their pricing page might change weekly. Their executive team changes quarterly. A single TTL (e.g., "30 days") produces both false positives (marking stable facts as stale) and false negatives (not catching fast-changing data).

**No metadata in the current architecture supports per-item TTL.** The gap schema would need TTL as a field, but that puts the burden on the user to set freshness thresholds for every gap — high friction, defeats the "zero friction" preference.

#### F4.3 — Race Condition: Staleness Check vs. Research Update
**Severity: HIGH** | Likelihood: Low (single-user), Higher (if automated)

If staleness detection runs concurrently with a research update:
1. Research run completes, writes "verified" status with fresh timestamp
2. Staleness detector reads old timestamp (before write completes)
3. Staleness detector flips status to "stale"
4. User sees contradictory state: fresh research results but "stale" status

The current architecture has no locking, no version fields, no optimistic concurrency control. The state file (which doesn't exist yet) would be vulnerable to read-write races.

#### F4.4 — State File Write Corruption
**Severity: CRITICAL** | Likelihood: Low but unrecoverable

Automatic status flipping means automatic writes to the state file. If the write fails mid-operation (process killed, disk full, permission error), the state file is partially written. JSON/YAML with a truncated closing bracket is unparseable.

**No write-safety patterns exist in the codebase.** The only file writes are report auto-saves in `main.py`, which are simple `Path.write_text()` calls with no atomic write pattern (write-to-temp + rename).

#### F4.5 — No Undo / Audit Trail for Automatic Flips
**Severity: MEDIUM** | Likelihood: Certain

If the system automatically flips a status and the flip was wrong (false positive staleness), there's no way to undo it. The user doesn't even know it happened unless they check the state file manually. Without an audit trail ("gap X flipped from verified to stale at timestamp T because last_verified was N days ago"), debugging staleness behavior is guesswork.

#### F4.6 — Infinite Re-Research Loop
**Severity: HIGH** | Likelihood: Low but possible

If staleness triggers automatic re-research, and the re-research finds the same information, and the staleness detector uses "last changed" (not "last checked") as its timestamp, the gap remains "stale" because nothing changed. This triggers another re-research cycle. The loop continues until the information actually changes or something external breaks the cycle.

**Mitigation is straightforward** (use "last verified" timestamp, not "last changed"), but the failure is subtle and could be introduced by a small implementation mistake.

---

## 5. Cross-Cutting Failure Modes

These failures span multiple features and are often more dangerous than individual feature failures because they involve unexpected interactions.

#### F5.1 — Error Cascade: Drive Failure → Schema Failure → Delta Failure
**Severity: CRITICAL** | Likelihood: Medium

If Google Drive is unavailable, context loading returns `None`. If the gap schema lives in the Drive document, it's also unavailable. If the previous baseline was generated with context+schema, the delta comparison is now comparing a context-rich baseline against a context-free new run — producing massive false deltas ("everything changed!").

**The current graceful degradation model doesn't account for this.** Each module degrades independently (skeptic fails → skip section 11; fetch fails → use snippet). But Drive failure affects context, schema, and delta simultaneously — the degradation compounds.

#### F5.2 — Context Window Budget War
**Severity: CRITICAL** | Likelihood: High

All four features add tokens to synthesis prompts:

| Component | Estimated tokens |
|-----------|-----------------|
| Drive document (large) | 10K-25K |
| Gap schema (50 gaps) | 5K-10K |
| Previous state for delta | 3K-8K |
| Staleness metadata | 500-1K |
| **New context total** | **18.5K-44K** |

The existing pipeline already uses substantial context for sources (summaries of 10-12 pages) + draft (sections 1-8) + skeptic findings. Adding 20K-40K tokens of new context pushes deep mode synthesis well past the point where model attention degrades.

**The best practices research (17-02) warns explicitly:** "Every token you add to the context window competes for the model's attention — stuffing 100K tokens of history degrades the model's ability to reason about what actually matters."

**No token budget allocation exists in the current codebase.** Nothing counts tokens before building prompts. Nothing prunes or prioritizes context when space is tight.

#### F5.3 — Exception Hierarchy Gaps
**Severity: HIGH** | Likelihood: Certain

The current `errors.py` has 6 exception types, all subclassing `ResearchError`: `SearchError`, `FetchError`, `ExtractionError`, `SynthesisError`, `RelevanceError`, `SkepticError`. None of these cover:

- Google Drive API errors (auth, rate limit, permission, not found)
- Schema parsing errors (malformed YAML, missing fields, invalid types)
- State file errors (corruption, version mismatch, lock failure)
- Delta computation errors (missing baseline, incompatible formats)
- Staleness errors (cascade failure, race condition)

Without proper exception types, these errors will either: (a) propagate as generic `Exception` and crash the pipeline, or (b) get caught by overly broad `except` clauses and silently swallowed. Both are bad.

#### F5.4 — Testing Combinatorial Explosion
**Severity: MEDIUM** | Likelihood: Certain

The current test suite has 385 tests for a stateless, single-file-input, single-output pipeline. Adding four features with external dependencies (Drive API), persistent state (schema file, baseline file), and temporal behavior (staleness) creates a combinatorial testing challenge:

- Drive available vs. unavailable vs. rate-limited vs. auth-expired
- Schema present vs. absent vs. malformed vs. partial
- Baseline present vs. absent vs. corrupted vs. version-mismatched
- Staleness: fresh vs. stale vs. mixed vs. cascading

Full coverage of these combinations is impractical. The risk is undertested interaction paths.

#### F5.5 — Graceful Degradation Hierarchy Undefined
**Severity: HIGH** | Likelihood: Certain

When the pipeline can't do everything, what does it cut first? The current degradation is simple: skeptic fails → skip adversarial section. But with four new features, the degradation order matters:

1. If context budget is tight, which gets pruned: Drive document, gap schema, or previous baseline?
2. If Drive is unavailable, should the pipeline run without context, or abort?
3. If the schema is malformed, should priorities be ignored (all gaps equal) or should the run abort?
4. If the baseline is corrupted, should it generate a full report instead of delta, or fail?

**Without an explicit degradation hierarchy, each feature will implement its own fallback logic independently, leading to inconsistent and unpredictable behavior.**

---

## 6. Highest-Risk Items (Prioritized)

Ordered by (severity x likelihood x difficulty of detection):

| Rank | ID | Failure | Why It's Top |
|------|-----|---------|------|
| 1 | F5.2 | Context window budget war | Certain to occur, affects output quality silently, no existing mitigation |
| 2 | F3.2 | Semantic diff accuracy | Hard problem with no clean solution, wrong deltas erode trust permanently |
| 3 | F5.1 | Error cascade across features | Single Drive failure corrupts schema + delta + staleness simultaneously |
| 4 | F1.1 | Context overflow from Drive docs | Large docs silently degrade synthesis quality |
| 5 | F4.1 | Cascading status flips | One stale gap can flip the entire graph |
| 6 | F2.1 | Malformed schema crashes pipeline | Users will introduce YAML errors; current error handling won't catch them |
| 7 | F3.3 | Baseline state corruption | Low probability but unrecoverable — silent wrong deltas forever |
| 8 | F5.3 | Exception hierarchy gaps | New error classes needed before any implementation begins |
| 9 | F4.4 | State file write corruption | No atomic write pattern exists in codebase |
| 10 | F3.4 | Context window doubling for delta | Compounds with F5.2 to make budget war worse |

---

## 7. Architectural Recommendations (Pre-Implementation)

These aren't a plan — they're constraints that any implementation should satisfy to avoid the highest-risk failures above.

**Token budget system (addresses F5.2, F1.1, F2.4, F3.4):**
Before building any prompt, count tokens across all components and enforce a budget. If over budget, prune by priority: staleness metadata first, then previous baseline (fall back to full report), then schema (fall back to top-N gaps only), then Drive context (fall back to section slicing).

**Atomic file writes (addresses F4.4, F3.3):**
Any state file write (baseline, schema, staleness timestamps) must use write-to-temp + atomic rename. This is a one-line change per write site but prevents the most catastrophic corruption scenarios.

**Explicit degradation hierarchy (addresses F5.5, F5.1):**
Define and document: "If X fails, the system does Y." Make degradation decisions explicit in code, not emergent from scattered `try/except` blocks.

**Exception types before features (addresses F5.3):**
Add `ContextError`, `SchemaError`, `StateError`, `DeltaError` to `errors.py` before implementing any feature. The error handling design constrains the feature design.

**Separate "missing" from "failed" (addresses F1.2, F2.1):**
The current `None` return from context loaders means "no context." But "Drive API failed" is different from "no Drive document configured." These need distinct return values or exceptions so the pipeline can degrade appropriately.
