---
status: pending
priority: p2
issue_id: "127"
tags: [code-review, temperature, cycle-27]
dependencies: []
unblocks: []
sub_priority: 1
---

# 127 - `generate_insufficient_data_response` uses wrong temperature tier

## Problem Statement

`generate_insufficient_data_response()` generates user-facing prose explaining why insufficient data was found, with suggestions for alternative queries. In `agent.py:846`, it receives `temperature=self.mode.planning_temperature` (0.2), which is the classification tier.

This function produces ~200-word natural language explanations — closer to synthesis (0.8) or summarization (0.5) than classification (0.2). A temperature of 0.2 will make these responses dry and formulaic.

## Findings

- **Source:** Python reviewer (Kieran) — all other 15 call sites are correctly classified
- **Location:** `research_agent/agent.py:846`, `research_agent/relevance.py:383`
- **Impact:** Low — responses are correct but may sound robotic. Not a bug, a misclassification.

## Proposed Solutions

### Option A: Use `summarize_temperature` (0.5)
- Pros: Middle ground, the response summarizes why data is insufficient
- Cons: Slightly more variable than classification
- Effort: Small (1 line)
- Risk: None

### Option B: Use `synthesis_temperature` (0.8)
- Pros: Most natural prose, matches the task type (user-facing explanation)
- Cons: May be too creative for a "sorry, not enough data" message
- Effort: Small (1 line)
- Risk: None

## Recommended Action

Option A — `summarize_temperature` is the better fit. The response is informational prose, not creative synthesis.

## Acceptance Criteria

- [ ] `agent.py:846` passes `temperature=self.mode.summarize_temperature`
- [ ] Existing tests still pass
