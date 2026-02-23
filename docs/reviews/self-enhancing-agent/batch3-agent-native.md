# Agent-Native Reviewer — Review Findings

**PR:** Self-Enhancing Agent (self-critique feedback loop)
**Branch:** self-enhancing-agent (bad292e..57bf44e)
**Date:** 2026-02-23
**Agent:** agent-native-reviewer

## Findings

### Self-critique has no CLI entry point
- **Severity:** P1
- **File:** research_agent/agent.py:126-157, cli.py (no --critique flag)
- **Issue:** An LLM agent orchestrating this tool cannot invoke critique independently. Critique only runs as a hidden side effect of `--standard` or `--deep` runs. Cannot re-evaluate a previous report or critique a report from a different source.
- **Suggestion:** Add `--critique <report-path>` CLI subcommand that accepts a report and outputs CritiqueResult.

### Critique results invisible to CLI consumers
- **Severity:** P1
- **File:** research_agent/agent.py:151-153, cli.py (no critique output)
- **Issue:** After research completes, CLI prints the report but says nothing about critique scores. Results silently written to YAML in `reports/meta/`. Classic "silent action" anti-pattern — agents get zero quality feedback.
- **Suggestion:** Print one-line summary to stdout: `Self-critique: mean=3.8, pass=True (reports/meta/critique-music_1234567890.yaml)`

### Critique history has no read path via CLI
- **Severity:** P1
- **File:** research_agent/context.py:228-285 (load_critique_history, internal only)
- **Issue:** Agents cannot ask "what are my recurring weaknesses?" without parsing YAML files manually. The aggregation function exists internally but has no CLI exposure.
- **Suggestion:** Add `--critique-history` CLI flag to print summarized patterns.

### No way to opt out of critique per-run
- **Severity:** P2
- **File:** research_agent/agent.py:135-136
- **Issue:** Quick mode skips critique (hardcoded), but there's no `--no-critique` flag for standard/deep modes. Agents cannot control cost or speed by skipping critique.
- **Suggestion:** Add `--no-critique` CLI flag plumbed through to agent initialization.

### CritiqueResult not in research() return value
- **Severity:** P2
- **File:** research_agent/agent.py:164-166
- **Issue:** `research()` returns `str` (report text only). CritiqueResult stored on private `self._last_critique` attribute. Programmatic consumers must reach into private state to inspect quality.
- **Suggestion:** Return a `ResearchResult` dataclass with both report text and optional CritiqueResult, or add a public `last_critique` property.

### Critique threshold not configurable
- **Severity:** P3
- **File:** research_agent/context.py:137
- **Issue:** `_MIN_CRITIQUES_FOR_GUIDANCE = 3` is hardcoded. Agents cannot tune when the adaptive feedback loop activates.
- **Suggestion:** Expose as parameter on `load_critique_history()` or field on `CycleConfig`.

### Hardcoded critique output directory
- **Severity:** P2
- **File:** research_agent/agent.py:149
- **Issue:** `Path("reports/meta")` is hardcoded relative path. No CLI flag to control meta directory. If invoked from different directory, files land in unexpected locations.
- **Suggestion:** Derive from report output path or add `--meta-dir` option.

### YAML output format is strong agent-native choice (POSITIVE)
- **Severity:** N/A (positive finding)
- **File:** research_agent/critique.py:254-266
- **Issue:** Structured YAML with typed fields is excellent for machine consumption. Schema is clean and validated on read. The format is right — the issue is purely about access.
- **Suggestion:** No action needed.

### Adaptive feedback loop is genuinely agent-native (POSITIVE)
- **Severity:** N/A (positive finding)
- **File:** research_agent/context.py (load_critique_history → _summarize_patterns)
- **Issue:** Past critique scores influence future behavior through prompt injection. This is self-improving infrastructure — a strong agent-native pattern.
- **Suggestion:** No action needed.

## Agent-Native Score
- 5 of 11 capabilities are agent-accessible
- 6 new critique-related capabilities have no agent access path
- Verdict: NEEDS WORK — internal implementation is agent-friendly (YAML, sanitization, graceful degradation) but no CLI/API surface for agents to observe, control, or invoke critique independently

## Summary
- P1 (Critical): 3
- P2 (Important): 3
- P3 (Nice-to-have): 1
