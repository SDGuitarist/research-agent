# Appendix C: ContextProfile Evolution — Data Model & Migration Path

**Source:** context-evolution agent, 2026-04-21
**Revised:** 2026-04-21 per Codex review (dropped preferred_sources, moved source_config to H3, added path governance)

## Current State

`ContextProfile` is a frozen dataclass with 4 fields, all with empty defaults:
- `blocked_domains: tuple[str, ...]`
- `extract_domains: tuple[str, ...]`
- `gap_schema: str`
- `synthesis_tone: str`

Consumed in 4 places inside `agent.py` plus `cli.py`. Parser uses per-field try/except (graceful degradation).

## Simplicity Constraints

1. **"5-minute context test":** If a field can't be understood in 5 minutes from a one-line YAML comment, it's too complex for inline. Complex behavior gets a file-path reference.
2. **"One-screen rule":** Frontmatter must fit in ~40 lines of terminal.
3. **"ls test":** `--list-contexts` summary must fit one line per context.

## Path Governance Rules

1. **One-hop only.** A context profile references auxiliary files directly. Auxiliary files must not reference further files (no chained references).
2. **Shared validation.** All file-path fields use the same two-layer defense from Cycle 24: character rejection (no `..`, no absolute paths, no null bytes) at parse time + `resolve()` + `is_relative_to(project_root)` containment at runtime.
3. **Read-only vs read/write.** `gap_schema`, `source_config`, `swarm_roles` are read-only — the engine never modifies them. `knowledge_store` is the only writable path.
4. **Writable path containment.** `knowledge_store` points to a directory (not a file) where the engine appends per-run JSON entries via `atomic_write()`. The directory must resolve inside the project root. The engine creates it if missing but never writes outside it. Per-context isolation (`knowledge_store: memory/pfe`) prevents cross-context data leakage.

## Evolution Path

### H1 (C29-31): Two Inline Fields

```yaml
evidence_tier_overrides:     # per-topic minimum evidence tier
  pricing: documented
  exclusivity: documented
skeptic_focus:               # adversarial instructions (max 3, max 200 chars each)
  - "Verify claims about exclusive venue partnerships"
```

**Data model:** `evidence_tier_overrides: tuple[tuple[str, str], ...]`, `skeptic_focus: tuple[str, ...]`

**Dropped: `preferred_sources`.** Cycle 24 explicitly rejected `preferred_domains` because +0.5 on int scores with int cutoff is a no-op (see `docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md`, Prior Phase Risk section). The same issue applies. If C29's score-aware refinement creates a real mechanism for source preference, the field can be added then with a defined behavioral effect.

### H2 (C32-35): Two Fields (one inline, one file-path)

```yaml
confidence_flag_threshold: 3  # flag claims at or below this confidence (default 2)
knowledge_store: memory/pfe   # directory for persistent research memory (read/write)
```

**`confidence_flag_threshold`** (inline, from C33): Simple integer, defaults to 2. PFE context might set it to 3 ("flag anything about pricing that's inferred, not documented"). Consumed by confidence extraction in `synthesize.py`.

**`knowledge_store`** (file-path, from C34): Points to a **directory** containing per-run JSON entry files (e.g., `memory/pfe/entry-2026-04-21T14-30.json`). This is the only writable path on ContextProfile. Read/write via `atomic_write()` for crash safety. Scoped per context to prevent cross-context leakage.

**Moved to H3: `source_config`.** No H2 cycle consumes it. Multi-source data fusion is C38 (H3).

### H3 (C36-39): Two File-Path References

```yaml
source_config: sources/pfe.yaml      # data source definitions (read-only, C38)
swarm_roles: roles/pfe.yaml          # specialist agent definitions (read-only, C39)
```

## Complete Data Model at H3

```python
@dataclass(frozen=True)
class ContextProfile:
    # Existing (H0)
    blocked_domains: tuple[str, ...] = ()
    extract_domains: tuple[str, ...] = ()
    gap_schema: str = ""
    synthesis_tone: str = ""
    # H1: Pipeline tuning (C29-31)
    evidence_tier_overrides: tuple[tuple[str, str], ...] = ()
    skeptic_focus: tuple[str, ...] = ()
    # H2: Confidence + memory (C32-35)
    confidence_flag_threshold: int = 2
    knowledge_store: str = ""         # directory path (read/write)
    # H3: Fusion + swarm (C36-39)
    source_config: str = ""           # file path (read-only)
    swarm_roles: str = ""             # file path (read-only)
```

**Final field count: 10** (4 existing + 2 H1 + 2 H2 + 2 H3). All default to empty/zero. Zero migration needed.

## Complexity Boundary

| Inline in ContextProfile | File-path reference |
|--------------------------|---------------------|
| Domain lists (blocked, extract) | Knowledge stores (writable directory of JSON entries) |
| Simple configs (tone, gap_schema path, threshold int) | Source configs (structured per-source metadata) |
| Short instruction lists (skeptic_focus, max 3) | Swarm role definitions (system prompts, strategies) |
| Topic-tier pairs (evidence_tier_overrides) | Anything exceeding ~500 chars per entry |

## Directory Layout After H2

```
contexts/   pfe.md, agm.md, venue-intel.md, general.md  (read-only)
memory/     pfe/                (knowledge store, read/write, C34)
gaps/       pfe.yaml            (gap schemas, read-only, existing)
```

## Directory Layout After H3

```
contexts/   pfe.md, agm.md, venue-intel.md, general.md  (read-only)
memory/     pfe/                (knowledge store, read/write)
gaps/       pfe.yaml            (gap schemas, read-only)
sources/    pfe.yaml            (source configs, read-only, C38)
roles/      pfe.yaml            (swarm roles, read-only, C39)
```
