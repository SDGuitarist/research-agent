---
title: Process Lessons
category: process
tags: [planning, review, testing, prompting, feed-forward, validation-questions]
cycles: [1, 4, 7, 8, 13, 18, post-10]
---

# Process Lessons

Planning, review cadence, testing discipline, prompting strategy, and feed-forward. These lessons shaped how the research agent was developed, not just what was built.

## Planning Decisions That Saved Time (Cycle 1)

### Research Before Coding Paid Off

We spent time upfront researching existing solutions (GPT Researcher, LangChain Open Deep Research, STORM) before writing any code. This revealed:

- **Multi-model strategy works**: Use cheaper models for summarization, expensive models for synthesis. We adopted this pattern.
- **Parallel report generation fails**: LangChain learned that generating report sections in parallel produces disjointed results. We avoided this mistake by using single-shot synthesis.
- **Citation tracking is essential**: All three projects emphasized source attribution. We built this in from the start.
- **Token explosion is real**: Research tasks use 15x more tokens than typical chat. We implemented chunking early.

### Constraint Mapping Prevented Scope Creep

Researching rate limits and API constraints before coding helped us choose DuckDuckGo for development (free) with a clear path to Tavily for production, set appropriate timeouts (15s) and concurrency limits (5 max).

### Failure Mode Analysis Guided Error Handling

Cataloging failure modes upfront meant we knew exactly what to catch. Without this research, we would have used bare `except Exception` everywhere.

## Mistakes to Avoid Next Time (Cycle 1)

### Don't Use Bare Exceptions

```python
# Bad
except Exception:
    return None

# Good
except (ConnectionError, TimeoutError, httpx.ConnectError):
    return None
```

### Don't Trust User-Provided URLs

Any URL from search results or user input could be `file:///etc/passwd`, `http://169.254.169.254/`, or `http://localhost:8080/admin`. Always validate before fetching.

> Cross-reference: See [security.md](security.md) for the SSRF doctrine that grew from this early lesson.

### Don't Pass Secrets via CLI Arguments

Visible in `ps aux`. Use environment variables only.

### Don't Ignore Rate Limits

Always add throttling for external requests. We initially had no concurrency limit on URL fetching.

### Don't Skip the Code Review

The SSRF vulnerability wasn't in the original implementation plan. It was caught during code review. Even for personal projects, review your own code with fresh eyes.

### Don't Hardcode Model IDs Without Testing

Always test API calls early with your actual credentials.

### Don't Mix Output Concerns

Separate user-facing progress from debug logging. `print()` scattered throughout makes it hard to redirect output properly.

## Sub-Query Divergence (Cycle 13)

### Concrete Examples Outperform Vague Instructions

Sub-queries were too similar to the original query (80% word overlap = restatement). Two gaps working together:

1. **Prompt gap**: Said "cover DIFFERENT angles" but gave no framework for what "different" means and no BAD/GOOD examples.
2. **Validation gap**: No maximum overlap check against the original query.

**Fix:** Added `MAX_OVERLAP_WITH_ORIGINAL = 0.8`, improved prompt with concrete rules and BAD/GOOD examples, and research facet guidance.

**Before:** 0 new results from first sub-query (restatement). **After:** All sub-queries explore distinct facets.

**Key Lesson:** Concrete examples and measurable rules outperform vague instructions. Validate with real query diagnostics before and after.

### Threshold Choice: 0.8 Not 0.7

Inter-sub-query duplicate threshold is 0.7. Max overlap with original is 0.8. Different thresholds serve different purposes: 0.7 catches duplicate sub-queries; 0.8 catches restatements of the original.

## Codebase Review: Review Methodology (Post-Cycle 10)

Four specialized review agents ran in parallel:
1. **Security Sentinel** — SSRF, prompt injection, secret handling, path traversal
2. **Performance Oracle** — async patterns, batching, rate limits, bottlenecks
3. **Pattern Recognition Specialist** — bugs, code smells, error handling, test gaps
4. **Codebase Explorer** — file inventory, architecture map, next-cycle plan cross-reference

Findings were deduplicated across agents and cross-referenced against already-planned work.

### Finding Summary: 27 Total

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 4 |
| Medium | 11 |
| Low | 11 |

### CLAUDE.md Discrepancies

Two items where documentation didn't match code — batch size and quick mode source count. **Lesson:** When you tune parameters, update CLAUDE.md.

### Test Coverage Gaps

- No `test_main.py` for CLI entry point
- Sync `research()` wrapper uses fragile string matching
- `_resolve_and_validate_host` mocked out in tests (security-critical logic never directly tested)

### Key Process Lessons from Review

- Multi-agent parallel review catches cross-cutting concerns that single-perspective reviews miss
- Dead code accumulates during rapid iteration — schedule periodic sweep passes every 2-3 cycles

> Cross-reference: See [security.md](security.md) for security findings. See [operations.md](operations.md) for performance findings.

## Minimal Plans Execute Faster (Cycle 7)

| Version | Planning Time | Implementation Time | Total |
|---------|---------------|---------------------|-------|
| Original (complex) | 2 hours | (not started) | - |
| Simplified | 30 min | 2 hours | 2.5 hours |

**Why simpler plans execute faster:** Fewer decisions, less code, fewer edge cases, easier to review.

## User Interviews Before Planning (Cycles 7-8)

### Interview Users Before Designing Features

Before Cycle 7, we conducted a structured interview that revealed DuckDuckGo's limitation wasn't obvious from code analysis alone. Before Cycle 8, a discovery interview surfaced that Alex views "insufficient data" as failures, reframing decomposition from nice-to-have to critical fix.

**Lesson:** Interview users before assuming you know the problem.

## Validation Questions Feed Forward Between Sessions (Cycle 18)

Asking 3 questions after each work session catches design risks early. **Q3 ("least confident + what test catches it?") is the highest value** — it forces identification of the weakest point.

In Cycle 18, Session 1's Q3 answer directly shaped Session 2's prompt to include explicit tests for a private attr contract.

**Validation questions yield most on design sessions, least on mechanical sessions.** Budget accordingly.
