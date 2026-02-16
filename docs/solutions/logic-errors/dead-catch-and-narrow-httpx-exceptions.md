---
title: "Dead APIConnectionError Catch and Too-Narrow httpx Exception Handling"
date: 2026-02-15
category: logic-errors
tags:
  - python
  - exception-handling
  - httpx
  - anthropic-sdk
  - dead-code
  - streaming
module: synthesize
symptoms:
  - unreachable except clause
  - uncaught httpx transport errors during streaming
  - potential unhandled exceptions in production
severity: P2
summary: >
  APIConnectionError is a subclass of APIError, making it dead code in a final
  catch clause that follows an except APIError handler. Additionally, catching
  only httpx.ReadError and httpx.RemoteProtocolError missed other transport
  failures during SDK streaming iteration.
---

## Problem

Two related exception-handling bugs in `research_agent/synthesize.py`, repeated
at 3 call sites (lines 235, 338, 553):

### 1. Dead code: APIConnectionError in final catch

```python
# Before — APIConnectionError is DEAD CODE here
except APIError as e:
    raise SynthesisError(f"API error: {e}")
except (SynthesisError, KeyboardInterrupt):
    raise
except (APIConnectionError, httpx.ReadError, httpx.RemoteProtocolError, ValueError) as e:
    raise SynthesisError(f"Synthesis failed: {e}")
```

`APIConnectionError` is a subclass of `APIError` in the Anthropic SDK. The
`except APIError` handler on the line above catches it first — the final clause
never executes for `APIConnectionError`.

### 2. Too-narrow httpx exception catch

During streaming iteration (`stream.text_stream`), the Anthropic SDK does **not**
wrap raw httpx transport errors. Only `httpx.ReadError` and
`httpx.RemoteProtocolError` were caught, but other transport failures like
`CloseError` and `WriteError` could escape unhandled.

## Root Cause

**Exception hierarchy misunderstanding.** Two independent issues:

1. Not recognizing that `APIConnectionError` inherits from `APIError`, making
   it unreachable after an `except APIError` handler.
2. Not recognizing that `httpx.TransportError` is the parent class for all
   transport-level failures, and that the SDK passes these through raw during
   streaming.

## Solution

Remove dead `APIConnectionError` from the import and all catch clauses. Replace
the two specific httpx exceptions with the parent `httpx.TransportError`:

```python
# After — clean and complete
from anthropic import Anthropic, RateLimitError, APIError, APITimeoutError

# ... (at each of the 3 call sites)
except APIError as e:
    raise SynthesisError(f"API error: {e}")
except (SynthesisError, KeyboardInterrupt):
    raise
except (httpx.TransportError, ValueError) as e:
    raise SynthesisError(f"Synthesis failed: {e}")
```

**Commit:** `5cb8a3d` — 527 tests pass.

## Key Insight: Anthropic SDK Exception Hierarchy

```
BaseException
└── Exception
    └── APIError              ← catches ALL API errors
        ├── APIConnectionError  ← subclass, caught by APIError first
        ├── APITimeoutError
        ├── RateLimitError
        ├── APIStatusError
        └── ...
```

If you need to handle `APIConnectionError` differently from other API errors,
it must appear **before** the `except APIError` clause.

## Key Insight: httpx During SDK Streaming

When iterating `stream.text_stream`, the SDK does not wrap httpx transport
errors. The hierarchy:

```
httpx.TransportError          ← catch this one
├── httpx.ReadError
├── httpx.WriteError
├── httpx.CloseError
├── httpx.ConnectError
├── httpx.RemoteProtocolError
└── ...
```

Catching `httpx.TransportError` covers all transport-level failures in one
clause.

## Prevention

1. **Check inheritance before catching.** When adding an exception to a catch
   clause, verify it isn't already caught by a parent class handler above.
2. **Catch parent classes for transport errors.** Unless you need different
   behavior per subclass, use `httpx.TransportError` instead of listing
   individual transport exceptions.
3. **Audit repeated patterns.** This bug was copy-pasted across 3 call sites.
   When fixing exception handling, search for all instances of the same pattern.

## Detection

Found during code review (Cycle 17 review action plan). Could also be detected
by:
- Static analysis tools that flag unreachable except clauses
- `pyright` / `mypy` with strict exception checking
- Manual review of exception handler ordering
