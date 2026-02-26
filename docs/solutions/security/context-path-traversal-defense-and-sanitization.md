---
title: Context Handling Subsystem Security & Architecture Hardening
date: 2026-02-26
category: security
tags: [security, architecture, input-validation, prompt-injection-defense, api-design, agent-reuse, state-mutation]
components: [context.py, agent.py, decompose.py, synthesize.py, skeptic.py, __init__.py]
severity: high
root_cause: >
  Path traversal vulnerability combined with sentinel object pattern and
  state mutation in context loading pipeline; missing input validation and
  unsanitized LLM prompts exposed the system to file-read attacks and
  prevented safe agent reuse.
todos_resolved: [054, 055, 056, 057, 058, 059, 060]
commits: dbd0b80, 6183330, be02a2d, b4ee6f9, 1128e1e
---

# Context Handling Subsystem Security & Architecture Hardening

## Problem

The research agent's context-handling subsystem had seven interconnected
issues discovered during code review (todos 054-060). The anchor was a P1
path traversal vulnerability: `resolve_context_path()` accepted user input
like `--context ../../etc/passwd` without validation, allowing arbitrary
`.md` files to be read and sent to the Anthropic API. Surrounding this were
architectural issues — a sentinel `Path("__no_context__")` object, async
self-mutation breaking agent reuse, unsanitized LLM prompt inputs,
inconsistent XML tag naming, missing integration tests, and a public API
that lacked context control.

## Root Cause

The context system evolved incrementally without three critical layers:

1. **Input validation omission** — `resolve_context_path()` trusted user
   input, with no checks for path separators or containment.
2. **Sentinel pattern lock-in** — Early code used `Path("__no_context__")`
   to signal "skip context," forcing state mutation as the threading mechanism.
3. **API-level abstraction gap** — Context was treated as an implementation
   detail, not parameterized for programmatic callers.

## Solution

Six patterns were applied across 5 commits:

### Pattern 1: Defense-in-Depth Path Validation

Two layers in `resolve_context_path()`:

```python
# Layer 1: Character-level rejection
if "/" in name or "\\" in name or name.startswith("."):
    raise ValueError(f"Invalid context name: {name!r}")

# Layer 2: Containment check after resolution
path = (CONTEXTS_DIR / f"{name}.md").resolve()
if not str(path).startswith(str(CONTEXTS_DIR.resolve()) + "/"):
    raise ValueError(f"Context name {name!r} resolves outside contexts/")
```

Layer 1 catches obvious traversal attempts. Layer 2 catches anything that
slips through (symlinks, encoding tricks).

### Pattern 2: Eliminate Sentinel Objects

Replaced `Path("__no_context__")` with passing already-loaded content directly:

```python
# Before: decompose_query loaded context internally via a path
decompose_query(client, query, context_path=self._effective_context_path)

# After: agent loads context once, passes content
self._run_context = self._load_context_for(effective_context_path, effective_no_context)
decompose_query(client, query, context_content=self._run_context.content)
```

This removed `_effective_context_path`, `Path("__no_context__")`, and
decompose.py's dependency on `load_full_context`.

### Pattern 3: Local Variables for Async Safety

Replaced `self` mutation with local variables in `_research_async()`:

```python
# Before: mutated instance state
if detected is not None:
    self.context_path = detected    # Persists to next call!
else:
    self.no_context = True          # Persists to next call!

# After: local variables only
effective_context_path = self.context_path
effective_no_context = self.no_context
if detected is not None:
    effective_context_path = detected    # Local only
else:
    effective_no_context = True          # Local only
```

The agent's `__init__` configuration is now preserved across calls.

### Pattern 4: Sanitize at LLM Boundaries

Applied `sanitize_content()` and XML tags to `auto_detect_context()`:

```python
safe_query = sanitize_content(query)
safe_preview = sanitize_content(preview)
prompt = f"Given this research query:\n\n  <query>{safe_query}</query>\n\n..."
```

This was the only LLM prompt in the codebase without sanitization.

### Pattern 5: Consistent XML Tag Naming

Renamed `<business_context>` to `<research_context>` across all prompt
templates (synthesize.py, skeptic.py, modes.py) to match the generic
`context` parameter naming established in Session 3.

### Pattern 6: Public API Parity

Added `context: str | None` parameter to `run_research()` and
`run_research_async()`, plus exported `list_available_contexts` and
`resolve_context_path` in `__all__`:

```python
run_research("query", context="pfe")    # Use named context
run_research("query", context="none")   # Skip context
run_research("query")                   # Auto-detect (default)
```

## Key Code Changes

| File | Change | Purpose |
|------|--------|---------|
| `context.py` | Input validation + containment check in `resolve_context_path()` | Path traversal defense |
| `context.py` | `sanitize_content()` + `<query>` tags in `auto_detect_context()` | Prompt injection defense |
| `agent.py` | Remove `_effective_context_path` property, add `_run_context` | Eliminate sentinel, load once |
| `agent.py` | Local variables in `_research_async()` | Async-safe, agent reusable |
| `decompose.py` | Accept `context_content: str \| None` instead of `context_path` | Direct data, no file I/O |
| `synthesize.py`, `skeptic.py`, `modes.py` | `<business_context>` -> `<research_context>` | Naming consistency |
| `__init__.py` | `context` param on public API, export context utils | API parity |
| `tests/test_agent.py` | 4 integration tests for auto-detect | Close test gap |
| `tests/test_public_api.py` | 3 tests for context parameter | Verify public API |

## Prevention Strategies

### For Path/File Operations
- Any function accepting user-provided filenames must validate containment
  (not just existence). Use `Path.resolve()` + prefix check.
- Test with adversarial inputs: `../`, `../../`, absolute paths, `.env`.
- Input validation + output containment = defense in depth.

### For LLM Prompts
- Every user-facing value in an LLM prompt must pass through
  `sanitize_content()` before interpolation.
- Wrap user data in XML boundary tags (`<query>`, `<sources>`).
- Treat missing sanitization as a security bug, not a style issue.

### For Instance State
- Async methods should use local variables for per-run state.
- Only mutate `self` for state that must persist across calls.
- Test agent reuse: call `research()` twice on the same instance.

### For API Surface
- If a lower-level constructor accepts a parameter, the public API
  should expose it (or document why not).
- Export utility functions that programmatic callers need.

### For Naming Consistency
- XML tags in prompts should match parameter names in code.
- When renaming parameters, grep for corresponding prompt templates.

## Checklist for New Features

- [ ] User inputs validated (path safety, character checks, enum membership)
- [ ] LLM inputs sanitized with `sanitize_content()` + XML boundary tags
- [ ] No magic sentinel values — use `None`, `Enum`, or typed alternatives
- [ ] Async methods don't mutate `self` for per-run state
- [ ] XML tag names match code parameter names
- [ ] Unit tests + integration tests for the feature
- [ ] Public API exposes new capabilities with documentation

## Related Documentation

- [non-idempotent-sanitization-double-encode.md](../security/non-idempotent-sanitization-double-encode.md) — Sanitize-once-at-boundary pattern; same `sanitize_content()` function used here
- [ssrf-bypass-via-proxy-services.md](../security/ssrf-bypass-via-proxy-services.md) — Security validation bypass when new code paths skip shared validators
- [pip-installable-package-and-public-api.md](../architecture/pip-installable-package-and-public-api.md) — API design patterns, validation ownership
- [conditional-prompt-templates-by-context.md](../logic-errors/conditional-prompt-templates-by-context.md) — Context-conditional prompt branching pattern
- [agent-native-return-structured-data.md](../architecture/agent-native-return-structured-data.md) — Agent lifecycle and reuse patterns

## Risk Resolution

| Flagged Risk | What Happened | Lesson |
|---|---|---|
| Path traversal (security-sentinel, P1) | Fixed with two-layer defense; verified `--context ../CLAUDE` raises ValueError | Defense in depth: validate input characters AND check output containment |
| Sentinel Path fragility (3 agents flagged) | Eliminated by passing content directly; `Path("__no_context__")` removed entirely | Magic values are a design smell — use the type system |
| Self-mutation in async (4 agents flagged) | Local variables preserve agent config across calls | Async code must be reentrant by default |
| Unsanitized auto-detect prompt | Applied existing `sanitize_content()` pattern | New LLM prompts must follow established sanitization convention |
| XML tag drift | Unified to `<research_context>` | Rename parameters and prompt tags together |

## Three Questions

1. **Hardest pattern to extract from the fixes?**
   The relationship between the sentinel Path elimination (055) and the
   state mutation fix (056) — they're the same underlying issue (threading
   context state through the pipeline) solved in two different ways that
   had to be coordinated. Documenting them as separate patterns risks
   missing that they're two faces of "pass data, don't share mutable state."

2. **What did you consider documenting but left out, and why?**
   Considered a detailed section on XML tag centralization (constants
   module for all tag names). Left it out because the codebase only has
   ~5 XML tags and the overhead of a constants module isn't warranted yet.
   The naming consistency check is sufficient at current scale.

3. **What might future sessions miss that this solution doesn't cover?**
   The `sanitize_content()` function itself — if its escaping rules ever
   change (e.g., to handle new injection vectors), every call site trusts
   it implicitly. There's no test that verifies sanitization is applied at
   every LLM boundary, only tests at individual call sites. A grep-based
   CI check ("every `client.messages.create` call must have a preceding
   `sanitize_content`") would close this gap.
