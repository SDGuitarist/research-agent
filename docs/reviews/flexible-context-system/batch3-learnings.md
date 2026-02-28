# Learnings Research: Flexible Context System

**Researcher:** learnings-researcher
**Date:** 2026-02-28

## Relevant Past Solutions

### 1. Non-Idempotent Sanitization Double-Encoding (`security/non-idempotent-sanitization-double-encode.md`)
**CRITICAL match.** Session 2's double-sanitization fix in `_summarize_patterns()` exactly matches this documented pattern: "Sanitize once at data boundary; downstream assumes pre-sanitized."

### 2. Defensive YAML Frontmatter Parsing (`logic-errors/defensive-yaml-frontmatter-parsing.md`)
**IMPORTANT.** Establishes that every new data source needs its own sanitize-at-boundary call. Context loading refactors must verify sanitization boundaries.

### 3. Context Path Traversal Defense (`security/context-path-traversal-defense-and-sanitization.md`)
**CRITICAL match.** Covers sentinel elimination and auto-detect patterns. Session 2's removal of `DEFAULT_CONTEXT_PATH` aligns with Pattern 2: "Eliminate sentinel objects — pass content directly."

### 4. Conditional Prompt Templates (`logic-errors/conditional-prompt-templates-by-context.md`)
**IMPORTANT.** Validates Session 1's approach of parameterizing templates by context assumptions.

## Validation Checks Recommended

- Grep for other `critique_guidance` + `sanitize_content()` double-sanitization sites
- Verify no remaining domain-specific terms in prompt templates
- Test context auto-detect with `--context none`
