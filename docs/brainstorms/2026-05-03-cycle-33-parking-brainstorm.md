# Cycle 33 Brainstorm: Parking Decision

**Date:** 2026-05-03
**Type:** Triage (no work cycle started)
**Prior cycle:** 32 (hygiene bundle -- constant consolidation, dataclass conversion)

## Prior Phase Risk

> "The modes.py -> results.py import edge. If someone adds `from .modes
> import ...` to results.py, the circular import won't be caught until
> runtime. A CI rule (import-graph linter) would be more durable than a
> comment."
> -- Cycle 32 compound, "Least confident"

Accepted as-is. An import-graph linter is low priority for a solo-maintainer
project. The comment guardrail in results.py is sufficient until the team
grows.

## Decision: Park the project

All high-value work is blocked on API key renewal:

| Deferred Item | Blocked? | Value |
|---------------|----------|-------|
| A/B novelty validation | **Yes** (Tavily key is placeholder) | High |
| Diversity gate tuning | **Yes** (needs A/B data) | Medium |
| ModeInfo `__post_init__` | No | Low |
| Import-graph linter | No | Low |
| `converters.py` extraction | No (only if problems arise) | None yet |

The unblocked items (ModeInfo validation, import linter) are micro-tasks that
don't justify a full compound cycle. The project is at a natural pause after
completing the entropy roadmap (C27-C31) and its deferred hygiene (C32).

## Resume trigger

Renew the Tavily API key, then run Cycle 33 as:

1. Verify novelty decomposition with A/B test (`scripts/validate_cutoff_ab.py`)
2. Monitor SHORT_REPORT frequency (diversity gate interaction)
3. Tune thresholds if needed

The A/B methodology is established (Cycle 28 solution doc), the validation
script exists, and the diversity gate solution doc flags the exact risk to
watch (niche queries with few authoritative sources).

## Feed-Forward

- **Hardest decision:** Whether to invent busy work or park. Parking is the
  right call -- the entropy roadmap is done and the next meaningful work has
  a clear external blocker.
- **Rejected alternatives:** Running ModeInfo `__post_init__` validation as a
  micro-cycle (too small to justify the overhead), adding an import-graph
  linter (solves a theoretical problem, not an actual one).
- **Least confident:** Whether the Tavily key blocker will persist long enough
  that the novelty decomposition code goes stale. If more than 2 months pass,
  re-read the C30/C31 brainstorms before resuming.

## Three Questions

1. **Hardest decision in this session?** Accepting that parking is the right
   move. There's always pressure to "do something," but shipping low-value
   work wastes compound cycles.
2. **What did you reject, and why?** A micro-cycle for ModeInfo validation.
   It's 15 lines of code with no behavioral impact -- not worth brainstorm +
   plan + review overhead.
3. **Least confident about going into the next phase?** Context decay. When
   this project resumes, the developer will need to re-read C30-C32 solution
   docs to rebuild mental models of the diversity gate, novelty decomposition,
   and ANTHROPIC_ERRORS patterns.
