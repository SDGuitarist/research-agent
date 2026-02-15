---
title: "Model String Unification via Frozen Dataclass"
date: 2026-02-15
category: architecture
tags: [dataclass, single-source-of-truth, model-config, frozen-dataclass]
module: modes.py, decompose.py, search.py, relevance.py, skeptic.py, agent.py
symptoms: "Model version scattered across 4+ module-level constants. Changing the model requires finding and updating every file."
severity: low
summary: "Per-module model constants create drift risk. Moving the model string into the frozen ResearchMode dataclass creates a single source of truth threaded through the pipeline."
---

# Model String Unification via Frozen Dataclass

## Problem

Four modules each defined their own model string constant:

```python
# decompose.py
DECOMPOSITION_MODEL = "claude-sonnet-4-20250514"

# search.py
REFINEMENT_MODEL = "claude-sonnet-4-20250514"

# relevance.py
SCORING_MODEL = "claude-sonnet-4-20250514"

# skeptic.py
SKEPTIC_MODEL = "claude-sonnet-4-20250514"
```

All four held the same value, but nothing enforced that. Updating the model meant finding and changing 4+ constants across 4 files. If you missed one, that module silently used a different model version with no error and no warning. The drift would only show up as subtle behavioral differences in output quality.

## Root Cause

Organic growth. Each module was built in a different cycle. When `decompose.py` needed a model string, it defined one locally. When `search.py` was added later, it did the same. Nobody introduced a shared constant because each module worked fine in isolation. By the time `skeptic.py` was added (Cycle 16), the pattern was already established in three places.

This is a common trajectory: local constants feel simpler when you write the first module, but every copy adds a coordination burden that compounds over time.

## Solution

Added a `model` field to the existing `ResearchMode` frozen dataclass in `modes.py`:

```python
@dataclass(frozen=True)
class ResearchMode:
    name: str
    max_sources: int
    search_rounds: int
    summarize_pass: bool
    model: str = "claude-sonnet-4-20250514"  # single source of truth

QUICK    = ResearchMode("quick",    4,  1, False)
STANDARD = ResearchMode("standard", 10, 2, False)
DEEP     = ResearchMode("deep",     12, 2, True)
```

Each module function now receives the model string as a parameter instead of reading a local constant:

```python
# Before
async def analyze_query(query, context):
    response = client.messages.create(model=DECOMPOSITION_MODEL, ...)

# After
async def analyze_query(query, context, model):
    response = client.messages.create(model=model, ...)
```

The agent orchestrator passes `self.mode.model` to every call. Removed all four module-level constants.

**Commit:** `9176aeb Cycle 17: Session 6 — architecture consistency`

## Pattern

**Configuration belongs in a central frozen dataclass, not in per-module constants.**

When to apply this:
- A value is the same across multiple modules (model strings, timeout durations, retry counts)
- Changing that value should affect all modules simultaneously
- The value logically belongs to a "run configuration" rather than a single module

When *not* to apply this:
- A constant is genuinely module-specific and would never need to match another module
- The value is a structural detail (like a prompt template) rather than a tunable parameter

The frozen dataclass is the right vehicle because it is immutable (no accidental mutation mid-pipeline), inspectable (you can log or return the full config), and already threaded through the pipeline as a parameter.

## Related

- [`agent-native-return-structured-data.md`](agent-native-return-structured-data.md) -- another architecture decision about how `ResearchMode` and structured data flow through the pipeline
- `research_agent/modes.py` -- the dataclass that now holds the `model` field
- `research_agent/agent.py` -- the orchestrator that passes `self.mode.model` to each module
