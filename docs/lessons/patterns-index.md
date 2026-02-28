---
title: Patterns Index
category: all
tags: [patterns, quick-reference, index]
cycles: 1-18
---

# Patterns Index

Searchable table of all patterns discovered across development cycles. Each row maps to a narrative section in one of the category files (`security.md`, `architecture.md`, `operations.md`, `process.md`).

**Multi-cycle patterns** (re-flagged across multiple cycles) are marked with multiple cycle numbers.

| Category | Key Takeaway | Cycle(s) | Detail File |
|----------|-------------|----------|-------------|
| **Planning** | Research existing solutions before coding—learn from their mistakes | 1 | process.md |
| **Planning** | Design features completely before coding—fewer mid-flight changes | 2-3 | architecture.md |
| **Planning** | Validate plans against actual codebase before implementing—file names and types drift | 6 | architecture.md |
| **Security** | Validate all external URLs; never pass secrets via CLI | 1 | security.md |
| **Security** | Layer prompt injection defenses: sanitize + XML boundaries + system prompts | 4 | security.md |
| **Security** | Security features should compound across cycles, not get replaced | 4 | security.md |
| **Security** | Sanitize all code paths including fallbacks—error paths are easy to forget | 6 | security.md |
| **Error Handling** | Catch specific exceptions; log failures from `gather()` | 1 | operations.md |
| **Error Handling** | Always have graceful fallbacks for optional enhancements (pass 2, refinement) | 2-3, 8 | architecture.md |
| **Error Handling** | Bare `except Exception` is the most recurring code smell—always fix it | 1, 2, 4 | security.md |
| **Error Handling** | Validate config values that would cause confusing downstream errors | 6 | architecture.md |
| **Performance** | Use connection pooling; limit concurrency; parallelize where safe | 1 | operations.md |
| **Performance** | New async pipeline components should be async—sync in async context kills parallelism | 6 | operations.md |
| **Architecture** | One file per responsibility; dataclass pipelines; fallback chains | 1 | architecture.md |
| **Architecture** | Frozen dataclasses make excellent configuration objects | 2-3 | architecture.md |
| **Architecture** | Extract shared logic into reusable methods when extending features | 6 | architecture.md |
| **Architecture** | Small source budgets (3) are fragile; 5-6 minimum for reliability | 4 | architecture.md |
| **Architecture** | Append to configuration (mode instructions) rather than replace—preserve existing behavior | 6 | architecture.md |
| **Testing** | Test API calls early; review code even for personal projects | 1 | process.md |
| **Testing** | Verify model access before optimizing for specific models | 2-3 | process.md |
| **Testing** | Inline validation tests confirm features work but don't catch regressions | 4 | process.md |
| **Review** | Dedicated review-only cycles find more issues than feature-building cycles | 4, Post-10 | process.md |
| **Review** | Be specific when requesting fixes—agents default to fixing everything in a category | 4 | process.md |
| **Review** | "Complete" plans still need review—security and edge cases emerge from reading code | 6 | process.md |
| **UX** | Show users what's happening (both queries) to build trust in automated processes | 2-3 | architecture.md |
| **UX** | For streaming output with metadata, print metadata first so users have context | 6 | architecture.md |
| **Code Quality** | Name magic numbers—future-you needs context on why "2x" or "30.0" | 6 | architecture.md |
| **Simplification** | When three reviewers say "too complex," believe them—simplest solution is usually correct | 7 | operations.md |
| **Simplification** | Prompt engineering often beats code—ask "can I solve this with LLM instructions?" first | 7 | operations.md |
| **Configuration** | Environment variables beat CLI flags for optional features and secrets | 7 | operations.md |
| **Filtering** | When you add filtering, budget must increase proportionally—attempts ≠ survivors | 7 | operations.md |
| **Async** | Use `asyncio.to_thread()` for sync libraries in async code | 7 | operations.md |
| **Testing** | Mock where the name is imported FROM, not where it's used | 7 | operations.md |
| **Planning** | Interview users before planning—assumptions miss real pain points | 8 | process.md |
| **Planning** | Minimal plans execute faster—fewer decisions, less code, easier review | 7 | process.md |
| **Architecture** | Additive enhancements eliminate regression risk by construction—baseline always preserved | 8-18 | architecture.md |
| **Architecture** | Multi-topic queries fail because no single search covers the intersection—decompose into components | 8 | architecture.md |
| **Planning** | Discovery interviews reframe the problem—"insufficient data" was a UX failure, not a data problem | 8 | process.md |
| **Validation** | Always validate LLM-generated structured output before using it—plausible ≠ correct | 8, 13, 16 | architecture.md |
| **Rate Limiting** | Default to serial with jitter for external API fan-out—parallel bursts trigger rate limits | 8 | operations.md |
| **Configuration** | Static context files personalize LLM behavior without per-query prompting or auto-learning complexity | 8 | architecture.md |
| **Error Handling** | Optional pipeline stages must have zero-cost fallbacks—fail back to pre-enhancement behavior | 8 | architecture.md |
| **Operations** | Verify integrations are active, not just built—graceful fallbacks hide silent degradation | 8+ | operations.md |
| **Debugging** | Instrument the pipeline before diagnosing—a --verbose flag costs 11 lines and saves hours | 8+ | operations.md |
| **Architecture** | When a downstream stage appears broken, check if upstream is starving it of input | 8+ | architecture.md |
| **Architecture** | Convert new data sources to existing intermediate types as early as possible—no downstream changes needed | 8+, 9, 18 | architecture.md |
| **Cost** | Before building complex fallback chains, check if your existing provider has a parameter you're not using | 8+ | operations.md |
| **Fetch** | Site-level bot protection has tiers—some block direct HTTP, some block headless browsers, some block everything | 9 | operations.md |
| **Fetch** | Live-test fallback services on actual blocked URLs before designing fallback chains—compatibility matrices beat documentation | 9 | operations.md |
| **Fetch** | Jina Reader is the highest-value free fetch tool—works on standard sites AND WeddingWire where even Tavily fails | 9 | operations.md |
| **Architecture** | One file per pipeline stage—cascade.py follows the same pattern as fetch.py, extract.py, etc. | 1, 9 | architecture.md |
| **Architecture** | Return existing intermediate types from new pipeline stages—zero downstream changes | 9 | architecture.md |
| **YAGNI** | Inline markers (`[Source: search snippet]`) beat structured metadata when the consumer is an LLM | 9 | architecture.md |
| **Cost** | Domain-filter expensive API calls—only fire Tavily Extract on high-value domains worth the credit | 9 | operations.md |
| **Debugging** | Not all fetch failures are bot blocks—check HTTP status codes (404 vs 403) before escalating | 9 | operations.md |
| **Testing** | Always live-test integrations before committing—Jina Search required an API key contrary to initial assumptions | 9 | operations.md |
| **Architecture** | Generic prompt templates + context file > hardcoded business specifics—templates work for ANY business | 10 | architecture.md |
| **Architecture** | Business context passes through the pipeline, not baked into prompts—separation of concerns | 10 | architecture.md |
| **Rate Limiting** | Batching (12/batch, 3s delay) + retry (1 retry, 2s sleep) reduces 429s but doesn't eliminate them at 30K tokens/min tier | 10 | operations.md |
| **Rate Limiting** | Structured summaries (5 chunks x N sources) multiply API calls—budget for this when choosing batch sizes | 10 | operations.md |
| **Prompting** | 12-section templates produce consistent analytical structure—omit-if-empty is better than always-include | 10 | architecture.md |
| **Prompting** | Structured extraction (FACTS/KEY QUOTES/TONE) gives synthesis richer input for analytical sections | 10 | architecture.md |
| **Testing** | Test data must be large enough to exercise the code path—500 repetitions wasn't enough for 5-chunk tests | 10 | operations.md |
| **Rate Limiting** | Batch-level rate limiting is meaningless if individual items fan out internally—rate limit at the request level, not the item level | Post-10, 11 | operations.md |
| **Security** | SSRF protection with separate validation and connection steps creates TOCTOU gaps—pin DNS or validate at the transport layer | Post-10 | security.md |
| **Security** | `follow_redirects=True` is an SSRF bypass unless every redirect target is re-validated | Post-10 | security.md |
| **Code Quality** | Duplicated utility functions across 5+ files is the most common smell in additive-pattern codebases—extract shared utilities early | Post-10, 12 | architecture.md |
| **Architecture** | Private function imports across module boundaries signal the function belongs in a shared module | Post-10 | architecture.md |
| **Testing** | Security-critical code that gets mocked out in tests is effectively untested—test the real validation logic | Post-10 | security.md |
| **Documentation** | When you tune parameters, update CLAUDE.md—stale docs mislead future reviewers | Post-10 | process.md |
| **Performance** | Deliberate sleep calls can account for more wall time than actual computation—audit sleep budgets periodically | Post-10 | operations.md |
| **Review** | Multi-agent parallel review catches cross-cutting concerns that single-perspective reviews miss | Post-10 | process.md |
| **Refactoring** | `replace_all` on substrings corrupts identifiers—`_sanitize` inside `test_sanitize` loses the `test_` prefix, silently dropping tests from collection | 12 | operations.md |
| **Testing** | Always compare collected test count against documented count after refactoring—silent drops mean name corruption | 12 | operations.md |
| **Performance** | Serial delays purely for rate-limit avoidance can be replaced with semaphores—overlap saves wall time while preserving safety | 12 | operations.md |
| **LLM Validation** | LLM instructions are requests, not guarantees—validate critical output requirements after generation and fix automatically | 12 | architecture.md |
| **Architecture** | Targeted regeneration of 2 sections is much cheaper than re-running the full pipeline—scope the fix to the failure | 12 | architecture.md |
| **Architecture** | Multi-pass synthesis (draft→review→final) catches errors single-pass cannot—separate generation from evaluation | 16 | architecture.md |
| **Architecture** | Stage-appropriate context slicing prevents business context from coloring factual sections | 16 | architecture.md |
| **Python** | `lstrip()` strips characters from a set, not string prefixes—use `removeprefix()` for known prefixes | 16 | architecture.md |
| **Code Quality** | Consolidated duplicate utility functions reduce drift—if a function exists in 2+ files, extract to shared module | 12 | architecture.md |
| **Code Quality** | Dead code accumulates during rapid iteration—schedule periodic sweep passes every 2-3 cycles | Post-10 | process.md |
| **Resilience** | LLM API calls need standardized retry with backoff—rate limits and timeouts are routine, not exceptional | 11 | operations.md |
| **LLM Validation** | Adversarial prompts find claims the generator would never flag—the author's blind spots are visible to a reviewer | 16 | architecture.md |
| **Query Design** | Keep initial queries under ~15 words—complex queries pull irrelevant sources that the relevance scorer drops | 17+ | operations.md |
| **Templates** | Business analysis templates generate filler for factual questions—need query-type detection to skip irrelevant sections | 17+ | operations.md |
| **Fetch** | LinkedIn is the agent's biggest blind spot—executive changes and hiring news often exist only there | 17+ | operations.md |
| **Fetch** | Review sites (TripAdvisor, Yelp, Google) are heavily bot-protected—the fetch cascade struggles with review extraction | 17+ | operations.md |
| **Architecture** | Agentic browsers (controlling real browser sessions) bypass bot detection and auth walls the fetch pipeline cannot | 17+ | architecture.md |
| **Operations** | The agent finds public record; humans find ground truth—treat reports as the public-facing layer, not the complete picture | 17+ | operations.md |
| **Operations** | "Insufficient data" can be the answer—when searching for something that should be publicly advertised, finding nothing is a meaningful finding | 17+ | operations.md |
| **Relevance** | Near-identical entity names fool the relevance scorer—"Lodge at Torrey Pines" (resort) vs "Torrey Pines Lodge" (state reserve) both pass as relevant | 17+ | operations.md |
| **Validation** | When module A validates data module B owns, delegate to B and translate the exception—don't duplicate valid-value sets | 18 | architecture.md |
| **Packaging** | Additive migrations (wrap, don't refactor) keep script-to-package conversions safe—zero changes to internal modules | 18 | architecture.md |
| **API Design** | Return typed objects from public APIs, not raw dicts—follows codebase pattern and provides IDE autocomplete + type safety | 18 | architecture.md |
| **API Design** | Library functions should not call `load_dotenv()` or have global side effects—the caller owns their environment | 18 | architecture.md |
| **API Design** | Validate env vars up front in public API wrappers—fail fast instead of 30s into the pipeline | 18 | architecture.md |
| **Architecture** | Private attr access between files in the same package is acceptable when the alternative breaks additive constraints | 18 | architecture.md |
| **Process** | Post-session validation Q3 ("least confident + what test catches it?") is the highest-value question—feeds forward into next session | 18 | process.md |
| **Process** | Validation questions yield most on design sessions, least on mechanical sessions—budget accordingly | 18 | process.md |
