---
status: complete
priority: p2
issue_id: "040"
tags: [code-review, quality]
dependencies: []
---

# Narrow httpx Exception Catch Should Use TransportError

## Problem Statement

The final catch clause in `synthesize.py` catches only `httpx.ReadError` and `httpx.RemoteProtocolError`. During streaming iteration (which bypasses the SDK's retry wrapper), other transport errors like `CloseError` or `WriteError` could also occur. The correct parent class `httpx.TransportError` covers all transport-level failures.

## Findings

- **kieran-python-reviewer**: The SDK's `_retry_request` wraps httpx exceptions into `APIConnectionError` for the initial request, but streaming body consumption (`stream.text_stream`) iterates raw httpx — transport errors escape unwrapped. `httpx.TransportError` is the right abstraction level.
- **code-simplicity-reviewer**: Agreed the catch is too specific for 2 of many possible failures.

## Proposed Solutions

### Option A: Replace with httpx.TransportError (Recommended)
- **Pros**: Catches all transport failures, more robust, simpler
- **Cons**: Slightly broader (also catches TimeoutException, but that path is already handled by APITimeoutError above)
- **Effort**: Small (3 lines)
- **Risk**: None — the broader catch is a safety net, not a behavior change

## Technical Details

- **Affected files**: `research_agent/synthesize.py` (lines 235, 338, 553)

## Acceptance Criteria

- [ ] `httpx.ReadError, httpx.RemoteProtocolError` replaced with `httpx.TransportError` at all 3 locations
- [ ] All 527 tests pass
