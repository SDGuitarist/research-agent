---
status: pending
priority: p2
issue_id: "026"
tags: [code-review, security, dos]
dependencies: []
---

# No HTTP Response Size Limits on Fetching

## Problem Statement

`fetch.py:_fetch_single()` calls `response.text` which reads the entire response into memory. While `extract.py` has `MAX_HTML_SIZE = 5MB`, this check occurs AFTER download. A malicious server could send a multi-gigabyte response causing OOM. Same issue in `cascade.py:136`.

## Findings

- **Source:** Security Sentinel agent, Performance Oracle agent
- **Location:** `research_agent/fetch.py:171-214`, `research_agent/cascade.py:136`

## Proposed Solutions

### Option A: Streaming with size check (Recommended)
Use httpx streaming to check size incrementally and abort if exceeding limit.
- **Effort:** Medium (1-2 hours)

## Acceptance Criteria

- [ ] Responses exceeding MAX_HTML_SIZE are aborted before full download
- [ ] Both `fetch.py` and `cascade.py` are protected
- [ ] Test: oversized response is rejected
