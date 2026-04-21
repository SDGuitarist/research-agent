# Appendix C: ContextProfile Evolution — Data Model & Migration Path

**Source:** context-evolution agent, 2026-04-21

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

## Evolution Path

### H1 (C29-31): Three Inline Fields

```yaml
preferred_sources:           # domains to boost during refinement
  - weddingwire.com
  - theknot.com
evidence_tier_overrides:     # per-topic minimum evidence tier
  pricing: documented
  exclusivity: documented
skeptic_focus:               # adversarial instructions (max 3, max 200 chars each)
  - "Verify claims about exclusive venue partnerships"
```

**Data model:** `preferred_sources: tuple[str, ...]`, `evidence_tier_overrides: tuple[tuple[str, str], ...]`, `skeptic_focus: tuple[str, ...]`

### H2 (C32-35): Two File-Path References

```yaml
knowledge_graph: memory/pfe.yaml     # persistent research memory (read/write)
source_config: sources/pfe.yaml      # data source definitions (read-only)
```

**Why file paths:** Knowledge graphs grow over time (mutable state). Source configs have per-source metadata (too structured for inline YAML). Same pattern as `gap_schema`.

### H3 (C36-39): One File-Path Reference

```yaml
swarm_roles: roles/pfe.yaml          # specialist agent definitions
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
    preferred_sources: tuple[str, ...] = ()
    evidence_tier_overrides: tuple[tuple[str, str], ...] = ()
    skeptic_focus: tuple[str, ...] = ()
    # H2: File-backed subsystems (C32-35)
    knowledge_graph: str = ""
    source_config: str = ""
    # H3: Swarm configuration (C36-39)
    swarm_roles: str = ""
```

**Final field count: 10.** All default to empty. Zero migration needed.

## Complexity Boundary

| Inline in ContextProfile | File-path reference |
|--------------------------|---------------------|
| Domain lists (blocked, extract, preferred) | Knowledge graphs (mutable, grows) |
| Simple string configs (tone, gap_schema path) | Source configs (structured per-source) |
| Short instruction lists (skeptic_focus, max 3) | Swarm role definitions (system prompts) |
| Topic-tier pairs (evidence_tier_overrides) | Anything exceeding ~500 chars per entry |

## Directory Layout After H2

```
contexts/   pfe.md, agm.md, venue-intel.md, general.md
memory/     pfe.yaml                    (knowledge graphs, read/write)
sources/    pfe.yaml                    (source configs, read-only)
gaps/       pfe.yaml                    (gap schemas, existing)
roles/      pfe.yaml                    (swarm roles, H3)
```
