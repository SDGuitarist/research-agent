# Brainstorm: Swappable Context Profiles (Cycle 24)

**Date:** 2026-03-06
**Status:** Complete
**Roadmap ref:** `docs/research/master-recommendations-future-cycles.md` Cycle 24

## What We're Building

Enrich the existing `contexts/` system with structured profile fields and better CLI discoverability. The infrastructure already exists (context files with YAML frontmatter, `--context <name>` flag, auto-detection, `ContextResult`/`ReportTemplate` dataclasses). This cycle adds:

1. **Source preferences** — `preferred_domains` (soft relevance boost) and `blocked_domains` (hard filter, never fetched)
2. **Gap schema path** — `gap_schema: gaps/pfe-gaps.yaml` linking a profile to its gap file
3. **Synthesis tone** — preset names (`executive`, `technical`, `casual`) or free-text custom instructions
4. **CLI discoverability** — `--list-contexts` flag showing available profiles with configured fields

No renaming of `--context` to `--profile`. No breaking changes.

## Why This Approach

The existing context system is 90% of a profile system already. Context files have YAML frontmatter with `name`, `template` (draft/final section structure), and `context_usage` instructions, plus a markdown body with business context. What's missing is structured fields that affect pipeline behavior beyond prompt content.

Adding fields to YAML frontmatter follows the established pattern — `_parse_template()` in `context.py` already extracts frontmatter. New fields layer on additively without changing downstream modules (the project's core architectural principle).

## Key Decisions

### 1. Keep `--context`, don't rename to `--profile`

**Why:** The MCP server also has a `context` parameter — renaming both would be a breaking change across two interfaces for zero functional benefit. "Context" already reads naturally (`--context pfe`). The value is in what's *inside* the files, not what the flag is called.

### 2. Blocked domains: hard filter

**Why:** Simple `if domain in blocked: skip` check. Predictable — if you block it, you never see it. Soft filtering would require threading into `relevance.py` scoring, creating a tuning problem with no clear right answer. If all results are blocked (unlikely), you just get fewer sources.

### 3. Preferred domains: soft relevance boost

**Why:** A small score bonus (e.g., +0.5 on the 1-5 relevance scale) nudges toward preferred sources without overriding the relevance gate. Keeps scoring honest — a terrible article from a preferred domain still gets filtered out.

### 4. Gap schema: path reference only

**Why:** Just store the path string. If the file doesn't exist at runtime, log a warning and proceed without gap awareness. No auto-creation, no templates. Users create gap files manually (they already know how — Cycles 17A-17D established the format).

### 5. Synthesis tone: presets + custom override

**Why:** Presets (`executive`, `technical`, `casual`) cover common cases with zero effort. Free-text `synthesis_tone` field allows full customization. If a preset name is given, expand it to its prompt text. If free-text is given, inject it directly. Both go through `sanitize_content()` for safety.

### 6. `--list-contexts` CLI flag

**Why:** The MCP server already has `list_contexts`. CLI users currently have to `ls contexts/` and read files manually. A `--list-contexts` flag shows name, description preview, and which optional fields are configured — matches the existing `--list` pattern for reports.

## Integration Points

Where new fields affect the pipeline:

| Field | Where it's consumed | How |
|-------|-------------------|-----|
| `blocked_domains` | `fetch.py` or `search.py` | Skip URLs matching blocked domains before fetching |
| `preferred_domains` | `relevance.py` | Add score bonus in `evaluate_sources()` |
| `gap_schema` | `agent.py` | Resolve path, pass to gap-aware pipeline stages |
| `synthesis_tone` | `synthesize.py` | Inject tone instruction into synthesis prompts |
| All fields | `context_result.py` | New fields on `ReportTemplate` or a sibling dataclass |

## Scope Boundaries

**In scope:**
- New YAML frontmatter fields parsed in `context.py`
- `blocked_domains` hard filter in fetch/search
- `preferred_domains` relevance boost
- `gap_schema` path resolution with warning on missing file
- `synthesis_tone` preset expansion + custom injection
- `--list-contexts` CLI flag
- Tests for all new fields and integration points
- Update `pfe.md` with example fields

**Out of scope:**
- Renaming `--context` to `--profile`
- Auto-creating gap schema files
- Soft/configurable domain blocking
- Profile inheritance or composition (e.g., base + override)
- Per-profile model routing

## Open Questions

*None — all resolved during brainstorm dialogue.*

## Example Profile (Target State)

```yaml
---
name: "Pacific Flow Entertainment"
gap_schema: "gaps/pfe-gaps.yaml"
synthesis_tone: "executive"
preferred_domains:
  - "billboard.com"
  - "musicbusinessworldwide.com"
  - "variety.com"
blocked_domains:
  - "tripadvisor.com"
  - "yelp.com"
template:
  draft:
    - "Market Overview": "Current state of the market..."
    - "Competitive Landscape": "Key competitors and positioning..."
  final:
    - "Executive Summary": "Key findings and recommendations..."
    - "Strategic Implications": "What this means for the business..."
  context_usage: "Use for analytical and recommendation sections. Keep factual analysis objective."
---

# Pacific Flow Entertainment — Research Context

[Business context markdown body...]
```

## Feed-Forward

- **Hardest decision:** Whether to rename `--context` to `--profile`. Decided against it — the rename would break two interfaces (CLI + MCP) for cosmetic benefit. The real value is in the YAML fields.
- **Rejected alternatives:** Soft domain filtering (too complex for the scoring pipeline), configurable block mode per-profile (YAGNI), preset-only tone without custom override (too restrictive).
- **Least confident:** How `preferred_domains` scoring boost integrates with `evaluate_sources()` — this function currently sends content to Haiku for scoring. The boost needs to happen post-LLM-scoring without distorting the gate decisions. Needs careful design in the plan phase.
