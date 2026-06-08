# AGENT_EPISODES.md — A Forensic Repository of Human↔AI Task Episodes

This file is a forensic, fact-checkable repository of real human↔AI collaboration episodes mined from the **research-agent** project (a Python CLI research agent for Pacific Flow Entertainment, built across ~33 compound-engineering cycles using both Claude Code and Codex). Five extraction agents independently mined the project's todos, review docs, fix batches, lessons, solution docs, git history, handoff notes, brainstorms, and plans for moments where an AI agent produced something a human (or a second AI reviewer) had to catch, steer, reject, or rebuild. Each episode below is a *de-duplicated, evidence-cited* account of one such incident, structured for use in a workshop on managing AI agents — so that each can be read as a teaching case with a concrete, reusable lesson.

---

## How to read this

Each canonical episode uses a fixed template. The fields are:

- **Friction-type** — one of F1–F6 (see taxonomy below). Where the source tiers disagreed on the tag, the best-fitting one is chosen and the alternative is noted in parentheses.
- **Source traces** — the union of every real citation (file:line, commit SHA, todo id, review doc) from every source tier that recorded this incident. Citations are never dropped, even when redundant.
- **Corroboration** — an integer 1–5: how many of the five independent source tiers (A1 todos, A2 reviews/fixes, A3 lessons/solutions, A4 git/handoff, A5 brainstorms/plans) recorded this same incident. Higher = stronger, independently-attested teaching evidence.
- **Cycle/arc**, **Date/source**, **Tool used**, **Project/topic**, **Original goal**, **Context provided**, **Files/tools used**, **Agent actions**, **What worked**, **What failed or caused friction**, **Human correction or steering**, **Final outcome**, **Reusable lesson**, **Workshop teaching opportunity** — as authored by the extractors, merged to keep the richest values.

### Friction taxonomy (F1–F6)

- **F1** — AI produced incorrect / hallucinated / unsafe output.
- **F2** — Vague/underspecified human input → bad output, fixed by prompt/spec refinement.
- **F3** — AI hit a wall / got stuck / indefinite deferral / loop.
- **F4** — Scope creep / over-engineering / wrong altitude (YAGNI).
- **F5** — Silent failure caught by a side-channel check (not by an error).
- **F6** — Other (consistency, duplication, architecture, process, reviewer disagreement, etc.).

### Authenticity conventions (non-negotiable)

- **`not clear`** — the source evidence did not determine this field. It is preserved verbatim, never invented into a fact.
- **`(inferred)`** — the extractor reconstructed this from the document's account rather than a primary record. Preserved as-is.
- **`(sources differ)`** — merging surfaced a genuine conflict between source tiers; both readings are kept rather than silently reconciled.
- **Tool attribution** is usually `not clear` per-incident: the project used **both Claude Code and Codex** (Codex as the external reviewer; nearly all commits carry a `Co-Authored-By: Claude Opus 4.5/4.6/4.8` trailer), but individual todos/docs rarely name which host tool ran a given review or wrote a given line. Codex is attributed only where a doc filename (`*-codex-*`) or body ("per review blocker", "Codex found") says so.

---

## Methodology & provenance

The five source tiers were mined from:

- **A1 — `todos/`** (147 review-todo markdown files): per-finding code-review records.
- **A2 — `docs/reviews/` and `docs/fixes/`**: multi-agent review summaries, fix batches, Codex↔Claude review dynamics.
- **A3 — `LESSONS_LEARNED.md`, `docs/lessons/`, `docs/solutions/`**: distilled retrospective lessons and solution docs.
- **A4 — git history (455 commits) + `HANDOFF.md`**: commit-level forensics. Note: the repo has **zero reverts** — corrections appear as forward `fix()` commits, so a "correction" is traced through later commits, not a revert.
- **A5 — `docs/brainstorms/`, `docs/plans/`, `RESEARCH_PLAN.md`**: upstream steering / spec-refinement friction during the brainstorm and plan phases.

**Excluded as episode sources:** `FAILURE_MODES_CATALOG.md` and `RESEARCH_PLAN.md` are treated as AI *deliverables* (artifacts the agent produced), not collaboration records — except where `RESEARCH_PLAN.md` itself documents an inception-stage architecture decision (one A5 episode). Several `docs/brainstorms/` files are research *outputs* about other projects (PF-Intel voice pipeline, expo-audio) and were excluded as not being steering docs for this project.

A small number of cross-project episodes (PF-Intel Supabase work, reviewed in the same compound-engineering loop) are retained where the extractor captured them, and labeled as cross-project.

---

## Index

| # | Canonical slug | Friction | Title | Corroboration | Cycle |
|---|----------------|----------|-------|:-------------:|-------|
| 1 | sanitize-non-idempotent-double-encode | F1 | Non-idempotent sanitization double-encodes ampersands, recurring across cycles | 5 | 18/20/24/27 (recurring) |
| 2 | ssrf-cascade-redirect-dns-bypass | F1 | SSRF defenses bypassed via cascade fallback, redirects, and independent DNS | 4 | 1, 9, 18, 03-11 |
| 3 | yaml-frontmatter-body-leak | F1 | Empty-body fallback leaks raw YAML frontmatter into prompts | 4 | 20/24 |
| 4 | bare-except-swallows-errors | F1 | Bare `except Exception` swallows real failures (and regresses) | 4 | 1, 3–4, 17, self-enhancing |
| 5 | bool-passes-isinstance-int | F1 | Python `bool` passes `isinstance(x, int)` at YAML/LLM boundaries | 4 | 18, p3-triage |
| 6 | context-path-traversal-and-symlink | F1 | `--context ../../etc/passwd` and symlinks escape the contexts/ boundary | 4 | 23, 24/25, 03-11 |
| 7 | temperature-task-misroute | F1 | One of 16 threaded call sites got the wrong temperature tier | 3 | 27 |
| 8 | second-order-prompt-injection | F1 | Attacker text round-trips through saved critique YAML into future prompts | 3 | self-enhancing |
| 9 | claude-has-no-clock-timestamp-collision | F1 | LLM-generated "microsecond" timestamps collide in parallel skill paths | 3 | 22 |
| 10 | url-unsanitized-in-prompt-xml | F1 | Untrusted URLs enter prompt XML outside the protected block | 2 | 03-11 / bg |
| 11 | lstrip-vs-removeprefix | F1 | `lstrip("# ")` strips characters, not the prefix | 1 | 16 |
| 12 | endswith-domain-substring-bypass | F1 | `host.endswith("yelp.com")` matches `evilyelp.com` | 1 | cascade |
| 13 | mcp-nonlocalhost-warn-not-fail | F1 | MCP server warned then bound to the network anyway | 3 | 19 |
| 14 | snippet-scored-like-full-content | F1 | 50-char snippets scored as high as full articles | 1 | 28 |
| 15 | single-pass-synthesis-unverified | F1 | No adversarial review of generated reports (hallucinations to user) | 1 | 16 |
| 16 | meaningful-words-rejects-valid-subqueries | F1 | Punctuation/hyphens silently dropped valid sub-queries | 1 | 27 |
| 17 | type-hint-lies | F1 | Type hint claims `str`/`dict[str,int]` but handles `None`/mixed | 1 | 18, 22 |
| 18 | nonetype-crash-missing-guard | F1 | Missing guard → runtime NoneType crash in `_update_gap_states` | 1 | 17 |
| 19 | dead-catch-narrow-httpx | F1 | Dead `except` subclass + too-narrow httpx transport catch | 1 | 17 |
| 20 | duplicated-valid-modes-set | F1 | Duplicated `_VALID_MODES` would silently reject new modes | 1 | 18 |
| 21 | symlink-race-atomic-write | F1 | Symlink TOCTOU on the atomic-write target | 1 | 17 |
| 22 | response-size-dos | F1 | DoS via unbounded `response.text` (size checked too late) | 1 | 18 |
| 23 | shell-injection-apostrophes | F1 | Apostrophes ("What's") break single-quoted skill shell command | 2 | 22 |
| 24 | stale-running-double-launch | F1 | Skill re-queues actively-running jobs (double API charge) | 1 | 22 |
| 25 | evidence-tier-regex-fragility | F1 | `[Critical Finding]` parser only coincidentally correct | 1 | 29 |
| 26 | self-enhancing-critique-injection-design | F1 | Designing against poisoned critique memory (brainstorm) | 1 | self-enhancing |
| 27 | committed-secrets-supabase | F1 | Service-role key + JWT secret committed to git (cross-project) | 1 | session-2 (PF-Intel) |
| 28 | cli-nargs-no-guard | F1 | `nargs="?"` let `python main.py` parse with `query=None` | 1 | 14 |
| 29 | walled-gardens-blind-spot | F1 | Walled-garden sources make reports contradict reality | 1 | 17+ |
| 30 | vague-query-no-gate | F2 | "stuff" burned API credits before any fail-fast gate | 2 | 27 |
| 31 | business-template-all-queries | F2 | Hardcoded business sections forced onto technical queries | 2 | 20/22/23 |
| 32 | skeptic-incorporate-vs-act | F2 | "Address this finding" produced vague compliance | 1 | 29 |
| 33 | mcp-input-normalization | F2 | LLM clients send `"null"`/`""` where they mean None | 1 | 19 |
| 34 | plan-public-api-test-gap | F2 | Plan widens public API but omits the test that polices it | 1 | 25 (plan) |
| 35 | plan-enforcement-gap | F2 | CI plan claims "prevents drift" but omits branch-protection | 1 | 26 (plan) |
| 36 | plan-install-ambiguity | F2 | Plan's verification commands assume uninstalled tooling | 1 | 26 (plan) |
| 37 | claudemd-stale-context | F2 | CLAUDE.md references a deleted file, misleading future sessions | 1 | flexible-context |
| 38 | mode-validation-boundary | F2 | No mode validation at the MCP trust boundary | 1 | 26 |
| 39 | abstention-gate-placement | F2 | Where to put a hallucination check: summarize vs synthesize | 1 | 30 (brainstorm) |
| 40 | novelty-prompt-wording-deferred | F2 | Study's "overlooked mechanisms" phrasing wrong for search queries | 1 | 31 |
| 41 | flexible-context-template-tension | F2 | Two of the agent's own decisions directly contradict | 1 | flexible-context |
| 42 | live-test-fetch-cascade | F2 | Compatibility matrix beat documentation for fallbacks | 1 | 9 |
| 43 | interactive-prompt-in-agent-context | F2 | Skill blocks on a human prompt in automated runs | 1 | 22 |
| 44 | vague-query-heuristic-vs-llm | F2 | Defining "vague" without burning an API call (brainstorm) | 1 | 27 |
| 45 | mcp-cost-critique-parity-deferred | F3 | MCP cost/critique parity + lint deferred ~5 cycles | 5 | 19→31 |
| 46 | batch-size-symptom-chasing | F3 | Four tuning commits chase 429s before the root cause | 2 | 10–11 |
| 47 | novelty-diversity-gate-unverified | F3 | Heuristic shipped behind invariants; live A/B blocked on API key | 1 | 28–32 |
| 48 | anthropic-errors-deferred-adopt | F3 | Shared exception constant defined but unused for 2 cycles | 1 | 32 (def. 29H) |
| 49 | auto-compact-mid-cycle | F3 | Auto-compaction silently degrades multi-step work | 1 | workflow |
| 50 | query-iteration-differentiation-risk | F3 | Forcing a feature to prove it isn't redundant | 1 | 20 (brainstorm) |
| 51 | cycle33-park-not-busywork | F3 | Choosing to stop rather than invent low-value work | 1 | 33 (brainstorm) |
| 52 | over-flagged-dead-code-rejected | F4 | Human rejects "remove 270 LOC of dead code" (roadmap scaffolding) | 1 | 17 (then 18) |
| 53 | ddg-yagni-fallback | F4 | 300-line provider abstraction cut to ~50 lines | 1 | 7 |
| 54 | preferred-domains-yagni-noop | F4 | Plan kills a brainstorm feature that was arithmetically a no-op | 1 | 24 (plan) |
| 55 | fixed-sleep-rate-limit | F4 | Unconditional inter-batch sleeps wasted 6–9s/run | 1 | 17 |
| 56 | over-engineered-spend-json | F4 | daily_spend.json over-engineered (7 fields → 3) | 1 | 22 |
| 57 | memory-blowup-full-file-read | F4 | Context preview read entire files into memory | 1 | 23 |
| 58 | research-plan-approach-b-not-c | F4 | Inception plan picks the moderate architecture over the impressive | 1 | origin |
| 59 | mcp-coarse-four-tools | F4 | Fewer coarse MCP tools beat granular pipeline exposure | 1 | 19 (brainstorm) |
| 60 | query-iteration-one-pass-no-loop | F4 | Capping an iterative feature so it can't spiral | 1 | 20 (brainstorm) |
| 61 | tiered-routing-tier1-only | F4 | Resisting the bigger cost-savings tier without data | 1 | 21 (brainstorm) |
| 62 | self-enhancing-tier-scope | F4 | Capping an ambitious self-improving agent at safe tiers | 1 | self-enhancing |
| 63 | p3-triage-skip-fstring-churn | F4 | Refusing a "correct" lint fix because it's churn | 1 | p3-triage |
| 64 | p2-triage-remove-query-domain | F4 | Deleting dead machinery instead of refactoring it | 1 | 23 |
| 65 | cycle25-bundle-trivial-housekeeping | F4 | Bundling sub-20-line items to avoid loop overhead | 1 | 25 |
| 66 | cycle32-config-py-new-file | F4 | A new file because every existing home is semantically wrong | 1 | 32 |
| 67 | ten-steps-ahead-merge-not-pivot | F4 | Folding a grand vision into the existing roadmap | 1 | strategic |
| 68 | diversity-gate-pure-count | F4 | Refusing the reputation-list slippery slope | 1 | 30 (brainstorm) |
| 69 | snippet-tier-field-placement | F4 | Put the field where it's consumed, not where it's "complete" | 1 | 28 (brainstorm) |
| 70 | quick-mode-retry-guard | F4 | Quick mode triggers the expensive coverage retry | 1 | 28 |
| 71 | private-attr-public-api | F4 | Public API reached into underscore-prefixed internals | 2 | 23/25 |
| 72 | debug-log-noise | F4 | 7 identical debug logs of a frozen value | 1 | 31 |
| 73 | background-research-approach-a | F4 | Choosing the simplest of three architectures for delivery | 1 | bg-research |
| 74 | temperature-three-not-four-fields | F4 | YAGNI on a fourth temperature knob | 1 | 27 (brainstorm) |
| 75 | retry-rescores-existing | F5 | Coverage retry re-scored already-scored sources | 3 | 18 |
| 76 | tavily-built-not-active | F5 | Tavily built but silently fell back to DuckDuckGo for cycles | 2 | 8+ |
| 77 | failed-context-silent-drop | F5 | FAILED context load silently treated as "no context" | 2 | bg / 25 |
| 78 | replace-all-corrupts-test-names | F5 | `replace_all` on a substring silently drops tests | 1 | 12 |
| 79 | auto-save-test-asserts-nothing | F5 | Auto-save test patches the writer but never asserts it | 2 | 19, 26 |
| 80 | nonatomic-cli-write-marks-complete | F5 | Non-atomic CLI write lets a corrupt report be marked Completed | 2 | bg / 25 |
| 81 | self-critique-invisible | F5 | Self-critique works but is invisible to CLI/agent consumers | 1 | self-enhancing |
| 82 | error-message-info-leakage | F5 | Sensitive info leaks via error text / partial path redaction | 1 | 22, 26 |
| 83 | mcp-critique-not-saved | F5 | MCP critique returns data but never persists (broken feedback loop) | 2 | 31 |
| 84 | test-helper-accidental-compliance | F5 | Diversity-gate test passed by luck of the fixtures | 1 | 30 |
| 85 | ci-only-proves-listtools | F5 | Required CI check proves less than the dependency range claims | 1 | 26 |
| 86 | context-cache-shared-state | F5 | Module-level context cache: no thread safety / test pollution | 2 | bg / 25 / 29H |
| 87 | mock-data-triggers-quality-gate | F5 | New quality gate silently broke six existing tests | 1 | 29 |
| 88 | context-profile-funnel-leak | F5 | Blocked domains leaked into `refine_query` before the funnel | 1 | 24 |
| 89 | schema-erd-not-enforced | F5 | ERD promised constraints the SQL migration didn't enforce (cross-project) | 1 | PF-Intel V1 |
| 90 | insufficient-data-unsanitized | F5 | Fallback "insufficient data" response skipped sanitization | 1 | 6 |
| 91 | injection-regression-test-missing | F5 | Sanitization fix shipped without a regression test | 1 | 27 |
| 92 | rls-blocks-backend | F5 | RLS gates on auth.uid() but the AI pipeline has no JWT (cross-project) | 1 | session-2 |
| 93 | fastmcp-version-cap-walkback | F6 | FastMCP cap widened, then re-tightened on review (add→lose→re-find) | 3 | 19, 26 |
| 94 | stateful-agent-leaks-between-runs | F6 | Per-run state leaks across reused agent (recurring) | 2 | 17→25 |
| 95 | source-vs-chunk-relevance | F6 | Scoring chunks but deciding on sources | 1 | 15 |
| 96 | temporal-coupling-instance-state | F6 | Mutable instance state read in wrong order → fragility | 1 | 17 |
| 97 | duplication-cleanup-cluster | F6 | DRY cleanups: budget pruning, disclaimers, test helpers, query validation | 1 | 17, 25 |
| 98 | duplicate-tavily-cache | F6 | Two Tavily client caches drift apart | 1 | 18 |
| 99 | async-blocking-in-event-loop | F6 | Sync file I/O and API calls block the event loop | 1 | self-enhancing, 18 |
| 100 | model-string-scatter | F6 | Same model string defined in 4 modules | 1 | 17 |
| 101 | none-conflation-status-modeling | F6 | `None`/boolean overloads hide "ran but empty" and "failed" | 1 | 17, 20 |
| 102 | print-in-library-code | F6 | CLI-first design printed and discarded all pipeline metadata | 1 | planned |
| 103 | codebase-hygiene-audit | F6 | 6-agent audit found 14 P2s + 1 real bug during dedup | 1 | 29H |
| 104 | stale-section-references | F6 | Magic "Section 11" / stale PFE strings after renumbering | 1 | 20/24 |
| 105 | frozen-mutable-dict / inconsistent-frozen | F6 | Frozen dataclass with a mutable dict; 5 dataclasses non-frozen | 1 | 17/18 |
| 106 | cross-agent-consensus-severity | F6 | Cross-agent consensus and synthesis as a severity signal | 1 | 2nd review |
| 107 | codex-records-negative-findings | F6 | Codex declines to elevate overstated prior claims | 1 | 03-11 |
| 108 | reviewer-false-positives-rejected | F6 | Fresh-context reviewer re-litigates settled decisions | 1 | 32 |
| 109 | reviewer-severity-reconciliation | F6 | Synthesizer downgrades specialist "critical" gaps | 1 | 19, p3-do-now |
| 110 | reviewer-disagreement-developer-call | F6 | Two agents disagree (trigram/TEXT/imports) → developer decides | 1 | session-2, 17 |
| 111 | process-no-plan-document | F6 | Work phase started with no plan + oversized commits | 1 | self-enhancing |
| 112 | f-string-logging-recurs | F6 | f-string vs lazy logging recurs every cycle (automate it) | 1 | 17→31 |
| 113 | magic-number-thresholds | F6 | Inline magic thresholds vs named constants (per new module) | 1 | 18→30 |
| 114 | type-hint-precision-cluster | F6 | Type-annotation precision findings (high-volume) | 1 | 17–22 |
| 115 | agent-native-parity-cluster | F6 | New config/feature ships dev-visible but agent-invisible | 1 | 25→31 |
| 116 | auto-detect-new-feature-checklist | F6 | One new LLM feature, four friction types at once | 1 | 25 |
| 117 | new-llm-output-sanitize | F6 | LLM-output headings re-entering prompts (injection laundering) | 1 | 30 |
| 118 | iteration-timeout-and-status | F6 | No global iteration timeout; overloaded "skipped" status | 1 | 30 |
| 119 | token-cost-caps | F6 | Oversending draft input; unbounded mini-report output | 1 | 30 |
| 120 | skill-guards-are-prose-not-code | F6 | Shell-escaping/budget guards are LLM prose, not enforced code | 1 | bg-research |
| 121 | inline-imports-tradeoff | F6 | Deferred imports: move to top-level or document the tradeoff | 1 | 17 |
| 122 | input-validation-side-commands | F6 | Unvalidated subprocess target + budget value | 1 | 18, 22 |
| 123 | self-finding-became-wrong | F6 | A "dead code" finding was already false by fix time | 1 | self-enhancing |
| 124 | substring-bypass-lint-script | F6 | Lint `name not in instructions` false-positives on short names | 1 | 26 |
| 125 | ci-workflow-hardening | F6 | First CI workflow ships with security/perf gaps | 1 | 26 |
| 126 | unauth-http-transport | F6 | MCP HTTP transport has zero auth (open proxy) | 2 | 19, 26 |
| 127 | retry-query-char-validation | F6 | LLM retry queries lack character-class validation (low, self-rated) | 1 | 28/29 |
| 128 | tiered-model-routing-ab | F6 | A/B model swap measured against a hidden validation bug | 1 | 21 |
| 129 | no-transaction-wrapper | F6 | Migration not wrapped in a transaction (cross-project) | 1 | session-2 |
| 130 | validation-questions-between-sessions | F6 | "What test would catch it?" feeds the next session | 1 | 18 |
| 131 | dependency-pinning-loose | F6 | Loose `>=`-only dependency constraints, no lockfile | 1 | 18, 26 |

## Episodes by friction type

### F1 — AI produced incorrect / hallucinated / unsafe output

---

#### 1. sanitize-non-idempotent-double-encode — Non-idempotent sanitization double-encodes ampersands, recurring across cycles
- **Friction-type:** F1 (security + data-integrity; tagged F5 "silent corruption" in some tiers)
- **Source traces:** A1 `todos/024-complete-p2-sanitize-missing-ampersand.md:14`, `todos/019-complete-p3-sanitize-double-call.md:14`, `todos/041-p2-sanitize-contract-docs.md:14-21`, `todos/065-done-p1-double-sanitization-ampersand.md:14`; A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:23-30,276`, `docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md:24`, `docs/reviews/flexible-context-system/REVIEW-SUMMARY.md:28-30`, `docs/reviews/2026-03-06-cycle-24-codex-findings.md:33-39` (tone double-sanitize), `synthesize.py:132,441`, `decompose.py:141`, `relevance.py:122`, `context.py:121,405`, `synthesize.py:59`; A3 `docs/solutions/security/non-idempotent-sanitization-double-encode.md:14-106`, `docs/solutions/architecture/iterative-review-second-pass-patterns.md:63-115,238-246`, `synthesize.py:413,497`; A4 commits `fa4daaf`, `58425a1`, `60a185a`, `5060e63`; A5 `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md:117-161`
- **Corroboration:** 5
- **Cycle/arc:** Multiple — Cycles 18, 20, 24, 27 (recurring); idempotency landed in 27
- **Date/source:** see Source traces; solution doc dated 2026-02-23, idempotency commit `5060e63`
- **Tool used:** not clear (multiple Claude Code sub-agents: security-sentinel, performance-oracle, data-integrity-guardian; Codex caught the cycle-24 tone instance)
- **Project/topic:** Shared `sanitize_content()` prompt-injection defense boundary
- **Original goal:** Defend prompts against injection by escaping untrusted content, sanitizing once per the "shared sanitization single-source-of-truth" convention.
- **Context provided:** A documented solution doc existed and was referenced repeatedly; `sanitize(sanitize(x)) == sanitize(x)` idempotency invariant; pre-sanitization contracts noted in commit bodies.
- **Files/tools used:** `sanitize.py`, `synthesize.py`, `decompose.py`, `relevance.py`, `context.py`
- **Agent actions:** Across at least four review rounds, agents found `sanitize_content()` applied at multiple consumers, producing `&amp;amp;` (`& → &amp; → &amp;amp;`); `AT&T`, `R&D`, `R&amp;amp;D` corrupted in reports. In background-research it was upgraded P2→P1 once non-idempotence was recognized as *active data corruption*, not redundant work. Flexible-context review found "the PR fixed the **third** pass but two remain."
- **What worked:** Eventually made `sanitize_content()` itself idempotent via `html.unescape()` before escaping (commit `5060e63`); 13 idempotency invariant tests added. The cycle-27 brainstorm first *falsified the roadmap's own wrong suggestion* — `html.escape("&amp;")` → `"&amp;amp;"`, so the naive fix didn't work; unescape-then-escape was chosen instead.
- **What failed or caused friction:** Despite a written solution doc, the bug class kept being reintroduced because each new consumer re-sanitized already-sanitized input. "Defense in depth by re-running a non-idempotent transform" is itself corruption. A documented boundary (`load_context()`) existed only in docs — the code (`load_full_context()`) returned raw content and 4 consumers each sanitized (sources differ on exactly which sites: A3 cites `synthesize.py:413,497`, A2 cites `:132,441`).
- **Human correction or steering:** Standardize on sanitize-once-at-the-boundary; remove per-consumer calls; finally demand idempotency rather than spot-fixes; treat an upstream doc's recommended fix as a hypothesis to falsify.
- **Final outcome:** Idempotent sanitizer eliminates the recurrence class; single-boundary enforcement; contract comments added.
- **Reusable lesson:** A defect that recurs across cycles signals a missing invariant. A documented solution doc does not stop a bug class from recurring — the durable fix is to make the operation idempotent and/or enforce a single boundary, not to keep catching instances in review.
- **Workshop teaching opportunity:** The premier case study in the whole corpus: institutional memory ("we have a doc for that") vs. recurring defects, and why "sanitize twice to be safe" is actively harmful. Also a clean demo of an AI falsifying a confident-but-wrong handoff suggestion before coding.

---

#### 2. ssrf-cascade-redirect-dns-bypass — SSRF defenses bypassed via cascade fallback, redirects, and independent DNS
- **Friction-type:** F1 (security: SSRF; some hops tagged F5 "silent leak")
- **Source traces:** A1 `todos/022-complete-ssrf-redirect-bypass.md:14`, `todos/023-complete-dns-rebinding-toctou.md:14`, `todos/025-complete-cascade-bypasses-ssrf.md:14`, `todos/026-complete-no-http-response-size-limit.md:14`; A2 `docs/reviews/2026-03-11-codex-security-review.md:109-127`, `cascade.py:42-66,88-105`, `fetch.py:114-203,260-275`; A3 `docs/solutions/security/ssrf-bypass-via-proxy-services.md:16-121`, `docs/lessons/operations.md:14-34`, `LESSONS_LEARNED.md:9`; A4 commits `e5aa008`, `f2efd83` (early hardening)
- **Corroboration:** 4
- **Cycle/arc:** Cycle 1 (first build), Cycle 9 (cascade added), Cycle 18 (fetch/cascade pass), security review 2026-03-11
- **Date/source:** solution doc 2026-02-13; Codex review 2026-03-11
- **Tool used:** not clear (Security sentinel sub-agent); Codex for the 2026-03-11 cascade DNS finding
- **Project/topic:** Fetch SSRF protection and the cascade fallback (Jina Reader / Tavily Extract)
- **Original goal:** Block fetches to private IPs / internal resources; recover failed fetches via third-party extractors.
- **Context provided:** `fetch.py` validated URLs via `_is_safe_url()`; `cascade.py` added later as a fallback; Codex compared the cascade path to the stronger direct-fetch SSRF path.
- **Files/tools used:** `fetch.py`, `cascade.py`, `extract.py`
- **Agent actions:** Multiple distinct bypasses found: (a) `follow_redirects=True` lets a validated URL redirect to `http://169.254.169.254/...` (t022); (b) httpx re-resolves DNS on connect, enabling low-TTL rebinding (t023); (c) SSRF-blocked URLs land in `failed_urls` → `cascade_recover()` → forwarded to `r.jina.ai` (t025); (d) unbounded `response.text` read before the size check → OOM DoS (t026); (e) cascade's `_is_internal_url()` checks scheme/blocked-hosts/literal-IPs but does NOT DNS-resolve, so a public hostname resolving private gets forwarded to Jina/Tavily (Codex RA-SEC-004).
- **What worked:** Time-of-check/time-of-use reasoning; following the failure path not just the happy path; Codex noticing the asymmetry between two paths that should share a validator.
- **What failed or caused friction:** "Validate the URL once" is insufficient when redirects are followed and the HTTP client resolves DNS separately. A "fallback" was an independent fetch path skipping the gate — "No symptoms — silent bypass." The robust validation existed in `fetch.py` but wasn't reused in `cascade.py`.
- **Human correction or steering:** Validate every hop; reuse the SSRF-safe hostname validation before forwarding to fallback providers; stream-and-cap untrusted bytes; test hostnames that resolve private, not just literal private IPs.
- **Final outcome:** Hardening implemented across hops (some todos `ready`/`complete`); solution doc marked "Planned" for parts (sources differ on completion state).
- **Reusable lesson:** Every new code path touching external URLs inherits the same threat model; a strong check on one path is undermined by a weaker sibling. Security gates must govern fallback/recovery paths, or they just reroute the risk. "Advisory verification is no verification."
- **Workshop teaching opportunity:** The cloud-metadata endpoint (169.254.169.254) as the canonical SSRF demo; "fallback features quietly bypass primary-path safeguards" as a recurring agent-built-feature failure mode.

---

#### 3. yaml-frontmatter-body-leak — Empty-body fallback leaks raw YAML frontmatter into prompts
- **Friction-type:** F1 (logic error: template syntax injected as "context content")
- **Source traces:** A1 `todos/075-done-p1-body-fallback-leaks-yaml.md:14`, `todos/076-done-p1-yaml-delimiter-edge-case.md:14`; A2 `docs/reviews/template-per-context/REVIEW-SUMMARY.md:38-39,18-23`; A3 `docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md:33-95`; A4 commits `47aba21`, `1a2a6b3`, `6e0712a`, `6572949`
- **Corroboration:** 4
- **Cycle/arc:** Cycle 20 / ~23–24 (template feature)
- **Date/source:** solution doc 2026-02-27; commit `47aba21`
- **Tool used:** not clear (A2: kieran-python-reviewer sub-agent)
- **Project/topic:** YAML frontmatter context-template parser (`context.py:_parse_template()`)
- **Original goal:** Split YAML frontmatter from body content; parse a context file into body + template.
- **Context provided:** Additive template subsystem; rare edge cases (frontmatter-only file, `---` inside a value); 748 tests passing.
- **Files/tools used:** `research_agent/context.py`, `synthesize.py`, `__init__.py`, tests
- **Agent actions:** `body if body else raw` fallback returned the entire raw file (delimiters and all) as report content when a file was all-frontmatter; delimiter search `find("---", 3)` mis-split on `---` inside YAML values.
- **What worked:** Return `body` (empty is valid); search `\n---` (line-anchored). kieran-python found two parser logic bugs (P1s) the passing suite didn't cover.
- **What failed or caused friction:** A convenience fallback dumped structural metadata into the LLM prompt; embedded `---` produced malformed splits; high test count didn't guarantee edge-case coverage.
- **Human correction or steering:** Fix the body-fallback; harden delimiter handling line-aware; both treated as P1 blockers.
- **Final outcome:** Parsing hardened; combined behavior of fixes 075+079 documented as an edge case.
- **Reusable lesson:** Never fall back to raw input on empty parse output; match delimiters line-aware, not substring-wide. "Fall back to the whole file" is dangerous when the file contains structure the consumer (LLM) shouldn't see.
- **Workshop teaching opportunity:** A "defensive fallback" that actively corrupts output — over-helpful error handling as its own bug class, and why high test counts don't guarantee edge-case coverage.

---

#### 4. bare-except-swallows-errors — Bare `except Exception` swallows real failures (and regresses)
- **Friction-type:** F1 (silent error swallowing; tagged F5 in A1)
- **Source traces:** A1 `todos/001-complete-p1-bare-except-exception.md:14,18-20,63,67`; A2 `docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md:11-16`, `batch3-git-history.md:16-20`, `agent.py:155`; A3 `docs/solutions/logic-errors/dead-catch-and-narrow-httpx-exceptions.md:26-128`, `docs/lessons/operations.md:14-34`, `LESSONS_LEARNED.md:9`; A4 commits `e5aa008`, `f2efd83` (early), and the `ac4e7ae` fix referenced by the regression
- **Corroboration:** 4
- **Cycle/arc:** Cycle 1, Cycles 3–4, Cycle 17, Self-Enhancing Agent (regression)
- **Date/source:** see traces; convention "Never bare `except Exception`" codified in CLAUDE.md from the early hardening
- **Tool used:** not clear (8/9 Claude Code sub-agents flagged the regression; git-history-analyzer tied it to `ac4e7ae`)
- **Project/topic:** Exception handling across `token_budget.py`, `fetch.py`, critique error handling
- **Original goal:** Run pipeline stages without crashing while not swallowing real bugs.
- **Context provided:** Project convention "Never bare `except Exception`"; git history shows the exact pattern fixed earlier in `ac4e7ae`.
- **Files/tools used:** `token_budget.py:28`, `agent.py:155`, `fetch.py`, `summarize.py`, `synthesize.py`
- **Agent actions:** Original `except Exception:` "silently swallows configuration errors, auth failures, and network issues" and catches `MemoryError`/`SystemExit`. Later `except (CritiqueError, Exception) as e:` re-introduced the anti-pattern (CritiqueError redundant) — a *regression* of `ac4e7ae`, flagged by 8/9 agents.
- **What worked:** Multiple reviewers converged; precise replacement provided (narrow to specific exceptions + DEBUG log). The first build's hardening pass also removed an insecure `--api-key` CLI flag, capped fetch concurrency, and reused a pooled `AsyncClient`.
- **What failed or caused friction:** Broad catches hide auth/config failures that never surface as errors; the implementing agent re-introduced a documented, previously-fixed anti-pattern because the convention lived only in prose.
- **Human correction or steering:** Narrow to specific exceptions; add a separate `except Exception: logger.exception(...)` net only if needed; convention codified in CLAUDE.md.
- **Final outcome:** Anti-pattern fixed and re-fixed; convention established early and enforced.
- **Reusable lesson:** First-draft AI code reliably needs an exception-handling and secret-handling pass; anti-patterns recur when the convention lives only in prose — a git-history-aware reviewer that recognizes "we fixed this exact thing before" is uniquely valuable.
- **Workshop teaching opportunity:** Side-channel detection of a swallowed-error class, plus "the model regressed a past fix" and how history-aware review catches it.

---

#### 5. bool-passes-isinstance-int — Python `bool` passes `isinstance(x, int)` at YAML/LLM boundaries
- **Friction-type:** F1 (unsafe/incorrect validation — type confusion)
- **Source traces:** A2 `docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md:40-44`, `batch3-data-integrity.md:10-14`, `schema.py:94`; A3 `docs/solutions/logic-errors/python-bool-is-int-yaml-validation.md:14-69,111-112`, `schema.py:94`, `context.py:153`; A4 commit `58425a1`; A5 `docs/brainstorms/2026-02-23-p3-triage-brainstorm.md:51-55`
- **Corroboration:** 4
- **Cycle/arc:** Cycle 18 review; p3-triage
- **Date/source:** solution doc 2026-02-25; brainstorm 2026-02-23
- **Tool used:** not clear (data-integrity-guardian review agent caught the schema.py instance)
- **Project/topic:** Gap-schema and critique-YAML integer field validation (`priority`, dimension scores)
- **Original goal:** Validate that YAML fields like `priority` and scores are integers.
- **Context provided:** YAML files authored by user or LLM feed these fields; `isinstance(True, int)` is `True` in Python.
- **Files/tools used:** `schema.py:94`, `context.py:153`, `tests/test_context.py`, `tests/test_schema.py`
- **Agent actions:** Validation used `if not isinstance(priority, int)`. `priority: true` (YAML bool) passed because `bool` subclasses `int`; `true`→1, `false`→0 silently accepted. The triage brainstorm caught it buried as a "P3" and reclassified it as a real bug; the fix in context.py was then found to need the same guard in schema.py.
- **What worked:** Guard `isinstance(x, bool)` *before* the int check; rule scoped to *data-deserialization boundaries only* (not typed function params).
- **What failed or caused friction:** A type check gave false confidence; the original fix patched one site while the same quirk lived in a second validator (latent: `False` fails range anyway, `True` is the live risk).
- **Human correction or steering:** "Fix — it's a real bug"; add the bool guard at every YAML/JSON/LLM-output boundary; grep for siblings.
- **Final outcome:** Both sites guarded.
- **Reusable lesson:** At YAML/JSON/LLM-output boundaries, precede every `isinstance(x, int)` with an `isinstance(x, bool)` reject; when you fix a language-quirk bug, fix the whole class, not one instance.
- **Workshop teaching opportunity:** A portable language gotcha that defeats validation; "re-read low-priority findings on their merits"; and review-after-fix finding a second copy.

---

#### 6. context-path-traversal-and-symlink — `--context ../../etc/passwd` and symlinks escape the contexts/ boundary
- **Friction-type:** F1 (security: path traversal → prompt injection of file contents)
- **Source traces:** A1 `todos/054-done-p1-path-traversal-resolve-context.md:103-108`, `todos/064-done-p1-valueerror-uncaught-context-cli-api.md:14`, `todos/071-pending-p2-path-traversal-is-relative-to.md:14`; A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:16-22`, `docs/reviews/2026-03-11-codex-security-review.md:50-76`, `cli.py:311-318`, `__init__.py:99-102`, `context.py:229-244,318-329,392-405`; A3 `docs/solutions/security/context-path-traversal-defense-and-sanitization.md:19-59,192-201`; A4 commits `3d747ac`, `998290d`
- **Corroboration:** 4
- **Cycle/arc:** Cycle ~23, 24/25 (context feature), security review 2026-03-11
- **Date/source:** solution doc 2026-02-26; Codex review 2026-03-11
- **Tool used:** not clear (security-sentinel flagged P1); Codex reproduced the symlink bypass
- **Project/topic:** `resolve_context_path()` / `load_full_context()` in `context.py`
- **Original goal:** Load a named context file from `contexts/`; keep loading inside the operator-controlled directory.
- **Context provided:** `python3 main.py --standard "test" --context ../CLAUDE` reads `CLAUDE.md` and injects its contents into LLM prompts (PoC); Codex reproduced a symlinked `contexts/leak.md` bypass in a temp workspace.
- **Files/tools used:** `research_agent/context.py`, `cli.py`, `__init__.py`, `agent.py`, `mcp_server.py`
- **Agent actions:** Accepted traversal context names; `Path("a") / "/b"` returns `Path("/b")` (Python footgun); string-prefix containment used; symlinks resolving outside `contexts/` were previewed and fully loaded. The security fix then *raised* a `ValueError` that neither CLI nor public API caught → raw traceback (t064).
- **What worked:** Two-layer defense (character rejection + post-resolve containment); `Path.is_relative_to()` over string prefix; catch `(FileNotFoundError, ValueError)` and convert to `ResearchError`; resolved-path containment that *rejects* symlinks instead of following them.
- **What failed or caused friction:** Trusted user input + a `Path("__no_context__")` sentinel forced state mutation breaking agent reuse; string-level validation didn't protect against symlinks; a security check that raises wasn't paired with a handler.
- **Human correction or steering:** Validate containment (not just existence); ship a PoC to make severity undeniable; reject symlinked targets; audit every caller when a fix adds a new raise.
- **Final outcome:** Defense-in-depth path validation; sentinel eliminated; async made reentrant; symlink containment added.
- **Reusable lesson:** Path joins with user input require explicit containment checks; never validate containment with string prefixes; a security check that raises must be paired with a handler; resolution must reject, not follow, symlinks.
- **Workshop teaching opportunity:** Bundles path safety, magic sentinels, async self-mutation, "secure but crashing," and "reproduction beats inspection." Note the duplicate issue_id "054" reused for two unrelated P1s — a real tracking-hygiene defect worth showing.

---

#### 7. temperature-task-misroute — One of 16 threaded call sites got the wrong temperature tier
- **Friction-type:** F1 (incorrect output — wrong generation control)
- **Source traces:** A1 `todos/127-done-p2-insufficient-data-temperature-misroute.md:14-16`; A2 `docs/reviews/2026-04-05-cycle-27-review-summary.md:19,30-33,58`; A4 commit `da2a19c`; MEMORY.md "temperature misclassification on generate_insufficient_data_response"
- **Corroboration:** 3
- **Cycle/arc:** Cycle 27
- **Date/source:** commit `da2a19c`; review 2026-04-05
- **Tool used:** not clear (A2: kieran-python-reviewer)
- **Project/topic:** Per-task temperature threading (planning 0.2 / summarize 0.5 / synthesis 0.8) across 16 call sites
- **Original goal:** Route each task to its correct temperature tier.
- **Context provided:** `generate_insufficient_data_response` produces ~200-word prose but was "genuinely ambiguous" and initially tagged as classification (0.2).
- **Files/tools used:** `synthesize.py`, `modes.py`, `agent.py:846`, MCP standalone tools
- **Agent actions:** Classified 16 sites by task type and mis-tagged the prose generator as classification; "A temperature of 0.2 will make these responses dry and formulaic." (MCP standalone tools also defaulted to 1.0 — see episode 129.)
- **What worked:** Reclassify by output *format*, not by whether the call makes a logical decision; a per-site audit caught the misroute.
- **What failed or caused friction:** Mass-threading a parameter through many sites invites one-off misclassification on the ambiguous edge case; tests didn't assert the tier.
- **Human correction or steering:** 1-line fix to align the site; corrected rule recorded ("Classify by output format, not logical decision").
- **Final outcome:** All 16 sites correctly tagged.
- **Reusable lesson:** When applying a rule across many sites, the ambiguous edge case is where the AI errs — review the leaves, not just the source; temperature is a per-task decision.
- **Workshop teaching opportunity:** Mechanical fan-out tasks still hide one subtle misclassification.

---

#### 8. second-order-prompt-injection — Attacker text round-trips through saved critique YAML into future prompts
- **Friction-type:** F1 (security: multi-hop / persisted injection chain)
- **Source traces:** A2 `docs/reviews/self-enhancing-agent/batch2-security.md:22-26`, `REVIEW-SUMMARY.md:70-74`, `context.py:218-219`; A3 `docs/solutions/architecture/self-enhancing-agent-review-patterns.md:110-123,234-237`, `critique.py`, `context.py`; A5 `docs/brainstorms/2026-02-20-self-enhancing-agent-brainstorm.md:191-211,257-258`
- **Corroboration:** 3
- **Cycle/arc:** Self-Enhancing Agent (9-agent review)
- **Date/source:** solution doc 2026-02-23; brainstorm 2026-02-20
- **Tool used:** Claude Code sub-agent (security-sentinel); 9-agent review
- **Project/topic:** Self-critique feedback loop (critiques saved to YAML, loaded in future runs)
- **Original goal:** Improve future runs from past critiques.
- **Context provided:** Write path truncated to 200 chars but the read path trusted stored data; "the boundary between 'structured score' and 'free-text suggestion' is where the attack surface lives."
- **Files/tools used:** `critique.py`, `context.py:218-219`
- **Agent actions:** Trust chain: attacker web content → Claude writes a malicious "weakness" string → saved to YAML → loaded next run → injected into prompts (mitigated only by 200-char truncation). The brainstorm pre-emptively named the vector and specified mitigations.
- **What worked:** Sanitize each weakness string at *load* (use) time, not just write time; never store raw web content; summarize patterns instead of pasting verbatim; schema-validate on load.
- **What failed or caused friction:** Stored model output is treated as trusted on re-load though it derived from untrusted web content; the chain crosses three boundaries, hard to see from one module.
- **Human correction or steering:** Apply `sanitize_content()` to each weakness string before templating; "Summarize patterns, never paste raw critique text."
- **Final outcome:** Sanitize-at-use applied; pattern summaries over verbatim quotes; max 200 chars.
- **Reusable lesson:** Model output that gets persisted and re-fed becomes untrusted input on the next hop; a self-learning loop's memory is an injection surface — sanitize and summarize before re-injecting.
- **Workshop teaching opportunity:** "Your agent's notes can attack your agent" — persistent/agentic memory as an injection vector.

---

#### 9. claude-has-no-clock-timestamp-collision — LLM-generated "microsecond" timestamps collide in parallel skill paths
- **Friction-type:** F1 (AI limitation: model can't produce real time/randomness → collision)
- **Source traces:** A1 `todos/055-complete-p1-timestamp-collision-parallel.md:124`, `.claude/skills/research-queue.md:82-86`; A3 `docs/solutions/architecture/skill-only-features-background-research.md:68-98,182-188`; A4 commits `f2efd83` (microsecond ts), `92d2978` (atomic_write)
- **Corroboration:** 3
- **Cycle/arc:** Cycle 22 (research-queue parallel skill); atomic-write later
- **Date/source:** solution doc 2026-02-26
- **Tool used:** Claude Code skills (6-agent review)
- **Project/topic:** `/research:queue` background agents generating unique output paths
- **Original goal:** Avoid overwriting reports across parallel queries.
- **Context provided:** "Claude generates all paths in a single message — it has no real clock"; real test data confirmed two queries got identical timestamps (`005243522271`).
- **Files/tools used:** `.claude/skills/research-queue.md`, `research-digest.md`, `main.py`, `safe_io.py`
- **Agent actions:** Used microsecond timestamps for uniqueness; parallel queries got identical values (collision avoided only by luck). Related: second-resolution timestamps elsewhere risked collision; direct writes risked torn files.
- **What worked:** Deterministic batch index (1,2,3) for uniqueness; `atomic_write` (tempfile + rename); `'\''` escaping for apostrophes (see episode 23).
- **What failed or caused friction:** Asking an LLM to "use a microsecond timestamp" yields a plausible-but-fake constant.
- **Human correction or steering:** Generate real-world facts (time, randomness, IDs) in code, not the model; both P1s fixed in one commit.
- **Final outcome:** Deterministic IDs + atomic, collision-free persistence.
- **Reusable lesson:** Never delegate real-world facts to the model — Claude has no clock between values in one pass; use a counter and generate in code.
- **Workshop teaching opportunity:** A crisp demonstration of an LLM hallucinating a deterministic-looking value, and a non-obvious property of the agent runtime (no time progression in one inference pass).

---

#### 10. url-unsanitized-in-prompt-xml — Untrusted URLs enter prompt XML outside the protected block
- **Friction-type:** F1 (unsafe output — prompt-injection surface)
- **Source traces:** A2 `docs/reviews/2026-03-11-codex-security-review.md:29-48`, `docs/reviews/background-research-agents/batch2-security.md:40-44`, `summarize.py:87-115`, `synthesize.py:753-756`, `test_summarize.py:178-200`, `test_synthesize.py:72-87`
- **Corroboration:** 2 (A2 records both the Feb Claude-side P3 and the March Codex elevation)
- **Cycle/arc:** Background Research Agents (Feb 2026) → Security review 2026-03-11
- **Date/source:** Codex review 2026-03-11 (RA-SEC-001 Medium)
- **Tool used:** Codex (March); Claude Code security-sentinel (February)
- **Project/topic:** Prompt construction in summarize/synthesize
- **Original goal:** Insert source metadata (title, url, body) into LLM prompts safely.
- **Context provided:** Full security review ran `938 passed`; the system prompt's ignore-instructions rule is scoped only to `<webpage_content>`.
- **Files/tools used:** `summarize.py`, `synthesize.py`, tests
- **Agent actions:** `summarize_chunk()` and `_build_sources_context()` sanitize `chunk`/`title`/`summary` but insert raw `url` into `<webpage_metadata>`/`<url>` — outside the protected block.
- **What worked:** Codex tied the gap to the system-prompt's defense scope.
- **What failed or caused friction:** The exact same issue had been filed P3/cosmetic by a Claude sub-agent weeks earlier and not fixed.
- **Human correction or steering:** Sanitize all untrusted URL strings before prompt insertion; add regression tests with XML-like delimiters in URLs.
- **Final outcome:** RA-SEC-001 Medium, #1 in fix order; Claude Code fix handoff written.
- **Reusable lesson:** A finding deferred as "low" by one reviewer can be the top issue for another with a sharper threat model; re-run security review with fresh eyes before shipping.
- **Workshop teaching opportunity:** Cross-tool compounding — severity is a function of the reviewer's threat model.

---

#### 11. lstrip-vs-removeprefix — `lstrip("# ")` strips characters, not the prefix
- **Friction-type:** F1 (incorrect AI output — buggy code produced)
- **Source traces:** A3 `docs/solutions/logic-errors/adversarial-verification-pipeline.md:89-98`, `LESSONS_LEARNED.md:23`, `docs/lessons/patterns-index.md:95`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 16
- **Date/source:** dated 2026-02-11
- **Tool used:** not clear (Claude Code and Codex both used)
- **Project/topic:** Heading/section-title parsing in context slicing (`context.py`)
- **Original goal:** Strip the `"## "` markdown prefix from section headings.
- **Context provided:** Multi-pass synthesis refactor introducing stage-appropriate slicing.
- **Files/tools used:** `research_agent/context.py`, `synthesize.py`
- **Agent actions:** Used `line.lstrip("# ")` to remove the heading marker.
- **What worked:** `removeprefix("## ")` correctly removes the literal prefix.
- **What failed or caused friction:** `lstrip("# ")` strips any leading chars in the set `{'#',' '}`, eating characters that belong to the heading text. Silent — no error, just corrupted text.
- **Human correction or steering:** Replaced with `removeprefix`; added to the code-review checklist. (inferred: discovered while building the pipeline.)
- **Final outcome:** Bug fixed.
- **Reusable lesson:** `str.lstrip(chars)` removes a *set of characters*, not a prefix string. Use `str.removeprefix()` for fixed prefixes.
- **Workshop teaching opportunity:** A classic "plausible-looking but wrong" stdlib call — you must know the exact semantics of API calls the agent emits, and such bugs are silent.

---

#### 12. endswith-domain-substring-bypass — `host.endswith("yelp.com")` matches `evilyelp.com`
- **Friction-type:** F1 (security: substring domain bypass)
- **Source traces:** A3 `docs/solutions/security/domain-matching-substring-bypass.md:16-69` (commit `dffbbb1`)
- **Corroboration:** 1 (but cross-referenced later by A1 `todos/122` for the lint-script analogue — see episode 124)
- **Cycle/arc:** Code review (cascade)
- **Date/source:** 2026-02-15, commit `dffbbb1`
- **Tool used:** discovered during code review
- **Project/topic:** Domain-specific handling in cascade (e.g., Yelp)
- **Original goal:** Apply special parsing to known domains.
- **Context provided:** "No runtime symptoms."
- **Files/tools used:** `cascade.py`
- **Agent actions:** Used bare `endswith("yelp.com")` — a substring match.
- **What worked:** `host == domain or host.endswith(f".{domain}")` (dot-boundary).
- **What failed or caused friction:** Attacker domains like `evilyelp.com` would receive the trusted code path.
- **Human correction or steering:** Applied to every `endswith` domain check.
- **Final outcome:** Boundary-aware matching everywhere.
- **Reusable lesson:** Never use bare `endswith` for domain identity; flag it in review.
- **Workshop teaching opportunity:** A one-line security bug that recurs across cookies/CORS/certs — pattern recognition for reviewers; later transferred to catch a lint-script bug (compounding knowledge).

---

#### 13. mcp-nonlocalhost-warn-not-fail — MCP server warned then bound to the network anyway
- **Friction-type:** F1 (security: unauthenticated network exposure of API keys); tagged F5 "advisory check that doesn't block" in A4
- **Source traces:** A2 `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md:46-47`, `docs/fixes/cycle-19-mcp-server/batch1.md:14-18,34`; A3 `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md:48-90`; A4 commit `6ca586c`
- **Corroboration:** 3
- **Cycle/arc:** Cycle 19 (MCP Server)
- **Date/source:** solution doc 2026-02-28; commit `6ca586c`
- **Tool used:** Claude Code sub-agent (security-sentinel)
- **Project/topic:** MCP server HTTP transport / network binding
- **Original goal:** Expose the research pipeline over MCP without exposing API keys to the network.
- **Context provided:** Trust model shifted from "local user" to "untrusted LLM client over HTTP"; FastMCP HTTP has no auth hook.
- **Files/tools used:** `research_agent/mcp_server.py`, `agent.py`, `tests/test_mcp_server.py`
- **Agent actions:** Non-loopback `MCP_HOST` only logged a warning then started; allowed set missed `::1`; error-handler path-stripping regex only matched `/Users/|/home/`.
- **What worked:** Hard `sys.exit()` on non-loopback bind (Option C) chosen over bearer-token auth (no FastMCP middleware hook → would need monkey-patch/fork, over-engineering for a local tool); `::1` allowed; broadened path regex with URL-preserving negative lookbehind; regression test.
- **What failed or caused friction:** Any network process could invoke all tools and read `ANTHROPIC_API_KEY`/`TAVILY_API_KEY`; `/opt`,`/var`,`/tmp` paths leaked. "Warn then proceed" is not a safeguard.
- **Human correction or steering:** Fail closed; eliminate the attack surface (localhost-only) rather than build auth machinery.
- **Final outcome:** Fail-closed binding + parity checklist; one `except Exception` survived as a documented open risk.
- **Reusable lesson:** When a tool's transport changes (CLI→HTTP), re-audit the *whole* trust model; fail closed, don't warn-and-continue. When you can't add the "proper" control cheaply, eliminating the attack surface can be the right-sized fix.
- **Workshop teaching opportunity:** Choosing the proportionate security control for the actual threat model vs. gold-plating with token auth.

---

#### 14. snippet-scored-like-full-content — 50-char snippets scored as high as full articles
- **Friction-type:** F1 (incorrect scoring — quality signal ignored)
- **Source traces:** A3 `docs/solutions/feature-implementation/relevance-source-quality-gates.md:14-83`; A1 `todos/051`, `todos/043` context (cutoff era); `extract.py`, `cascade.py`, `summarize.py`, `relevance.py`, `modes.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 28
- **Date/source:** 2026-04-05; 7-agent review
- **Tool used:** not clear
- **Project/topic:** Relevance / source-quality gates
- **Original goal:** Keep only high-quality sources.
- **Context provided:** Cascade snippets (50–200 chars) scored 4–5 on topical relevance, ignoring depth; the only marker was a text prefix the LLM ignored; cutoff was 3.
- **Files/tools used:** `extract.py`, `cascade.py`, `summarize.py`, `relevance.py`, `modes.py`
- **Agent actions:** Snippets structurally identical to full extractions scored high.
- **What worked:** `SourceTier` literal set at the cascade (point of knowledge); `SNIPPET_SCORE_CAP=3` before every return; raise cutoff to 4 (standard/deep) → snippets auto-excluded.
- **What failed or caused friction:** Surviving sources lacked XML boundaries (review caught a defense-in-depth gap); live A/B blocked by expired key.
- **Human correction or steering:** All P2s fixed; layered cap/cutoff interaction documented with tests.
- **Reusable lesson:** LLM relevance scoring conflates "on topic" with "substantive" — encode the distinction structurally at the point of creation, not in prose the model ignores; cap low-evidence sources before the gate.
- **Workshop teaching opportunity:** Why structural quality signals beat instructions the model can ignore.

---

#### 15. single-pass-synthesis-unverified — No adversarial review of generated reports
- **Friction-type:** F1 (hallucination/unsupported claims surfacing in output)
- **Source traces:** A3 `docs/solutions/logic-errors/adversarial-verification-pipeline.md:16-92`; `agent.py`, `synthesize.py`, `skeptic.py`, `context.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 16
- **Date/source:** 2026-02-11
- **Tool used:** not clear
- **Project/topic:** Report synthesis
- **Original goal:** Produce trustworthy reports.
- **Context provided:** `synthesize_report()` was one LLM call; the first challenger of claims was the human user.
- **Files/tools used:** `agent.py`, `synthesize.py`, `skeptic.py`, `context.py`
- **Agent actions:** Single-pass synthesis mixed inferences with observations; framing/timing never challenged; unsupported claims propagated straight to the user.
- **What worked:** Draft→Skeptic→Final pipeline; skeptic tags claims SUPPORTED/INFERRED/UNSUPPORTED; deep mode runs 3 cumulative agents.
- **What failed or caused friction:** Architectural rebuild (385 tests, +1711/-481 lines).
- **Human correction or steering:** Multi-pass made default; quick mode stays single-pass.
- **Final outcome:** Adversarial verification shipped.
- **Reusable lesson:** Separate generation from evaluation — an adversarial reviewer sees the author's blind spots.
- **Workshop teaching opportunity:** Core agent-management lesson: a second adversarial pass catches what the generator never will.

---

#### 16. meaningful-words-rejects-valid-subqueries — Punctuation/hyphens silently dropped valid sub-queries
- **Friction-type:** F1 (incorrect output — valid input silently rejected)
- **Source traces:** A4 commit `55e314b`; `query_validation.py`, `decompose.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 27
- **Date/source:** commit `55e314b`
- **Tool used:** Claude (Opus 4.6 trailer)
- **Project/topic:** Query validation / decomposition vague-query gate
- **Original goal:** Validate sub-queries have enough meaningful words.
- **Context provided:** Concrete failing example in the commit body.
- **Files/tools used:** `query_validation.py`, `decompose.py`
- **Agent actions:** The validator compared raw tokens, so `"standards,"` != `"standards"` and `"post-quantum"` != `"quantum"` — silently rejecting good sub-queries like "Post-quantum cryptography threat assessment timeline."
- **What worked:** Strip punctuation and split hyphens in `meaningful_words()`; added decomposition debug logs.
- **What failed or caused friction:** The C27 vague-query feature "degraded decomposition quality on complex queries by dropping valid sub-queries" — a new guard over-rejected.
- **Human correction or steering:** (inferred) Caught after C27 shipped; HANDOFF flagged the new constraint.
- **Final outcome:** Punctuation/hyphen normalization restored valid sub-queries.
- **Reusable lesson:** Input-gating features need real-world token examples; naive string equality on natural language silently drops valid data — a safety guard that's too aggressive is itself a defect.
- **Workshop teaching opportunity:** False positives in validation are invisible failures.

---

#### 17. type-hint-lies — Type hint claims `str`/`dict[str,int]` but handles `None`/mixed values
- **Friction-type:** F1 (annotation contradicts runtime behavior — misleads tooling); F6 for the mixed-type variant
- **Source traces:** A1 `todos/044-done-p1-parse-gap-response-type-hint.md:14`, `todos/087-done-p2-from-parsed-type-hint.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18, ~22
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `_parse_gap_response(text: str)` handles `None`; `CritiqueResult.from_parsed(parsed: dict[str, int])` receives mixed int/str
- **Original goal:** Make hints match runtime reality.
- **Context provided:** A test `test_none_returns_safe_default` confirms `None` handling; the dict has 5 int scores + str `weaknesses`/`suggestions`.
- **Files/tools used:** decompose/gap parsing module, critique result module
- **Agent actions:** Cross-referenced the existing test against the signature; traced producer (`_parse_critique_response`) vs consumer.
- **What worked:** Use a test as proof the hint is wrong; producer/consumer trace.
- **What failed or caused friction:** A "lying" hint suppresses real mypy errors; latent false-alarm trap if type-checking is ever enabled.
- **Human correction or steering:** Fix to `str | None` / `dict[str, int | str]`.
- **Final outcome:** done.
- **Reusable lesson:** A hint contradicted by a passing test is a p1, not cosmetic — it actively misdirects static analysis. "Works at runtime" doesn't excuse a wrong hint if you plan to enable type checking.
- **Workshop teaching opportunity:** Distinguishes "missing hint" (p3) from "wrong hint" (p1).

---

#### 18. nonetype-crash-missing-guard — Missing guard → runtime NoneType crash
- **Friction-type:** F1 (latent incorrect/unsafe runtime behavior)
- **Source traces:** A1 `todos/003-complete-p1-nonetype-crash-update-gap-states.md:14`; A3 `docs/solutions/architecture/gap-aware-research-loop.md:24-101` (one of 3 P1s)
- **Corroboration:** 1 (the gap-loop solution doc records it among the cycle-17 P1 cluster)
- **Cycle/arc:** Cycle 17
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `agent.py:92` `_update_gap_states`
- **Original goal:** Guard `_current_research_batch`, which "can be `None` if `_update_gap_states` is called before the gap check runs."
- **Context provided:** The guard on line 89 only checks `schema_result`, not `_current_research_batch`.
- **Files/tools used:** `research_agent/agent.py`
- **Agent actions:** Identified the missing branch via order-of-call reasoning.
- **What worked:** Temporal reasoning exposed a crash path.
- **What failed or caused friction:** Temporal coupling — order-dependent state (see episode 96).
- **Human correction or steering:** Accepted — runtime crash if called before gap check.
- **Final outcome:** complete.
- **Reusable lesson:** Guards must cover every nullable they depend on, not just the obvious one.
- **Workshop teaching opportunity:** Pairs with temporal-coupling to show how order-dependent state breeds crash paths.

---

#### 19. dead-catch-narrow-httpx — Dead `except` subclass + too-narrow httpx transport catch
- **Friction-type:** F1 (incorrect exception handling — dead code + uncaught errors)
- **Source traces:** A3 `docs/solutions/logic-errors/dead-catch-and-narrow-httpx-exceptions.md:26-128` (commit `5cb8a3d`); `synthesize.py:235,338,553`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17
- **Date/source:** 2026-02-15, commit `5cb8a3d`
- **Tool used:** not clear (found during code review)
- **Project/topic:** Synthesis API error handling
- **Original goal:** Catch Anthropic SDK + httpx transport errors during streaming synthesis.
- **Context provided:** Same pattern copy-pasted at 3 sites.
- **Files/tools used:** `research_agent/synthesize.py`
- **Agent actions:** Listed `APIConnectionError` in a final `except` after `except APIError` (subclass → unreachable); caught only `httpx.ReadError`/`RemoteProtocolError`, missing other transport errors during stream iteration.
- **What worked:** Remove the dead subclass; catch the parent `httpx.TransportError`.
- **What failed or caused friction:** Unreachable clause + transport errors (`CloseError`, `WriteError`) could escape unhandled during streaming.
- **Human correction or steering:** Review found it; 527 tests pass.
- **Final outcome:** Clean handling at all 3 sites.
- **Reusable lesson:** Verify exception inheritance before adding a catch; catch transport parent classes; audit copy-pasted error handling across sites.
- **Workshop teaching opportunity:** Reading the SDK's exception hierarchy rather than guessing.

---

#### 20. duplicated-valid-modes-set — Duplicated `_VALID_MODES` would silently reject new modes
- **Friction-type:** F1 (duplicated knowledge → silent validation failure)
- **Source traces:** A3 `docs/solutions/architecture/pip-installable-package-and-public-api.md:83-103`; `__init__.py`, `modes.py`, `results.py`, `cli.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18
- **Date/source:** 2026-02-15
- **Tool used:** review caught it as P1
- **Project/topic:** Pip-installable public API mode validation
- **Original goal:** Validate the `mode` string in public `run_research()`.
- **Context provided:** Plan specified a `_VALID_MODES` frozenset in `__init__.py`, duplicating `ResearchMode.from_name()`.
- **Files/tools used:** `__init__.py`, `modes.py`, `results.py`, `cli.py`
- **Agent actions:** Hardcoded a second copy of the valid-mode set.
- **What worked:** Delegate to `ResearchMode.from_name()` and translate `ValueError` → `ResearchError`.
- **What failed or caused friction:** Adding a new mode to `modes.py` would silently fail validation in `__init__.py`.
- **Human correction or steering:** Review P1; single source of truth.
- **Final outcome:** Single source of truth for mode validation.
- **Reusable lesson:** When module A validates data module B owns, delegate to B and translate the exception.
- **Workshop teaching opportunity:** Duplicated "valid value" sets are a classic silent-divergence bug.

---

#### 21. symlink-race-atomic-write — Symlink TOCTOU on the atomic-write target
- **Friction-type:** F1 (security: unsafe filesystem write path)
- **Source traces:** A1 `todos/012-complete-p2-symlink-race-safe-io.md:14`; A2 `docs/reviews/2026-03-11-codex-security-review.md:78-105` (reports/ base-dir symlink variant), `report_store.py:35-40`, `safe_io.py:28-31`
- **Corroboration:** 1 (A2's reports/ symlink finding is a sibling, cross-referenced)
- **Cycle/arc:** Cycle 17; reports/ variant in 2026-03-11 review
- **Date/source:** see traces
- **Tool used:** not clear (Security sentinel; Codex for reports/ variant)
- **Project/topic:** `safe_io.py:28-40` `atomic_write`; `os.rename` follows symlinks
- **Original goal:** Validate the target isn't a symlink so writes can't be redirected.
- **Context provided:** "if a symlink is created at the target location, writes could be redirected." Codex later found `atomic_write()` only rejects a symlink at the final leaf path while a symlinked base dir is accepted (anchors to `REPORTS_DIR.resolve()`).
- **Files/tools used:** `research_agent/safe_io.py`, `report_store.py`, `mcp_server.py`, `context.py`, `agent.py`
- **Agent actions:** Flagged the symlink-follow gap; Codex distinguished leaf-symlink checks (present) from base-dir checks (absent).
- **What worked:** Reject symlinks; treat the literal `reports/`/`reports/meta/` directories as containment roots.
- **What failed or caused friction:** "atomic" ≠ "safe against symlink swap"; `Path.resolve()` *follows* symlinks instead of rejecting them.
- **Human correction or steering:** Compare against the *literal* intended root, not the resolved target.
- **Final outcome:** complete / RA-SEC-003 Medium.
- **Reusable lesson:** Atomicity and symlink-safety are independent properties; `Path.resolve()` is the wrong tool for containment because it silently follows symlinks.
- **Workshop teaching opportunity:** Subtle API misuse — `resolve()` feels safe but defeats the boundary it's meant to enforce.

---

#### 22. response-size-dos — DoS via unbounded `response.text`
- **Friction-type:** F1 (security/DoS: OOM from unbounded download)
- **Source traces:** A1 `todos/026-complete-no-http-response-size-limit.md:14`, `cascade.py:136`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18
- **Date/source:** see traces
- **Tool used:** not clear (Security sentinel)
- **Project/topic:** `fetch.py:_fetch_single()` reads whole response; size check is post-download
- **Original goal:** Cap download size before buffering (extract.py's 5MB check is too late).
- **Context provided:** "A malicious server could send a multi-gigabyte response causing OOM."
- **Files/tools used:** `fetch.py`, `cascade.py:136`
- **Agent actions:** Noted the check happens AFTER download.
- **What worked:** Ordering analysis (check-after-buffer).
- **What failed or caused friction:** Late validation can't prevent the harm it checks for.
- **Human correction or steering:** (inferred) accepted; implemented as part of SSRF hardening (episode 2).
- **Final outcome:** ready / (inferred) implemented.
- **Reusable lesson:** Stream-and-cap; never buffer untrusted bytes fully before size-checking.
- **Workshop teaching opportunity:** "Check too late" ordering bugs.

---

#### 23. shell-injection-apostrophes — Apostrophes break single-quoted skill shell command
- **Friction-type:** F1 (security: shell injection in a skill-generated command)
- **Source traces:** A1 `todos/054-complete-p1-shell-injection-apostrophes.md:80-85`, `.claude/skills/research-queue.md:98-99`; A3 `docs/solutions/architecture/skill-only-features-background-research.md:68-98` (escaping fix)
- **Corroboration:** 2
- **Cycle/arc:** Cycle 22 (research-queue skill)
- **Date/source:** see traces
- **Tool used:** not clear (the issue is in a Claude Code skill)
- **Project/topic:** `python3 main.py --{mode} '{query}'` with user query in single quotes
- **Original goal:** Stop queries like `What's the best async library?` breaking quote context; "A crafted query could execute arbitrary shell commands."
- **Context provided:** Common English apostrophes ("What's", "don't") break single quotes; ~30% of natural queries would break.
- **Files/tools used:** `.claude/skills/research-queue.md:98-99`
- **Agent actions:** Showed the everyday-input exploit, not just an exotic one — a functional bug as well as security.
- **What worked:** Reviewing the *skill prompt* as attackable code; `'\''` escaping.
- **What failed or caused friction:** The AI-authored skill itself shipped an injection vector.
- **Human correction or steering:** Accepted (p1).
- **Final outcome:** complete.
- **Reusable lesson:** AI-generated automation glue (skills, shell templates) needs the same security review as app code; shell-escape user text in skill-built commands.
- **Workshop teaching opportunity:** The agent's own tooling was the vulnerability — meta-lesson on reviewing agent scaffolding.

---

#### 24. stale-running-double-launch — Skill re-queues actively-running jobs
- **Friction-type:** F1 (incorrect state handling → double-launch / double-charge)
- **Source traces:** A1 `todos/058-complete-p2-stale-running-detection.md:14`, `.claude/skills/research-queue.md:48-52`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 22
- **Date/source:** see traces
- **Tool used:** not clear (skill logic)
- **Project/topic:** research-queue Step 2 unconditionally moves `## Running` → `## Queued`
- **Original goal:** Distinguish dead sessions from active ones to avoid "double-launches and double budget charges."
- **Context provided:** Running `/research:queue` while agents are active re-queues live work.
- **Files/tools used:** `.claude/skills/research-queue.md:48-52`
- **Agent actions:** Spotted an unconditional state reset that ignores liveness.
- **What worked:** Reasoned about concurrent invocations.
- **What failed or caused friction:** "Reset everything on start" assumes single-flight.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Queue/state machines must check liveness before reclaiming in-flight items.
- **Workshop teaching opportunity:** Real money at stake (double API charges) from a naive state reset.

---

#### 25. evidence-tier-regex-fragility — `[Critical Finding]` parser only coincidentally correct
- **Friction-type:** F1 (fragile/uncertain AI parsing)
- **Source traces:** A4 commit `6ee4972`, HANDOFF history; `skeptic.py`, `synthesize.py`; related A3 `docs/solutions/feature-implementation/skeptic-enforcement-quality-gates-evidence-tiers.md`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 29
- **Date/source:** commit `6ee4972`
- **Tool used:** Claude (Opus trailers)
- **Project/topic:** Skeptic critical-finding extraction (`skeptic.py`)
- **Original goal:** Extract `[Critical Finding]` markers and enforce a three-way contract (remove / mark [Disputed] / cite evidence).
- **Context provided:** Plan risk #1 "fragile parsing"; review findings.
- **Files/tools used:** `skeptic.py`, `synthesize.py`
- **Agent actions:** Built `_CRITICAL_FINDING_RE` for bold/em-dash/`[Evidence][Critical Finding]` variants; added real-format regression tests; strengthened wording from vague "refute or incorporate" to three concrete actions.
- **What worked:** Regression tests on real output formats; concrete enforcement options.
- **What failed or caused friction:** The reviewer noted matching `[Evidence][Critical Finding]` is "coincidental correctness, not intentional design"; LLMs could emit `[Critical finding:]` or unbracketed variants that miss.
- **Human correction or steering:** Plan/review named fragile parsing as the top risk and demanded real-format tests before accepting.
- **Final outcome:** Tests pin current behavior; residual risk documented.
- **Reusable lesson:** Parsing LLM output with regex is inherently fragile — pin it with real-output regression tests and document the gap.
- **Workshop teaching opportunity:** "Coincidental correctness" — code that passes tests but works for the wrong reason.

---

#### 26. self-enhancing-critique-injection-design — Designing against poisoned critique memory
- **Friction-type:** F1 (designing against unsafe/poisoned AI input)
- **Source traces:** A5 `docs/brainstorms/2026-02-20-self-enhancing-agent-brainstorm.md:191-211,257-258`
- **Corroboration:** 1 (distinct from episode 8: this is the *upstream design-phase* steering that anticipated the vector; episode 8 is the review/fix of the shipped instance)
- **Cycle/arc:** future cycle (self-enhancing agent)
- **Date/source:** 2026-02-20
- **Tool used:** not clear
- **Project/topic:** Storing critique history and re-injecting it into future prompts
- **Original goal:** Feed past critiques back into decompose/relevance prompts.
- **Context provided:** MemoryGraft-style memory-poisoning research; "the boundary between 'structured score' and 'free-text suggestion' is where the attack surface lives."
- **Agent actions:** Specified: never store raw web content in YAML, sanitize all fields, summarize patterns rather than paste verbatim weakness text, schema-validate on load.
- **What worked:** Treating the agent's own memory as an untrusted input channel during design.
- **What failed or caused friction:** A naive feedback loop would pipe sanitized-once web content back into prompts verbatim, re-opening injection.
- **Human correction or steering:** "Summarize patterns, never paste raw critique text."
- **Final outcome:** Structured-scores + short sanitized text (max 200 chars).
- **Reusable lesson:** A self-learning loop's memory is an injection surface; sanitize and summarize before re-injecting — designed in, not retrofitted.
- **Workshop teaching opportunity:** Security thinking for agent memory at the brainstorm stage.

---

#### 27. committed-secrets-supabase — Service-role key + JWT secret committed to git (cross-project)
- **Friction-type:** F1 (AI committed live secrets — unsafe output)
- **Source traces:** A2 `docs/reviews/session-2-supabase/REVIEW-SUMMARY.md:10-16,254-256`, `pf-intel/server/.env`
- **Corroboration:** 1
- **Cycle/arc:** Session 2 (Supabase) — cross-project (PF-Intel)
- **Date/source:** commit `67490b7`
- **Tool used:** Claude Code sub-agent (security-sentinel)
- **Project/topic:** PF-Intel Supabase schema/auth/storage
- **Original goal:** Set up Supabase backend.
- **Context provided:** 9-agent review.
- **Files/tools used:** `pf-intel/server/.env`
- **Agent actions:** Committed Supabase URL, anon key, service_role key, and JWT secret; service_role bypasses all RLS, JWT secret allows forging auth tokens.
- **What worked:** security-sentinel made this the top P1 with a concrete remediation sequence.
- **What failed or caused friction:** Secrets that bypass all access control placed in version control.
- **Human correction or steering:** Rotate all secrets, `git rm --cached`, `.gitignore`, consider `git filter-repo`, add `.env.example`.
- **Final outcome:** P1 "do immediately."
- **Reusable lesson:** Committed secrets aren't fixed by deleting the file — rotate and purge history because the exposure already happened.
- **Workshop teaching opportunity:** Secret-handling hygiene and the "delete isn't enough" remediation chain.

---

#### 28. cli-nargs-no-guard — `nargs="?"` let `python main.py` parse with `query=None`
- **Friction-type:** F1 (incorrect: missing validation guard)
- **Source traces:** A3 `docs/solutions/feature-implementation/cli-quality-of-life-improvements.md:88-103`, `LESSONS_LEARNED.md:21`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 14
- **Date/source:** 2026-02-10
- **Tool used:** not clear
- **Project/topic:** CLI flags (`--cost`, `--list`)
- **Original goal:** Make `query` optional so `--list`/`--cost` work without it.
- **Context provided:** Adding `nargs="?"` made bare invocation silently pass parsing.
- **Files/tools used:** `main.py`, `modes.py`, `agent.py`
- **Agent actions:** Made `query` optional without a downstream guard, so `query=None` would flow into research.
- **What worked:** Priority-ordered flag checks then an explicit `if args.query is None` guard; cost values moved into the dataclass; dual-regex for backward-compatible filename parsing; 28 new tests.
- **What failed or caused friction:** Silent `None` query.
- **Human correction or steering:** Guard + checklist added.
- **Final outcome:** Robust CLI.
- **Reusable lesson:** `nargs="?"` always needs an explicit validation guard; config values belong in dataclasses, not epilog strings.
- **Workshop teaching opportunity:** Small argparse footgun + single-source-of-truth for config.

---

#### 29. walled-gardens-blind-spot — Walled-garden sources make reports contradict reality
- **Friction-type:** F1 (incorrect/incomplete output due to data-source limits)
- **Source traces:** A3 `docs/lessons/operations.md:166-194`, `LESSONS_LEARNED.md:25`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17+
- **Date/source:** see traces (Lodge at Torrey Pines real runs)
- **Tool used:** real-world research runs
- **Project/topic:** Real-world report quality
- **Original goal:** Produce accurate org/competitive intel.
- **Context provided:** LinkedIn, TripAdvisor/Yelp/Google block scrapers, Jina, Tavily Extract.
- **Files/tools used:** fetch cascade
- **Agent actions:** Reports drew only on the public, fetchable record; near-identical entity names both passed relevance.
- **What worked:** Treat reports as the public-facing layer; "insufficient data" as a valid answer; short queries (<15 words) beat complex ones.
- **What failed or caused friction:** Reports could actively contradict reality when key info lives behind walled gardens; entity disambiguation is a scorer weakness.
- **Human correction or steering:** Frame reports as public record, not ground truth.
- **Final outcome:** Honest scoping of capabilities.
- **Reusable lesson:** Know the agent's blind spots (auth walls); "absence of evidence" can be a meaningful finding; keep queries short.
- **Workshop teaching opportunity:** Setting realistic expectations for what a web-research agent can and cannot know.

---

### F2 — Vague/underspecified human input → bad output, fixed by prompt/spec refinement

---

#### 30. vague-query-no-gate — "stuff" burned API credits before any fail-fast gate
- **Friction-type:** F2 (vague user input → wasted work, fixed by an input gate)
- **Source traces:** A3 `docs/solutions/feature-implementation/input-validation-and-generation-controls.md:39-52,66-71`; A5 `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md:40-88,308` (see also episode 44); `query_validation.py`, `agent.py`, `mcp_server.py`
- **Corroboration:** 2
- **Cycle/arc:** Cycle 27
- **Date/source:** solution doc 2026-04-05
- **Tool used:** not clear; 7-agent review
- **Project/topic:** Input validation
- **Original goal:** Reject useless queries cheaply.
- **Context provided:** "stuff"/"best things" ran decompose+search+summarize before producing nothing.
- **Files/tools used:** `query_validation.py`, `agent.py`, `mcp_server.py`
- **Agent actions:** No pre-check; vague queries consumed credits.
- **What worked:** Pure-Python `check_query_vagueness()` (no LLM) at the top of `_research_async()`; `VAGUE_WORDS` frozenset; idempotent sanitize via `html.unescape()` before escaping; `VagueQueryError` propagates through the existing MCP error path.
- **What failed or caused friction:** Heuristic misses subtler vague queries ("tell me about technology" passes) — accepted, monitor. Review found the temperature misroute (#127), missing injection tests (#128), MCP parity gaps.
- **Human correction or steering:** Place validation before expensive work.
- **Final outcome:** Fail-fast gate; idempotent sanitizer.
- **Reusable lesson:** Place validation before expensive work; unescape-then-escape makes sanitization idempotent.
- **Workshop teaching opportunity:** Fail-fast input gating and a clean fix to the recurring double-encode bug.

---

#### 31. business-template-all-queries — Hardcoded business sections forced onto technical queries
- **Friction-type:** F2 (template/prompt assumed wrong domain → bad output); tagged F4 "wrong altitude" in A4
- **Source traces:** A3 `docs/solutions/logic-errors/conditional-prompt-templates-by-context.md:16-83`, `docs/solutions/architecture/domain-agnostic-pipeline-design.md:24-187`; A4 commits `5f3a9d5`, `6e0712a`, `10a8b75`, `60a185a`, `80d27ad`, `341a3ab`
- **Corroboration:** 2
- **Cycle/arc:** Cycle 20 / 22 / ~23 (flexible-context-system)
- **Date/source:** solution docs 2026-02-26, 2026-02-28
- **Tool used:** not clear (surfaced during E2E testing of `/research:queue` and `/research:digest`)
- **Project/topic:** Synthesis prompt templates; generalizing the pipeline beyond competitive intel
- **Original goal:** Generate structured reports for all query types.
- **Context provided:** Prompts written for one use case (Pacific Flow competitive intel); 7 prompt sites hardcoded "business"; `DEFAULT_CONTEXT_PATH` silently loaded a file when `None`; one-file folder skipped relevance; write-time sanitization double-encoded on read.
- **Files/tools used:** `synthesize.py`, `agent.py`, `context.py`, `summarize.py`, `decompose.py`, `critique.py`, `context_result.py`
- **Agent actions:** "Buyer Psychology", "Service Portfolio", "Company Overview" forced onto "how does Python asyncio work" → hallucinated/empty sections; the fix had to be applied twice (draft + final; a leftover `elif context` legacy branch with "Competitive Implications"/"Positioning Advice" survived the first pass).
- **What worked:** Branch on `has_business_context: bool`; generic fields ("KEY EVIDENCE"/"PERSPECTIVE"); explicit None over hidden default; always run the relevance gate; sanitize at consumption. Net -210 lines (subtractive).
- **What failed or caused friction:** Invisible when only business queries were run; a single technical-query test would have caught it; reasonable single-user assumptions broke when generic.
- **Human correction or steering:** Make prompt assumptions explicit parameters; test outside the original domain; stale on-disk YAML accepted as self-healing (10-file TTL).
- **Final outcome:** Domain-neutral pipeline.
- **Reusable lesson:** Grep for original-domain vocabulary when expanding scope; explicit None > hidden defaults; domain-specific structure hardcoded into a shared path is technical debt — gate it behind a config check; test outside the original domain.
- **Workshop teaching opportunity:** How "reasonable" early assumptions accumulate into coupling — and that the fix is often deletion.

---

#### 32. skeptic-incorporate-vs-act — "Address this finding" produced vague compliance
- **Friction-type:** F2 (vague prompt instruction → vague model behavior)
- **Source traces:** A3 `docs/solutions/feature-implementation/skeptic-enforcement-quality-gates-evidence-tiers.md:24-38,100-104`; `skeptic.py`, `synthesize.py`, `evidence.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 29
- **Date/source:** 2026-04-21
- **Tool used:** not clear
- **Project/topic:** Skeptic-finding enforcement in synthesis
- **Original goal:** Make synthesis act on skeptic findings.
- **Context provided:** Prompt said "address/incorporate this finding."
- **Files/tools used:** `skeptic.py`, `synthesize.py`, `evidence.py`
- **Agent actions:** Model claimed it "incorporated" concerns without changing anything.
- **What worked:** A concrete 3-way action menu: (a) remove claim, (b) mark `[Disputed]`, (c) cite evidence.
- **What failed or caused friction:** "Incorporate" is interpreted as "mention without changing"; a quality gate broke 6 tests whose mock data was too short.
- **Human correction or steering:** Wording changed to observable actions; regression tests added.
- **Final outcome:** Enforceable contract; deep-mode label drift left unverified (API key).
- **Reusable lesson:** Replace "address X" with a concrete action menu; vague instructions yield vague compliance.
- **Workshop teaching opportunity:** Prompt-engineering core lesson: specify observable actions, not intentions.

---

#### 33. mcp-input-normalization — LLM clients send `"null"`/`""` where they mean None
- **Friction-type:** F2 (vague/malformed LLM input → downstream FileNotFoundError)
- **Source traces:** A3 `docs/solutions/security/mcp-server-boundary-protection-and-agent-parity.md:156-191,265`; A1 `todos/097-done-p3-context-param-normalization.md:14`
- **Corroboration:** 1 (A1 records the same as part of the auto-detect cluster — episode 116)
- **Cycle/arc:** Cycle 19 (finding 097)
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** MCP `context` parameter (three-way None/"none"/"name")
- **Original goal:** Let agents pass a context name, skip, or auto-detect.
- **Context provided:** LLM callers frequently stringify null as `"null"`, send `""` or whitespace.
- **Files/tools used:** `mcp_server.py`
- **Agent actions:** Wrong "no value" representations treated as filenames → crash deep in pipeline.
- **What worked:** 3-line boundary normalization (`strip`, lowercase, `"null"`/`""`→None) while preserving the `"none"` skip-sentinel.
- **What failed or caused friction:** Surgical distinction needed: normalize `"null"` but NOT `"None"` (a client bug to surface) and NOT `"none"` (the skip sentinel).
- **Human correction or steering:** Graceful normalization over `ToolError`.
- **Final outcome:** Robust boundary; documented why each case is handled or not.
- **Reusable lesson:** Defensively normalize optional string fields at the LLM boundary; preserve the distinction between "no value" and "explicit skip."
- **Workshop teaching opportunity:** Designing tool interfaces for the *actual* (sloppy) behavior of LLM callers.

---

#### 34. plan-public-api-test-gap — Plan widens the public API but omits the test that polices it
- **Friction-type:** F2 (underspecified plan would break the build if executed mechanically)
- **Source traces:** A2 `docs/reviews/2026-03-08-cycle-25-codex-plan-findings.md:5-12`, plan `:63-68,153`, `tests/test_public_api.py:45-66`, `2026-03-08-cycle-25-code-review-findings.md:11`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 25 (Housekeeping) — PLAN review
- **Date/source:** 2026-03-08
- **Tool used:** Codex
- **Project/topic:** `parse_context_file` public wrapper
- **Original goal:** Replace a private `_parse_template` import with a public wrapper.
- **Context provided:** Plan at `docs/plans/2026-03-08-cycle-25-housekeeping-plan.md`.
- **Files/tools used:** plan, `tests/test_public_api.py`
- **Agent actions:** Plan adds `parse_context_file` to `__init__.py.__all__`, but `test_public_api.py` asserts the exact contents of `__all__` — executing the plan mechanically fails the suite.
- **What worked:** Codex reviewed the plan against the *test that enforces the contract the plan changes* — before any code.
- **What failed or caused friction:** The plan claimed a mechanical change but quietly widened the public API without listing the test that polices it.
- **Human correction or steering:** Pick one path (module-public vs package-public) and update the plan's file list, acceptance criteria, and checks.
- **Final outcome:** P2 plan blocker; plan revised; resulting code review found no material findings.
- **Reusable lesson:** A plan that touches a contract must name the test that guards it; plan review catches build-breaking contradictions before they cost an implementation cycle.
- **Workshop teaching opportunity:** The cheapest place to catch a "this can't stay green" problem is the plan, not the diff.

---

#### 35. plan-enforcement-gap — CI plan claims "prevents drift" but omits branch-protection
- **Friction-type:** F2 (plan overstates what its artifact achieves)
- **Source traces:** A2 `docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md:5-9`, brainstorm `:16-20`, plan `:74-105`, handoff `:52-53`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26 — PLAN review
- **Date/source:** 2026-03-08
- **Tool used:** Codex
- **Project/topic:** MCP parity CI enforcement
- **Original goal:** Make the MCP parity check block drift from reaching `main`.
- **Context provided:** Brainstorm claims the workflow "actually prevents drift from reaching `main`."
- **Files/tools used:** brainstorm, plan, handoff
- **Agent actions:** The plan only adds the workflow file but never includes the repo-settings step to make the check *required* — so a mechanical implementer leaves it advisory-only.
- **What worked:** Codex distinguished "a workflow exists" from "a merge gate is enforced."
- **What failed or caused friction:** The cycle's entire justification was enforcement, but the plan delivered only visibility.
- **Human correction or steering:** Add the branch-protection rollout step, or narrow the claim to "surfaces drift in CI."
- **Final outcome:** P2 plan blocker.
- **Reusable lesson:** Adding a CI job is not the same as enforcing it; "required status check" is a separate, often-forgotten config step.
- **Workshop teaching opportunity:** The gap between writing automation and wiring it into the gate.

---

#### 36. plan-install-ambiguity — Plan's verification commands assume uninstalled tooling
- **Friction-type:** F2 (underspecified setup blocks reproducible verification)
- **Source traces:** A2 `docs/reviews/2026-03-08-cycle-26-codex-plan-findings.md:11-15`, plan refs, `pyproject.toml:25-29`, `CLAUDE.md:54-58`, `README.md:16-22`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26 — PLAN review
- **Date/source:** 2026-03-08
- **Tool used:** Codex
- **Project/topic:** Local-vs-CI setup instructions
- **Original goal:** Give a clean-checkout verification path.
- **Context provided:** Plan uses `pytest` for local checks but only documents `pip install -e .` (no test extra); README still says `pip install -r requirements.txt`.
- **Files/tools used:** plan, `pyproject.toml`, `CLAUDE.md`, `README.md`
- **Agent actions:** Codex cross-checked the plan's commands against three setup sources of truth; test tooling lives in the `[test]` extra so a clean checkout can't run verification without guessing.
- **What worked:** Cross-referencing three install sources.
- **What failed or caused friction:** Inconsistent install docs break the "executable without new design decisions" handoff standard.
- **Human correction or steering:** Add a prerequisites section separating CI install from local verification (`pip install -e ".[test]"`).
- **Final outcome:** P3 advisory; plan updated.
- **Reusable lesson:** Verification steps are only real if the setup to run them is specified; conflicting install docs are a silent blocker.
- **Workshop teaching opportunity:** "Works on my machine" starts in the plan.

---

#### 37. claudemd-stale-context — CLAUDE.md references a deleted file, misleading future sessions
- **Friction-type:** F2 (stale spec/context will mislead future agent runs)
- **Source traces:** A2 `docs/reviews/flexible-context-system/REVIEW-SUMMARY.md:24-26,49`, `CLAUDE.md:64,21-22`
- **Corroboration:** 1
- **Cycle/arc:** Flexible Context System
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agents (pattern-recognition + architecture-strategist)
- **Project/topic:** Project context doc accuracy
- **Original goal:** Refactor the context system (net -210 lines).
- **Context provided:** The refactor deleted `research_context.md` and removed business-context validation.
- **Files/tools used:** `CLAUDE.md`
- **Agent actions:** CLAUDE.md still references the deleted file — "Actively misleads every future Claude Code session" — prioritized #1 in the fix order.
- **What worked:** The reviewer recognized that a stale CLAUDE.md harms *future agent runs*, not just human readers.
- **What failed or caused friction:** Code was refactored but its governing context document wasn't updated.
- **Human correction or steering:** Update CLAUDE.md references; fixed first.
- **Final outcome:** P2, top of fix order.
- **Reusable lesson:** For agent-operated codebases, the instructions file *is* runtime input; stale guidance silently corrupts every future session.
- **Workshop teaching opportunity:** Treat CLAUDE.md/AGENTS.md as code — drift there compounds across sessions.

---

#### 38. mode-validation-boundary — No mode validation at the MCP trust boundary
- **Friction-type:** F2 (no input validation at the trust boundary → wasted work)
- **Source traces:** A1 `todos/093-done-p2-mode-validation-mcp-boundary.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26
- **Date/source:** see traces
- **Tool used:** not clear (Security/defense-in-depth)
- **Project/topic:** `run_research` accepts a free-form `mode` string, fails deep in `ResearchMode.from_name()`
- **Original goal:** Validate at the boundary so bad input fails fast.
- **Context provided:** "Invalid modes traverse the entire call stack before failing... wastes API call budget."
- **Files/tools used:** `mcp_server.py`
- **Agent actions:** Located where untrusted input first enters.
- **What worked:** Boundary-validation principle.
- **What failed or caused friction:** Validation happened too deep in the stack.
- **Human correction or steering:** Accepted.
- **Final outcome:** done.
- **Reusable lesson:** Validate at the edge; failing fast saves money and gives clearer errors.
- **Workshop teaching opportunity:** Cost-aware input validation for agent-facing tools.

---

#### 39. abstention-gate-placement — Where to put a hallucination check: summarize vs synthesize
- **Friction-type:** F2 (under-specified placement pinned to a concrete spec via evidence)
- **Source traces:** A5 `docs/brainstorms/2026-04-21-cycle-30-summarization-context-preservation-brainstorm.md:26-30,68,74`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 30
- **Date/source:** 2026-04-21
- **Tool used:** not clear
- **Project/topic:** Synthesis abstention gate (flag uncorroborated stats/dates/named studies)
- **Original goal:** Decide whether the abstention gate belongs in `summarize.py` (per-source) or `synthesize.py` (all sources visible) — roadmap flagged 75% confidence, "planning must resolve."
- **Context provided:** Epistemic calibration study §3.5 — the model only correctly refuses fabricated citations when it has cross-source context.
- **Agent actions:** Reasoned that per-chunk summarization has no cross-source visibility, so it would risk *false* refusals; synthesis can cross-reference.
- **What worked:** Using a specific study finding to break a genuine tie.
- **What failed or caused friction:** Both options had real trade-offs; the prior phase couldn't decide.
- **Human correction or steering:** Placement resolved to synthesis; documented that uncorroborated claims survive summarization unflagged until the final report.
- **Final outcome:** `ABSTENTION_INSTRUCTION` injected at synthesis, excluded from drafts.
- **Reusable lesson:** "Where should this check live?" is answered by "where does the check have enough context to be correct?"
- **Workshop teaching opportunity:** Resolving an explicitly-deferred risk by tracing what information each pipeline stage actually has.

---

#### 40. novelty-prompt-wording-deferred — Study's phrasing wrong for search queries
- **Friction-type:** F2 (vague prompt direction → risk of degraded output, refined in plan)
- **Source traces:** A5 brainstorm `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md:88,94`, plan `docs/plans/2026-04-23-feat-novelty-decomposition-mcp-cost-critique-plan.md:26-30,66-69`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 31
- **Date/source:** 2026-04-22/23
- **Tool used:** not clear
- **Project/topic:** Novelty-biased decomposition (some sub-queries target overlooked angles)
- **Original goal:** Apply the study's "mechanisms most people overlook" framing to push past centroid results.
- **Context provided:** Epistemic calibration study §3.1; but `decompose.py` generates *search queries*, not explanations.
- **Agent actions:** Brainstorm "Least confident" named the gap: the study's wording produces interesting explanations, not good *search engine queries*. The plan rewrote it to "angles that typical searches would miss," validated via three offline trace-throughs against `_validate_sub_queries()`.
- **What worked:** The brainstorm-to-plan feed-forward chain: a flagged uncertainty became a concrete prompt revision plus a verification method.
- **What failed or caused friction:** Lifting a prompt phrasing from a study without adapting it to the task would have degraded decomposition.
- **Human correction or steering:** Reframe in search-query terms; `verify_first: false` with offline fixture validation (live A/B blocked on API key).
- **Final outcome:** `NOVELTY_INSTRUCTION_TEMPLATE`; live A/B deferred to Cycle 33.
- **Reusable lesson:** A prompt that works in one task framing must be re-grounded in the target task's output type.
- **Workshop teaching opportunity:** Textbook "Least confident → next phase addresses it verbatim" steering loop.

---

#### 41. flexible-context-template-tension — Two of the agent's own decisions directly contradict
- **Friction-type:** F2 (ambiguous spec with a self-contradiction, flagged for resolution)
- **Source traces:** A5 `docs/brainstorms/2026-02-26-flexible-context-system-brainstorm.md:75-77,92-94,98-100`
- **Corroboration:** 1
- **Cycle/arc:** flexible context system, 2026-02-26
- **Date/source:** 2026-02-26
- **Tool used:** not clear
- **Project/topic:** Make the agent domain-agnostic (LLM generates report sections from any context file)
- **Original goal:** Both "report template adapts dynamically to context content" (Decision #4) and "preserve current PFE behavior" (Decision #5).
- **Context provided:** PFE currently uses a hardcoded 8-section format.
- **Agent actions:** Named the conflict in Open Questions: "Decisions #4 and #5 conflict," offering three resolution options and punting to the plan.
- **What worked:** Catching that two attractive goals are mutually incompatible before committing code.
- **What failed or caused friction:** Dynamic template generation is "powerful but hard to test and less predictable"; backward-compat pulls the opposite way.
- **Human correction or steering:** Flagged dynamic templates as "Least confident," requiring plan-phase guardrails (minimum required sections, malformed-output fallback).
- **Final outcome:** Tension handed to plan with explicit resolution options.
- **Reusable lesson:** When two key decisions tug opposite directions, write the contradiction down as an open question rather than papering over it.
- **Workshop teaching opportunity:** An AI noticing and surfacing its own inconsistent requirements.

---

#### 42. live-test-fetch-cascade — Compatibility matrix beat documentation for fallbacks
- **Friction-type:** F2 (designing from assumptions/docs → wrong design, fixed by live testing)
- **Source traces:** A3 `docs/lessons/operations.md:103-127`, `LESSONS_LEARNED.md:16`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 9
- **Date/source:** see traces
- **Tool used:** live testing on blocked URLs
- **Project/topic:** Fetch cascade (Jina → Tavily Extract → snippet)
- **Original goal:** Build a fallback chain for blocked fetches.
- **Context provided:** Different services block different sites; Jina Search was *assumed* free but needed an API key.
- **Files/tools used:** `cascade.py`, `fetch.py`
- **Agent actions:** Would have designed the chain from docs/assumptions.
- **What worked:** A live compatibility matrix; Jina Reader emerged as the highest-value free tool; domain-filter expensive Tavily Extract; check 404 vs 403 before escalating.
- **What failed or caused friction:** Assumptions (Jina Search free) were wrong; docs didn't reflect real block behavior.
- **Human correction or steering:** Live-test before committing.
- **Final outcome:** Evidence-based cascade.
- **Reusable lesson:** Live-test integrations on real blocked URLs before designing around them — compatibility matrices beat documentation.
- **Workshop teaching opportunity:** Verifying external-tool behavior empirically before the agent designs around assumptions.

---

#### 43. interactive-prompt-in-agent-context — Skill blocks on a human prompt in automated runs
- **Friction-type:** F2 (design assumes interactive human; breaks in automated runs)
- **Source traces:** A1 `todos/059-complete-p2-interactive-digest-prompt.md:14`, `.claude/skills/research-digest.md:67-71`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 22
- **Date/source:** see traces
- **Tool used:** not clear (Agent-native reviewer)
- **Project/topic:** digest skill says "Ask the user: 'Mark all N items as reviewed?'"
- **Original goal:** Don't block in agent/automated contexts with no interactive user.
- **Context provided:** tagged `agent-native`.
- **Files/tools used:** `.claude/skills/research-digest.md:67-71`
- **Agent actions:** Flagged a human-in-the-loop assumption.
- **What worked:** Agent-native lens caught a blocking interaction.
- **What failed or caused friction:** Skill authored for a human, run by an agent.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Automation steps must have a non-interactive default; "ask the user" is a deadlock in agent mode.
- **Workshop teaching opportunity:** The "agent-native parity" theme — design for both human and agent callers.

---

#### 44. vague-query-heuristic-vs-llm — Defining "vague" without burning an API call
- **Friction-type:** F2 (vague input → bad output, fixed by spec refinement)
- **Source traces:** A5 `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md:40-88,308`
- **Corroboration:** 1 (distinct from episode 30: this is the brainstorm-phase *heuristic design* deliberation; episode 30 is the shipped gate + its review)
- **Cycle/arc:** Cycle 27
- **Date/source:** 2026-04-05
- **Tool used:** not clear
- **Project/topic:** Vague-query detection
- **Original goal:** Roadmap said "reject queries with <3 meaningful words, no domain-specific terms" — a one-line, under-specified directive.
- **Context provided:** Existing `query_validation.py` helpers; entropy audit finding #1 that garbage queries flow through the pipeline.
- **Agent actions:** Built a 12-row edge-case table; iterated the rule live in the doc (pure word count → +4-char rule → +generic-adjective list), visibly walking toward complexity ("This is getting complex. Let me step back").
- **What worked:** The edge-case table exposed that pure word count passes "what is the best way to" (2 meaningful words, no topic).
- **What failed or caused friction:** The first two heuristics each failed a case; the AI nearly over-engineered toward POS tagging.
- **Human correction or steering:** "Keep it simple" / "Simplest viable rule" forced settling on ≥2 meaningful words AND reject if all words are vague; LLM-based classification explicitly rejected as defeating the purpose.
- **Final outcome:** `check_query_vagueness()` shipped as a pure-Python pre-flight check.
- **Reusable lesson:** When a spec says "detect X," write the adversarial input table first — it tells you whether a cheap heuristic suffices or you truly need the model.
- **Workshop teaching opportunity:** Watching an agent talk itself toward over-engineering and pull back — the clearest demo of "test cases before cleverness."

---

### F3 — AI hit a wall / got stuck / indefinite deferral / loop

---

#### 45. mcp-cost-critique-parity-deferred — MCP cost/critique parity + lint deferred ~5 cycles
- **Friction-type:** F3 (indefinite deferral / item decay)
- **Source traces:** A1 `todos/068-pending-p2-api-parity-gaps.md:14`, `todos/094-done-p2-missing-critique-report-tool.md:14`, `todos/095-done-p2-missing-skip-critique-max-sources.md`, `todos/123-pending-p2-mcp-missing-cost-and-critique-history-tools.md:14-22`; A2 `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md:52-53,72` (parity P1→P2); A3 `docs/solutions/workflow/mcp-parity-lint-ci-enforcement.md:26-92`; A4 commit `e9d1eba` (deferred #123), `329c469`/`94df004` (resolved), MEMORY.md; A5 `docs/brainstorms/2026-03-08-cycle-26-mcp-parity-lint-brainstorm.md:5-21,46-50`
- **Corroboration:** 5
- **Cycle/arc:** Cycles 19 → 31 (issue #123); lint deferred in 19, 20, 22, 25
- **Date/source:** see traces; solution doc 2026-03-10
- **Tool used:** not clear; A5 notes a Cycle 25 plan-review blocker (likely Codex); GitHub Actions CI
- **Project/topic:** MCP tool↔CLI parity and the parity lint script
- **Original goal:** Achieve full parity between CLI features and MCP tools; block merges where a tool isn't mentioned in MCP instructions.
- **Context provided:** "Deferred (#123): MCP --cost and --critique-history tools"; the pytest test catches drift only when the suite runs — the missing piece was *where and when* the check runs; substring matching (`name not in instructions`) gave `list`/`report` false-positives.
- **Files/tools used:** `mcp_server.py`, `scripts/lint_mcp_parity.py`, `.github/workflows/mcp-lint.yml`
- **Agent actions:** Repeatedly deferred the `--cost`/`--critique-history` MCP tools; the lint script itself was deferred across four cycles as the "least ready" bundled item. The C26 brainstorm diagnosed that the deferral recurred because the script lacked a *gate*, not because it was wrong.
- **What worked:** Promote-or-drop decision; added a GitHub Actions CI gate (rejected pre-commit/Makefile as no-enforcement); word-boundary regex; eventually `get_critique_history` shipped (C31) and `show_costs` was deliberately dropped (covered by `list_research_modes`).
- **What failed or caused friction:** A parity item drifted for ~5 cycles; "Items deferred 2+ times → drift indefinitely."
- **Human correction or steering:** "Promote-or-drop at deferral #2" rule established; "every enforcement mechanism ships with its feature."
- **Final outcome:** One tool shipped, one explicitly dropped; lint shipped with CI green first run.
- **Reusable lesson:** Track deferral counts and force a promote-or-drop decision at the second deferral; an item that keeps getting deferred is usually missing one concrete attribute (here: an enforcement gate) — supply it or drop it; ship the enforcement check with the feature it enforces.
- **Workshop teaching opportunity:** How agent-managed backlogs accumulate zombie items without an explicit kill rule.

---

#### 46. batch-size-symptom-chasing — Four tuning commits chase 429s before the root cause
- **Friction-type:** F3 (stuck / loop — repeated tuning that treats a symptom); A3 also tags the wrong-layer root cause F6 and the fixed-sleep F4
- **Source traces:** A4 commits `0c49066`, `c0176c0`, `413cbc5`, `ed59318`, lesson `84ff163`; A3 `docs/lessons/operations.md:129-135`, `LESSONS_LEARNED.md:18`, `docs/solutions/performance-issues/adaptive-batch-backoff.md:16-91` (commit `0c44f95`)
- **Corroboration:** 2
- **Cycle/arc:** Cycles 10–11 (plus the related Cycle-17 fixed-sleep — see episode 55)
- **Date/source:** see traces
- **Tool used:** Claude (Opus 4.6 trailers on `413cbc5`, `c0176c0`, `ed59318`)
- **Project/topic:** Summarization rate-limiting (HTTP 429) in `summarize.py` / `relevance.py`
- **Original goal:** Stop hitting the 30K tokens/min API tier rate limit during chunk summarization.
- **Context provided:** Benchmark counts ("651 → 303 HTTP 429 responses").
- **Files/tools used:** `summarize.py`, `relevance.py`, `CLAUDE.md`, tests
- **Agent actions:** Reduced batch size 12→8, then 8→5 + added relevance batching, then finally added a `MAX_CONCURRENT_CHUNKS=3` semaphore, then raised batch size back 5→8. The real fan-out was `5 sources × 5 chunks = 25 simultaneous calls` via `asyncio.gather`.
- **What worked:** The semaphore at the leaf `summarize_chunk` call capped in-flight calls regardless of batch size; app-level 429s dropped ~30→1.
- **What failed or caused friction:** Two commits of batch-size tuning treated the symptom; concurrency control was at the wrong (task-organization) layer.
- **Human correction or steering:** Lesson `84ff163` named this "symptom-chasing" and prescribed flattening chunk fan-out; move concurrency control to the API-call layer.
- **Final outcome:** Root-cause semaphore fix; batch size raised again with no 429s.
- **Reusable lesson:** When a knob "helps a bit," suspect you're tuning a symptom; find the multiplicative root cause (sources × chunks) and put concurrency control where the API calls actually happen.
- **Workshop teaching opportunity:** Classic agent failure mode — iterating on a parameter that reduces but never eliminates a problem instead of stepping back to the architecture.

---

#### 47. novelty-diversity-gate-unverified — Heuristic shipped behind invariants; live A/B blocked on API key
- **Friction-type:** F3 (blocked verification — wall on validation)
- **Source traces:** A4 HANDOFF history + `HANDOFF.md:5,38-39`, `scripts/validate_cutoff_ab.py`; `decompose.py`, `relevance.py`, `modes.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycles 28–32
- **Date/source:** HANDOFF "least confident" notes
- **Tool used:** Claude (Opus trailers)
- **Project/topic:** Decomposition + diversity gate interaction
- **Original goal:** Bias decomposition toward novelty while a diversity gate prevents single-source reports.
- **Context provided:** HANDOFF "least confident" notes across multiple cycles.
- **Files/tools used:** `decompose.py`, `relevance.py`, `scripts/validate_cutoff_ab.py`
- **Agent actions:** Shipped architectural "safety nets" (cross-module invariant test `deep().novelty_queries <= MAX_SUB_QUERIES`) but repeatedly logged that the cutoff/diversity/novelty interaction is "Untested end-to-end."
- **What worked:** Code-analysis-based safeguards and invariant tests.
- **What failed or caused friction:** The Tavily/Anthropic API key expired, so live A/B validation was "blocked on API key renewal"; the project was eventually parked.
- **Human correction or steering:** Human parked the project rather than ship unvalidated tuning; deferred A/B and threshold tuning explicitly.
- **Final outcome:** Feature shipped behind invariants; empirical validation deferred until key renewal.
- **Reusable lesson:** When you can't empirically validate a heuristic, ship behind invariants and *name the unverified risk* rather than claiming success.
- **Workshop teaching opportunity:** Honest "least confident" handoffs — the AI flagging exactly what it could not verify.

---

#### 48. anthropic-errors-deferred-adopt — Shared exception constant defined but unused for 2 cycles
- **Friction-type:** F3 (indefinite deferral; copy-paste kept accumulating)
- **Source traces:** A3 `docs/solutions/architecture/constant-consolidation-and-dataclass-conversion.md:18-93`; `modes.py`, `report_store.py`, `errors.py`, `results.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 32 (defined in 29H)
- **Date/source:** 2026-05-03
- **Tool used:** review (4 agents); 7-agent plan deepening
- **Project/topic:** Constant consolidation
- **Original goal:** Stop copy-pasting the 4-exception tuple across 10+ files.
- **Context provided:** `ANTHROPIC_ERRORS` defined in 29H but never consumed; `META_DIR` in the heavy orchestrator; 18-line `ModeInfo` manual mapping.
- **Files/tools used:** `modes.py`, `report_store.py`, `errors.py`, `results.py`
- **Agent actions:** Adopted the constant at 10 call sites; moved `META_DIR`; added explicit `to_mode_info()`.
- **What worked:** Pick the convention-matching option when 3 agents disagree; loud `TypeError` over silent dict-asdict; comment guardrail against circular import.
- **What failed or caused friction:** The 2-cycle define→adopt gap let copy-paste accumulate; `except (ResearchError, *ANTHROPIC_ERRORS)` is invalid Python.
- **Human correction or steering:** Documented edge cases; rule: adopt a constant the same cycle you define it.
- **Final outcome:** Consolidated.
- **Reusable lesson:** Don't define-then-defer; when agents disagree on placement, follow existing convention.
- **Workshop teaching opportunity:** Deferred-debt decay and the "3 agents disagree → pick convention" heuristic.

---

#### 49. auto-compact-mid-cycle — Auto-compaction silently degrades multi-step work
- **Friction-type:** F3 (context-window wall / lost state)
- **Source traces:** A3 `docs/solutions/workflow/auto-compact-mid-cycle-risks.md:14-84`
- **Corroboration:** 1
- **Cycle/arc:** not clear (workflow)
- **Date/source:** 2026-02-11
- **Tool used:** Claude Code (auto-compact)
- **Project/topic:** Session management
- **Original goal:** Run multi-step plans without losing context.
- **Context provided:** Auto-compact fires when the window is full; no pre-threshold warning hook; `PreCompact` fires only at full.
- **Files/tools used:** CLAUDE.md, `docs/plans/`, `todos/`, git
- **Agent actions:** Long sessions risk flattened plans, broken multi-file edit coherence, stale task state.
- **What worked:** Write everything to disk; commit every 50-100 lines; proactive `/compact` between phases; CLAUDE.md for critical context.
- **What failed or caused friction:** No hook to warn before compaction; mid-edit compaction breaks file coherence.
- **Human correction or steering:** Mitigation playbook established.
- **Final outcome:** "Write it down" as the primary defense.
- **Reusable lesson:** Disk is permanent, context is ephemeral — persist plans/state and commit frequently to survive compaction.
- **Workshop teaching opportunity:** Managing long agent sessions and the context wall — a central workshop topic.

---

#### 50. query-iteration-differentiation-risk — Forcing a feature to prove it isn't redundant
- **Friction-type:** F3 (risk of building something that duplicates existing behavior — wasted spend)
- **Source traces:** A5 `docs/brainstorms/2026-03-01-query-iteration-brainstorm.md:104-106`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 20
- **Date/source:** 2026-03-01
- **Tool used:** not clear
- **Project/topic:** Auto-refine queries + predictive follow-up questions within one run
- **Original goal:** Add a refinement pass that reframes the question and pre-researches follow-ups.
- **Context provided:** The agent already has decompose (splits facets) and coverage retry (more sources on weak sub-queries).
- **Agent actions:** Flagged that refinement might not be "meaningfully different from what decompose + coverage retry already do" and demanded the plan define a prompt producing queries "decompose would never generate," tested on 3-5 real queries before committing.
- **What worked:** Pre-emptively setting a differentiation bar so the feature can't ship as redundant API calls.
- **What failed or caused friction:** Without this gate, the feature risked being expensive duplication.
- **Human correction or steering:** "otherwise this is wasted API calls. Test ... before committing to the architecture."
- **Final outcome:** Additive `iterate.py` stage with mode params; differentiation made a plan-phase prerequisite.
- **Reusable lesson:** Before adding a stage that resembles an existing one, define and test what makes it non-redundant.
- **Workshop teaching opportunity:** "Does this new step earn its cost?" as a steering question for feature-happy agents.

---

#### 51. cycle33-park-not-busywork — Choosing to stop rather than invent low-value work
- **Friction-type:** F3 (external blocker / avoiding loop-for-its-own-sake)
- **Source traces:** A5 `docs/brainstorms/2026-05-03-cycle-33-parking-brainstorm.md:20-46,49-58,60-66`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 33
- **Date/source:** 2026-05-03
- **Tool used:** not clear
- **Project/topic:** Whether to start another cycle
- **Original goal:** Keep the compound loop going.
- **Context provided:** All high-value remaining work (novelty A/B validation, diversity-gate tuning) is blocked on Tavily API-key renewal; unblocked items are 15-line micro-tasks.
- **Agent actions:** Decided to park; rejected running ModeInfo `__post_init__` validation or an import-graph linter as too small to justify a full cycle.
- **What worked:** Honestly assessing that the meaningful next work has a hard external blocker.
- **What failed or caused friction:** "There's always pressure to 'do something'."
- **Human correction or steering:** "Whether to invent busy work or park. Parking is the right call." Documented a concrete resume trigger.
- **Final outcome:** Project paused with a copy-paste resume plan.
- **Reusable lesson:** When the valuable work is blocked, stop and document the resume trigger instead of generating filler.
- **Workshop teaching opportunity:** Giving an agent permission to say "nothing worth doing right now" — and how to leave a clean resume note.

---

### F4 — Scope creep / over-engineering / wrong altitude (YAGNI)

---

#### 52. over-flagged-dead-code-rejected — Human rejects "remove 270 LOC of dead code"
- **Friction-type:** F4 (over-flagging YAGNI judgment reversed by human; later flipped)
- **Source traces:** A1 `todos/004-rejected-p2-dead-code-removal.md:1-3,14,18-26,63,67`, `todos/007-rejected-p2-dead-cycle-config-params.md:1-3,14,18-19,41`, `todos/010-rejected-p2-schema-too-many-responsibilities.md:1-3,7,18-19,26`, `todos/033-complete-p3-dead-code-387-loc.md:14`; A3 `docs/solutions/architecture/gap-aware-research-loop.md:24-101` (3 rejected as future-use foundation)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17 (rejected), then Cycle 18 (accepted in 033)
- **Date/source:** created 2026-02-15
- **Tool used:** not clear (Simplicity reviewer / Architecture strategist)
- **Project/topic:** dead-code removal in `schema.py`, `state.py`, `errors.py`; unread `cycle_config.py` fields; SRP split of 362-line `schema.py`
- **Original goal:** Reviewers proposed deleting ~270 LOC of never-called functions (`detect_cycles`, `sort_gaps`, `SortedGaps`, `validate_gaps`, `update_gap`, `ContextAuthError`) and two never-read config params.
- **Context provided:** "Total potential LOC reduction: ~530 lines"; finding 010 depended on 004; "If dead code (004) is removed first, this shrinks to ~160 lines."
- **Files/tools used:** `schema.py`, `state.py`, `errors.py`, `cycle_config.py`
- **Agent actions:** 3/7 agents flagged YAGNI ("built for hypothetical future needs that don't exist yet"). The human rejected 004/007/010; the SRP split (010) auto-resolved because its premise (004 removed) no longer held. By Cycle 18 the roadmap changed and 033 re-proposed the same code — accepted then.
- **What worked:** Reviewers correctly identified no live callers; the reviewer chained 010 to its dependency rather than recommending the big split outright.
- **What failed or caused friction:** The AI treated "no callers now" as "delete forever"; it can't see the roadmap; it re-proposed the same removal across cycles (rejected in 004, complete in 033).
- **Human correction or steering:** "Rejected — foundation code for future cycles"; "params will be read when budget enforcement uses config"; "resolves naturally since 004 is kept." Don't permanently suppress — re-triage.
- **Final outcome:** 004/007/010 rejected; 033 complete (roadmap reassessment).
- **Reusable lesson:** "No current caller" ≠ "delete it"; a human with roadmap context knows code is scaffolding; triage the dependency graph, not each item in isolation; a finding rejected once can be valid later when context changes.
- **Workshop teaching opportunity:** Why AI "dead code" findings need human triage against the roadmap — same code, opposite decision, because human context shifted.

---

#### 53. ddg-yagni-fallback — 300-line provider abstraction cut to ~50 lines
- **Friction-type:** F4 (over-engineering / wrong altitude, caught by reviewers)
- **Source traces:** A3 `docs/lessons/operations.md:38-69`, `LESSONS_LEARNED.md:13`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 7
- **Date/source:** see traces
- **Tool used:** three reviewers independently said YAGNI
- **Project/topic:** Tavily + DuckDuckGo search fallback
- **Original goal:** Add a search-provider fallback.
- **Context provided:** Original plan: `SearchProvider` Protocol, `MultiProvider`, 5 new files, a CLI flag.
- **Files/tools used:** `search.py`
- **Agent actions:** Designed a full provider abstraction (~6x the code for no added capability).
- **What worked:** ~50 lines, one function (`_search_tavily`) in existing `search.py`, zero new files; env vars over CLI flags; prompt instruction over query-decomposition code for comparison bias.
- **What failed or caused friction:** The abstraction was 6x the code for the same functionality.
- **Human correction or steering:** "When three reviewers say too complex, believe them."
- **Final outcome:** Minimal implementation shipped.
- **Reusable lesson:** Prefer the simplest solution; ask "can prompt engineering solve this?" before building abstractions.
- **Workshop teaching opportunity:** Canonical YAGNI example with a concrete 300→50 line reduction.

---

#### 54. preferred-domains-yagni-noop — Plan kills a brainstorm feature that was arithmetically a no-op
- **Friction-type:** F4 (forward-compatible stub / no-op feature removed)
- **Source traces:** A5 `docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md:26,37-39,431,498,511`, brainstorm `docs/brainstorms/2026-03-06-swappable-context-profiles-brainstorm.md:35-37`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 24
- **Date/source:** 2026-03-06
- **Tool used:** not clear (plan deepened with 10 research agents)
- **Project/topic:** `preferred_domains` "+0.5 relevance boost" context-profile field
- **Original goal:** Brainstorm proposed `preferred_domains` giving a +0.5 nudge on the 1-5 relevance scale.
- **Context provided:** Scores are `int` (1-5); `relevance_cutoff` is `int` (3 at that time).
- **Agent actions:** During planning, did the arithmetic: 2 + 0.5 = 2.5 still drops; 3 already passes → the boost is a no-op. Tested +1 boost, parallel cutoff, tiebreaker — all too aggressive or no gate effect. An earlier plan revision had even parsed/stored the field "for forward compatibility."
- **What worked:** Tracing the proposed feature through the actual integer gate exposed zero behavioral effect.
- **What failed or caused friction:** The brainstorm's "soft boost" sounded reasonable but couldn't move an integer gate.
- **Human correction or steering:** Removed `preferred_domains` entirely: "storing a no-op field confuses future readers (YAGNI). Adding a field to a frozen dataclass later costs ~2 lines." `verify_first: true` flagged it as the risk to resolve before work.
- **Final outcome:** Field dropped.
- **Reusable lesson:** Verify a proposed feature actually changes behavior in the real type system before building or even stubbing it.
- **Workshop teaching opportunity:** The single best "the plan caught what the brainstorm missed" example — forward-compatible stubs as anti-YAGNI.

---

#### 55. fixed-sleep-rate-limit — Unconditional inter-batch sleeps wasted 6–9s/run
- **Friction-type:** F4 (over-defensive premature optimization); A1 records the related search-pass delay
- **Source traces:** A3 `docs/solutions/performance-issues/adaptive-batch-backoff.md:16-91` (commit `0c44f95`); A1 `todos/030-complete-p2-remove-search-pass-delay.md:14`
- **Corroboration:** 1 (A1's search-pass-delay is a sibling defensive-sleep finding)
- **Cycle/arc:** Cycle 17 (Session 4); Cycle 18 for the search-pass delay
- **Date/source:** 2026-02-15, commit `0c44f95`
- **Tool used:** not clear
- **Project/topic:** Batch API throttling; inter-pass sleeps
- **Original goal:** Avoid Anthropic 429s / rate limiting.
- **Context provided:** `relevance.py` (3.0s) and `summarize.py` (1.5s) slept between every batch unconditionally; a separate 1.0-1.5s sleep ran between search passes.
- **Files/tools used:** `relevance.py`, `summarize.py`, `agent.py`
- **Agent actions:** Fixed defensive sleeps fired even when no rate limiting occurred; query refinement already provided natural spacing.
- **What worked:** Adaptive backoff — only sleep after an actual 429 (boolean flag); remove the redundant search-pass delay.
- **What failed or caused friction:** ~9s dead time on deep runs for hypothetical safety; hardcoded sleeps outlive their justification.
- **Human correction or steering:** React to actual 429s; worst case = old behavior.
- **Final outcome:** ~9s saved on deep runs.
- **Reusable lesson:** React to actual 429s; don't pay guaranteed latency for hypothetical rate limits; re-examine defensive sleeps when surrounding architecture changes.
- **Workshop teaching opportunity:** "Magic sleep" smell — latency hidden in good intentions; measure before optimizing defensively.

---

#### 56. over-engineered-spend-json — daily_spend.json over-engineered
- **Friction-type:** F4 (over-engineering / YAGNI on a data schema)
- **Source traces:** A1 `todos/060-complete-p2-simplify-daily-spend-json.md:14`; A3 `docs/solutions/architecture/skill-only-features-background-research.md:68-98` (7 fields→3)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 22
- **Date/source:** see traces
- **Tool used:** not clear (Simplicity reviewer)
- **Project/topic:** spend file stores full per-query array duplicating `queue.md`
- **Original goal:** Flatten to 3 fields ("how much have I spent today?").
- **Context provided:** "duplicates information already tracked in `reports/queue.md`."
- **Files/tools used:** `.claude/skills/research-queue.md`
- **Agent actions:** Identified data duplication + unbounded growth (7-field schema for a 3-field question).
- **What worked:** Reduced a schema to its actual question.
- **What failed or caused friction:** The agent designed a richer data model than the use case needs.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Store the answer you need, not a general-purpose log; agents over-model by default.
- **Workshop teaching opportunity:** YAGNI applied to data schemas, not just code.

---

#### 57. memory-blowup-full-file-read — Context preview read entire files into memory
- **Friction-type:** F4 (over-broad implementation / inefficiency)
- **Source traces:** A4 commits `84ec074`, `7f6073e` (note: single-file shortcut later partly reverted in `60a185a`)
- **Corroboration:** 1
- **Cycle/arc:** Cycle ~23
- **Date/source:** see traces
- **Tool used:** Claude (Opus 4.6 trailer)
- **Project/topic:** Context listing / auto-detect latency
- **Original goal:** Preview available context files and auto-detect the right one.
- **Context provided:** commit bodies.
- **Files/tools used:** `context.py`, `agent.py`, `modes.py`
- **Agent actions:** `84ec074` reads line-by-line and stops after `_PREVIEW_LINES`; `7f6073e` switches auto-detect to Haiku (~0.3s vs ~2s) and skips the LLM call when only one context file exists.
- **What worked:** Bounded reads + cheaper model + single-file shortcut.
- **What failed or caused friction:** Original code read full files for a preview and used Sonnet for a trivial classification. The single-file shortcut was later partly *reverted* in `60a185a` to prevent injecting PFE context into unrelated queries — a correctness-vs-latency tradeoff reversal.
- **Human correction or steering:** (inferred) Performance review findings.
- **Final outcome:** Faster, bounded context handling.
- **Reusable lesson:** Right-size the model and I/O to the task; but beware a latency shortcut can reintroduce a correctness bug.
- **Workshop teaching opportunity:** Optimization and correctness can pull in opposite directions.

---

#### 58. research-plan-approach-b-not-c — Inception plan picks the moderate architecture over the impressive one
- **Friction-type:** F4 (premature over-engineering at project inception)
- **Source traces:** A5 `RESEARCH_PLAN.md:101-205,195-197`
- **Corroboration:** 1
- **Cycle/arc:** project origin
- **Date/source:** `RESEARCH_PLAN.md`
- **Tool used:** not clear
- **Project/topic:** Initial architecture choice for the whole research agent
- **Original goal:** Build a research agent; three approaches sketched (A Simple / B Moderate / C Robust multi-agent).
- **Context provided:** Survey of GPT-Researcher, LangChain Open Deep Research, STORM; documented failure modes (hallucinated sources, token explosion, parallel-report disjointedness).
- **Agent actions:** Recommended Approach B: "Approach A is too fragile ... Approach C is premature — query decomposition and multi-agent coordination add complexity that isn't needed until you've validated the core use case."
- **What worked:** Anchoring the choice to "validate the core use case first" and a clear upgrade path to C.
- **What failed or caused friction:** The robust multi-agent design (C) is the most impressive and easiest to over-invest in early.
- **Human correction or steering:** Start moderate; the project grew toward C-like capabilities cycle by cycle once validated.
- **Reusable lesson:** Pick the architecture that validates the core value with a clear upgrade path; don't pay multi-agent complexity before you have a working single-pass pipeline.
- **Workshop teaching opportunity:** Inception-stage altitude control — "could build" vs "should build now."

---

#### 59. mcp-coarse-four-tools — Fewer coarse MCP tools beat granular pipeline exposure
- **Friction-type:** F4 (granularity over-engineering)
- **Source traces:** A5 `docs/brainstorms/2026-02-28-cycle-19-mcp-server-brainstorm.md:18-38,122-123`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 19
- **Date/source:** 2026-02-28
- **Tool used:** FastMCP / Claude Code clients (stated)
- **Project/topic:** MCP server wrapping the research agent
- **Original goal:** The Cycle 19 source doc recommended separate `search`/`fetch`/`synthesize` tools.
- **Context provided:** GPT-Researcher's gptr-mcp uses 5 coarse tools; tool-selection accuracy "degrades past ~30 tools."
- **Agent actions:** Chose 4 coarse intent-based tools; rejected hybrid (coarse + escape hatches) as "complexity and testing surface for edge cases we don't have yet. YAGNI."
- **What worked:** Designing for the *calling LLM's* tool-selection accuracy, not pipeline completeness.
- **What failed or caused friction:** The upstream doc pushed granular tools; following it would expose orchestration the agent should own.
- **Human correction or steering:** "The calling LLM shouldn't orchestrate the pipeline — that's the agent's job."
- **Final outcome:** 4 coarse tools (`run_research`, `list_reports`, `get_report`, `list_modes`).
- **Reusable lesson:** Expose intents, not internals; fewer well-chosen tools improve downstream agent reliability.
- **Workshop teaching opportunity:** Designing tool surfaces for an AI consumer rather than a human power user.

---

#### 60. query-iteration-one-pass-no-loop — Capping an iterative feature so it can't spiral
- **Friction-type:** F4 (unbounded loop / cost over-engineering)
- **Source traces:** A5 `docs/brainstorms/2026-03-01-query-iteration-brainstorm.md:24-31,105`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 20
- **Date/source:** 2026-03-01
- **Tool used:** not clear
- **Project/topic:** Query refinement depth
- **Original goal:** "Iterate on the question itself."
- **Context provided:** Cost/runtime predictability concerns.
- **Agent actions:** Chose "One pass, not a loop" and rejected "Loop-until-satisfied refinement — too expensive and unpredictable."
- **What worked:** Bounding an inherently recursive idea to a single deterministic pass.
- **What failed or caused friction:** "Iterate" naturally invites a loop that can blow up cost/latency.
- **Human correction or steering:** "The agent won't spiral into recursive self-improvement."
- **Final outcome:** `query_iterations=1` for standard/deep, 0 for quick.
- **Reusable lesson:** Replace "iterate until good" with a fixed small number of passes unless you have a hard convergence criterion.
- **Workshop teaching opportunity:** How to bound agentic loops at design time instead of hoping they terminate.

---

#### 61. tiered-routing-tier1-only — Resisting the bigger cost-savings tier without data
- **Friction-type:** F4 (risk-blind optimization scope creep)
- **Source traces:** A5 `docs/brainstorms/2026-03-02-tiered-model-routing-brainstorm.md:42-61,80`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 21
- **Date/source:** 2026-03-02
- **Tool used:** not clear
- **Project/topic:** Route cheap Haiku to planning, keep Sonnet for quality-critical steps
- **Original goal:** Cut cost by using a cheaper model where safe.
- **Context provided:** Tier 2 (relevance scoring on Haiku) offered ~20-25% savings but "Haiku mis-scoring could pollute reports."
- **Agent actions:** Limited to Tier 1 (low-volume planning calls, ~6-8% savings); deferred Tier 2 pending A/B; Tier 3 (summarization) "indefinitely."
- **What worked:** Tying optimization scope to where quality risk is provably low.
- **What failed or caused friction:** The larger savings tier was tempting but unvalidated; a cheaper model on a *judgment* gate could silently degrade every report.
- **Human correction or steering:** "the risk of mis-scored sources polluting reports outweighs the cost benefit without A/B validation data."
- **Final outcome:** `planning_model` field; verification required before shipping.
- **Reusable lesson:** Cost optimizations on judgment/gating steps need measurement first; optimize the safe, low-volume steps first.
- **Workshop teaching opportunity:** Separating "cheap and safe" from "cheap and risky" model-routing.

---

#### 62. self-enhancing-tier-scope — Capping an ambitious self-improving agent at safe tiers
- **Friction-type:** F4 (scope creep / risky altitude)
- **Source traces:** A5 `docs/brainstorms/2026-02-20-self-enhancing-agent-brainstorm.md:43-46,86,226-231,254-255`
- **Corroboration:** 1
- **Cycle/arc:** future cycle (self-enhancing agent)
- **Date/source:** 2026-02-20
- **Tool used:** not clear
- **Project/topic:** Agent that critiques its own reports and adapts future prompts
- **Original goal:** A self-improving feedback loop — tempts toward parameter auto-tuning and self-rewriting (Tiers 3-4).
- **Context provided:** OpenAI self-evolving agents cookbook, DSPy, SAFLA; risk that self-modification is "irreversible without version control on prompts."
- **Agent actions:** Scoped to Tier 1 (critique log) + Tier 2 (prompt-only adaptation); explicitly listed Tier 3/4 as "NOT building yet."
- **What worked:** Bounding the blast radius to ephemeral prompt adaptations that "don't persist in code."
- **What failed or caused friction:** The exciting version (self-rewriting agent) carries a sharply higher risk profile.
- **Human correction or steering:** "Tier 1 + Tier 2 close the feedback loop with zero self-modification risk."
- **Final outcome:** Prompt-only adaptive loop with mode-collapse detection.
- **Reusable lesson:** With self-modifying systems, ship the reversible tier first and gate the irreversible tiers behind benchmarks.
- **Workshop teaching opportunity:** How to let an agent be ambitious in vision while constraining it to a safe, reversible first increment.

---

#### 63. p3-triage-skip-fstring-churn — Refusing a "correct" lint fix because it's churn
- **Friction-type:** F4 (low-value change / churn-for-churn's-sake)
- **Source traces:** A5 `docs/brainstorms/2026-02-23-p3-triage-brainstorm.md:104-109,146`
- **Corroboration:** 1
- **Cycle/arc:** P3 triage, 2026-02-23
- **Date/source:** 2026-02-23
- **Tool used:** not clear (findings from a multi-agent review)
- **Project/topic:** Triaging 11 P3 review findings into do-now / do-later / skip
- **Original goal:** Finding #24 (f-string in logger calls) was flagged by 3 review agents as a real Python convention.
- **Context provided:** ~40 calls across 10 files; lazy-logging benefit only at disabled log levels; the tool logs at WARNING in production.
- **Agent actions:** Skipped #24 — "high churn, negligible benefit, debatable best practice"; noted f-strings are more readable.
- **What worked:** Weighing reviewer consensus against actual runtime impact and diff size.
- **What failed or caused friction:** Three agents agreeing created pressure to "just fix it."
- **Human correction or steering:** "touching 40+ lines ... for negligible runtime benefit in a CLI tool felt like churn for churn's sake."
- **Final outcome:** Skipped; 5 genuine quick wins batched into one ~60-line session. (Note: the same f-string finding *did* recur and get partially fixed later — see episode 112.)
- **Reusable lesson:** "Multiple reviewers flagged it" is not the same as "worth doing"; weigh churn vs. benefit, and don't fix style the team disagrees with.
- **Workshop teaching opportunity:** Pushing back on AI/reviewer consensus when cost/benefit doesn't hold.

---

#### 64. p2-triage-remove-query-domain — Deleting dead machinery instead of refactoring it
- **Friction-type:** F4 (YAGNI machinery with no consumer)
- **Source traces:** A5 `docs/brainstorms/2026-02-28-p2-triage-critique-synthesize-brainstorm.md:14-36,59-60`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 23 (triage)
- **Date/source:** 2026-02-28
- **Tool used:** not clear
- **Project/topic:** `query_domain` field on `CritiqueResult`
- **Original goal:** A `query_domain` field extracted, stored, validated, slugged into filenames — but "never read back for filtering."
- **Context provided:** ~20 lines of machinery for a feature that doesn't exist; review said "remove, add later if needed."
- **Agent actions:** Chose full removal over a deprecation path; "pointless for a personal CLI tool."
- **What worked:** Recognizing the field as a forward-looking stub whose consumer never materialized.
- **What failed or caused friction:** Risk that removing the filename slug breaks `load_critique_history`'s glob (flagged "Least confident").
- **Human correction or steering:** Remove entirely; verify the glob doesn't depend on the slug during planning.
- **Final outcome:** `query_domain` deleted across dataclass, prompts, parser, validation, filename logic.
- **Reusable lesson:** Delete speculative machinery rather than maintaining or deprecating it; re-adding a field later is cheap.
- **Workshop teaching opportunity:** Recognizing and removing "we'll use it eventually" code that nothing consumes.

---

#### 65. cycle25-bundle-trivial-housekeeping — Bundling sub-20-line items to avoid loop overhead
- **Friction-type:** F4 (process over-engineering / altitude — full loop on trivial change)
- **Source traces:** A5 `docs/brainstorms/2026-03-08-cycle-25-housekeeping-brainstorm.md:30-37,41-46`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 25
- **Date/source:** 2026-03-08
- **Tool used:** not clear
- **Project/topic:** MCP parity lint script + public `parse_context_file()` wrapper
- **Original goal:** Two tiny deferred items carried across multiple cycles.
- **Context provided:** The full brainstorm→plan→review loop is overkill for ~30-50-line mechanical refactors.
- **Agent actions:** Bundled both into one housekeeping cycle; chose a standalone script over a pytest plugin / ruff rule / CI-only as "the simplest thing that works."
- **What worked:** Matching process weight to change size.
- **What failed or caused friction:** Running a heavyweight loop per trivial item wastes compound cycles.
- **Human correction or steering:** "Bundling them into one housekeeping cycle avoids the overhead of separate brainstorm/plan/review loops for trivial changes."
- **Final outcome:** Both shipped; the lint script's enforcement path was later found inadequate (episode 45).
- **Reusable lesson:** Right-size the process to the change; bundle trivial items, but still gate each one.
- **Workshop teaching opportunity:** When NOT to run the full ceremony — process altitude matching.

---

#### 66. cycle32-config-py-new-file — A new file because every existing home is semantically wrong
- **Friction-type:** F4 (avoiding expedient-but-wrong placement)
- **Source traces:** A5 `docs/brainstorms/2026-05-03-cycle-32-hygiene-bundle-brainstorm.md:42-47,49-65,136-148`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 32
- **Date/source:** 2026-05-03
- **Tool used:** not clear
- **Project/topic:** Relocating `META_DIR` out of the heavy `agent.py` orchestrator
- **Original goal:** Stop importing a path constant from a heavy module (mcp_server even had an apologetic comment).
- **Context provided:** Every existing module (modes/errors) is the wrong semantic domain for a path constant.
- **Agent actions:** Created a new `config.py` (<10 lines); also explicitly kept `ANTHROPIC_ERRORS` consolidation *out* of `skeptic.py`/`synthesize.py` because their per-type logging is intentional.
- **What worked:** Choosing semantic correctness over expediency; recognizing where NOT to apply the consolidation.
- **What failed or caused friction:** Adding a file feels heavier than reusing one, creating pressure toward the wrong home.
- **Human correction or steering:** "Putting it in an existing file would be expedient but wrong."
- **Final outcome:** `config.py` for shared constants; per-type exception handling preserved.
- **Reusable lesson:** A new small file is the right call when no existing module owns the concept; a global consolidation should spare sites with intentional per-case behavior.
- **Workshop teaching opportunity:** Two steering moves in one — correct placement, and knowing the exceptions to your own refactor.

---

#### 67. ten-steps-ahead-merge-not-pivot — Folding a grand vision into the existing roadmap
- **Friction-type:** F4 (vision scope creep vs. foundation discipline)
- **Source traces:** A5 `docs/brainstorms/2026-04-21-ten-steps-ahead-brainstorm.md:97-120`
- **Corroboration:** 1
- **Cycle/arc:** strategic brief, 2026-04-21
- **Date/source:** 2026-04-21
- **Tool used:** not clear
- **Project/topic:** "10 steps ahead of Deep Research Max" — multi-agent swarm, evidence graphs, native viz, streaming
- **Original goal:** A 10-item ambitious feature vision to leapfrog a competitor.
- **Context provided:** The existing dependency-ordered entropy roadmap; many vision items depend on roadmap plumbing.
- **Agent actions:** Verdict "MERGE — the roadmap is the foundation, the vision is the ceiling"; mapped each of the 10 concepts to existing roadmap seeds vs. genuinely new ground.
- **What worked:** Recognizing the vision items are prerequisites-gated ("can't build a multi-agent swarm on a pipeline that doesn't enforce skeptic findings").
- **What failed or caused friction:** A grand vision tempts abandoning the unglamorous roadmap.
- **Human correction or steering:** Merge rather than pivot; finish the plumbing before building the house.
- **Final outcome:** Vision reframed as the ceiling above the current roadmap.
- **Reusable lesson:** Map ambitious ideas onto your dependency graph; most "next big things" are blocked on foundational work you've already scoped.
- **Workshop teaching opportunity:** Steering an excited agent from "let's pivot" back to "finish the foundation that makes the vision possible."

---

#### 68. diversity-gate-pure-count — Refusing the reputation-list slippery slope
- **Friction-type:** F4 (scope creep into an open-ended maintained list)
- **Source traces:** A5 `docs/brainstorms/2026-04-21-cycle-30-summarization-context-preservation-brainstorm.md:31-34,69,75`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 30
- **Date/source:** 2026-04-21
- **Tool used:** not clear
- **Project/topic:** Source diversity gate (require N unique domains or downgrade)
- **Original goal:** Ensure reports aren't built from one domain.
- **Context provided:** "domain reputation scoring is a C33+ concern if ever needed."
- **Agent actions:** Considered a "trusted domains" exception list ("Wikipedia alone is fine") and rejected it as a slippery slope.
- **What worked:** Framing the gate honestly: "did we look at more than one perspective?"
- **What failed or caused friction:** The exception list is intuitively appealing and would create unbounded maintenance.
- **Human correction or steering:** "No, pure count (YAGNI)."
- **Final outcome:** Pure unique-domain count, min 2/3/4 by mode, downgrade-only.
- **Reusable lesson:** A simple count that's honest about what it measures beats a "smarter" rule that requires perpetual curation.
- **Workshop teaching opportunity:** Spotting the moment a feature would commit you to an ever-growing config list.

---

#### 69. snippet-tier-field-placement — Put the field where it's consumed, not where it's "complete"
- **Friction-type:** F4 (architectural over-completion / YAGNI)
- **Source traces:** A5 `docs/brainstorms/2026-04-05-cycle-28-relevance-cutoff-brainstorm.md:27-35,70-74`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 28
- **Date/source:** 2026-04-05
- **Tool used:** not clear
- **Project/topic:** `source_tier` field to cap thin "snippet" sources
- **Original goal:** Track whether content came from a real fetch vs. a search-snippet fallback.
- **Context provided:** Cycle 24's "no forward-compatible stubs" lesson; only the relevance scorer needs tier info today.
- **Agent actions:** Weighed `ExtractedContent` (deeper, "complete") vs. `Summary` (where consumed); chose `Summary`.
- **What worked:** "Adding it to `ExtractedContent` ... is more architecturally complete but violates YAGNI."
- **What failed or caused friction:** Flagged its own uncertainty: how does the tier get *set* during summarization without fragile text-prefix detection? Punted to plan.
- **Human correction or steering:** Explicit deferral of the unresolved mechanism to the plan phase.
- **Final outcome:** `source_tier` added to `Summary`; snippets capped at 3.
- **Reusable lesson:** Place data at the point of consumption; resolving "where does this value get set" can be a separate, later decision.
- **Workshop teaching opportunity:** Honest brainstorming that says "I haven't solved the hard half — plan will."

---

#### 70. quick-mode-retry-guard — Quick mode triggers the expensive coverage retry
- **Friction-type:** F4 (feature applies expensive path where it shouldn't)
- **Source traces:** A1 `todos/043-done-p1-quick-mode-coverage-retry-guard.md:14-20`, `agent.py:522-528`; A4 commit `fc8ca59`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 28
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `_evaluate_and_synthesize()` triggers coverage retry "regardless of mode"
- **Original goal:** Add a quick-mode bypass like every other expensive op has.
- **Context provided:** decompose, critique, skeptic all skip in quick mode; coverage retry "has no such guard."
- **Files/tools used:** `agent.py:522-528`
- **Agent actions:** Compared the new retry against the established quick-mode-bypass pattern.
- **What worked:** Pattern-consistency catch.
- **What failed or caused friction:** Quick mode (designed for ~$0.12/4 sources) silently incurred extra cost+latency.
- **Human correction or steering:** Accepted (p1).
- **Final outcome:** done.
- **Reusable lesson:** When a "speed tier" exists, every new expensive stage must opt into its bypass; absence is a bug.
- **Workshop teaching opportunity:** Mode/tier invariants as a review checklist item.

---

#### 71. private-attr-public-api — Public API reached into underscore-prefixed internals
- **Friction-type:** F4 (wrong altitude — encapsulation leak)
- **Source traces:** A4 commit `4463f94`, `agent.py`, `__init__.py`, `tests/test_public_api.py`; A1 `todos/072-pending-p2-private-attribute-access-public-api.md:14` (done)
- **Corroboration:** 2
- **Cycle/arc:** Cycle ~23 / 25
- **Date/source:** see traces
- **Tool used:** Claude (Opus 4.6 trailer)
- **Project/topic:** Public API surface (`agent.py`, `__init__.py`)
- **Original goal:** Expose source count and gate decision to API consumers.
- **Context provided:** Public API reads `agent._last_source_count` (private).
- **Files/tools used:** `agent.py`, `__init__.py`, `tests/test_public_api.py`
- **Agent actions:** Added read-only `last_source_count` / `last_gate_decision` properties so the API stops reading `_`-prefixed attributes.
- **What worked:** Property accessors.
- **What failed or caused friction:** Original public API accessed private internals.
- **Human correction or steering:** (inferred) Review finding.
- **Final outcome:** Clean public surface.
- **Reusable lesson:** If the public layer reads private fields, promote them to properties.
- **Workshop teaching opportunity:** Encapsulation drift that AI introduces when "just exposing one more value."

---

#### 72. debug-log-noise — 7 identical debug logs of a frozen value
- **Friction-type:** F4 (over-instrumentation: noise, not signal)
- **Source traces:** A1 `todos/114-pending-p2-consolidate-debug-log-lines.md:14-16` (done), `agent.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle ~31 (planning-model routing)
- **Date/source:** see traces
- **Tool used:** not clear (Simplicity reviewer)
- **Project/topic:** 7 `logger.debug("Planning: <fn> -> %s", planning_model)` lines logging the same frozen field
- **Original goal:** Replace with one summary log at run start.
- **Context provided:** "Logging the same constant 7 times is noise, not signal"; two back-to-back logs at the same timestamp.
- **Files/tools used:** `agent.py`
- **Agent actions:** Recognized a frozen-dataclass field can't change between call sites.
- **What worked:** Used immutability to prove the logs are redundant.
- **What failed or caused friction:** Defensive over-logging added ~6 LOC of pure noise.
- **Human correction or steering:** Accepted.
- **Final outcome:** done.
- **Reusable lesson:** Don't log an unchanging value repeatedly; more logging ≠ more observability.
- **Workshop teaching opportunity:** Observability anti-pattern — instrumentation as noise.

---

#### 73. background-research-approach-a — Choosing the simplest of three architectures for delivery
- **Friction-type:** F4 (over-engineering — two-system hybrid for v1)
- **Source traces:** A5 `docs/brainstorms/2026-02-25-background-research-agents-brainstorm.md:31-49,103-107`
- **Corroboration:** 1
- **Cycle/arc:** background research agents, 2026-02-25
- **Date/source:** 2026-02-25
- **Tool used:** Claude Code (skill + `run_in_background` Task agents) — stated
- **Project/topic:** Queue research queries to run in the background during other work
- **Original goal:** Background research; three approaches (queue-file+skill / standalone Python runner / hybrid).
- **Context provided:** ADHD-friendly "results must find you" requirement; existing CLI + auto-save + Claude Code background agents.
- **Agent actions:** Picked Approach A (queue file + skill, no new Python). Rejected B ("results don't find you") and C ("two systems to build for v1 is over-engineering").
- **What worked:** Selecting on the *delivery* constraint (notifications find you) rather than raw capability.
- **What failed or caused friction:** The more capable standalone runner was tempting but didn't serve the user need.
- **Human correction or steering:** "If in-session background research works well, the offline runner can be added later without changing anything."
- **Final outcome:** Markdown queue file + `/research:queue` skill orchestrating the existing CLI.
- **Reusable lesson:** Choose the architecture that satisfies the real constraint (delivery UX), and defer the more capable one until proven necessary.
- **Workshop teaching opportunity:** Briefing matters — stating "results must find me" steered the AI away from the impressive-but-wrong option.

---

#### 74. temperature-three-not-four-fields — YAGNI on a fourth temperature knob
- **Friction-type:** F4 (over-engineering / premature config surface)
- **Source traces:** A5 `docs/brainstorms/2026-04-05-cycle-27-input-validation-brainstorm.md:223-229,310`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 27
- **Date/source:** 2026-04-05
- **Tool used:** not clear
- **Project/topic:** Per-task temperature controls on `ResearchMode`
- **Original goal:** Map ~13 LLM call sites onto temperature categories; the table revealed 4 natural categories but the roadmap listed only 3 fields.
- **Context provided:** Epistemic calibration study (temperature affects style not epistemics); the Cycle 21 `planning_model` precedent.
- **Agent actions:** Considered a 4th `adversarial_temperature` field, then folded skeptic+critique into `synthesis_temperature`.
- **What worked:** Recognizing skeptic and synthesis "both benefit from creative exploration," so one field serves both.
- **What failed or caused friction:** The category/field mismatch tempted a wider config surface than needed.
- **Human correction or steering:** "Option A with 3 fields ... If we later need to separate skeptic, we add a field then (YAGNI)."
- **Final outcome:** 3 temperature fields threaded to 16 call sites.
- **Reusable lesson:** Don't add a configuration dimension because a table looks asymmetric — add it when a real need splits the cases.
- **Workshop teaching opportunity:** "The data has 4 buckets" vs "the user needs 4 controls."

---

### F5 — Silent failure caught by a side-channel check (not by an error)

---

#### 75. retry-rescores-existing — Coverage retry re-scored already-scored sources
- **Friction-type:** F5 (silent redundant work); A3/A4 also tag F6/F1 (wasted API calls)
- **Source traces:** A1 `todos/046-pending-p2-redundant-re-evaluation.md:14-16` (done), `agent.py:492-500`; A3 `docs/solutions/performance-issues/redundant-retry-evaluation-and-code-deduplication.md:41-91,167-177` (commit `a8c4ae2`); A4 commits `a8c4ae2` (#046), `1d60c4d` (#045/#047), `fc8ca59` (#043/#044)
- **Corroboration:** 3
- **Cycle/arc:** Cycle 18 review (also tracked as Cycle 28)
- **Date/source:** 2026-02-25, commit `a8c4ae2`
- **Tool used:** not clear (code review)
- **Project/topic:** Coverage-gap retry path
- **Original goal:** Add sources after a coverage gap, then merge.
- **Context provided:** `_try_coverage_retry` passed `existing + new` summaries to `evaluate_sources`; "~30 redundant calls, ~$0.06 waste and ~15 seconds extra latency."
- **Files/tools used:** `agent.py`, `relevance.py`, `coverage.py`, `modes.py`, `tests/test_agent.py`
- **Agent actions:** Re-sent already-scored sources to the LLM, wasting calls and discarding accurate prior scores; also ran retry searches sequentially; quick mode wrongly ran the expensive retry.
- **What worked:** Score only new summaries; merge evaluations arithmetically; re-derive the decision from mode thresholds; parallelize retry searches; mode-scoped config.
- **What failed or caused friction:** "Gather more and re-run the whole evaluation" became a perf bug as retry matured; left an inline decision-logic duplication (documented remaining risk).
- **Human correction or steering:** Fixed; test rewritten to exercise the merge path.
- **Final outcome:** No re-scoring; efficient, mode-aware retry; decision-logic duplication flagged for future `_make_decision()` extraction.
- **Reusable lesson:** Incremental evaluation beats re-running; score only the delta, not the union; retry/merge must respect mode budgets.
- **Workshop teaching opportunity:** How an innocent early assumption silently becomes a cost bug as the system grows.

---

#### 76. tavily-built-not-active — Tavily built but silently fell back to DuckDuckGo for cycles
- **Friction-type:** F5 (silent degradation — feature built but never activated)
- **Source traces:** A3 `docs/lessons/operations.md:70-101`, `LESSONS_LEARNED.md:15`; A4 commit `7b3c7f8`, lesson `84ff163`
- **Corroboration:** 2
- **Cycle/arc:** Cycle 8–9
- **Date/source:** see traces
- **Tool used:** `--verbose` instrumentation; local side-channel test
- **Project/topic:** Tavily search integration (`search.py`, `fetch.py`)
- **Original goal:** Use Tavily for higher-quality search/content; improve low-quality reports.
- **Context provided:** Tavily code existed since Cycle 7 but `TAVILY_API_KEY` was never in `.env`; every run silently used DuckDuckGo. Initially attributed bad output to site-level bot blocking / relevance.
- **Files/tools used:** `search.py`, `fetch.py`, `.env`, `--verbose`
- **Agent actions:** Graceful fallback hid that the integration was inactive; tested `include_raw_content` locally and discovered the real provider in use.
- **What worked:** A local side-channel test revealed the actual provider; `--verbose` exposed the bottleneck (fetch, not relevance); `include_raw_content="markdown"` lifted 1/8→4/8 pages with content at zero extra cost.
- **What failed or caused friction:** "nothing threw an error... we attributed that to site-level bot blocking, not to using the wrong search provider entirely."
- **Human correction or steering:** "When a downstream stage appears broken, check if an upstream stage is starving it of input"; verify integrations are *active*, not just built; log when fallbacks activate.
- **Final outcome:** Tavily activated; instrumentation added.
- **Reusable lesson:** Silent fallbacks hide root causes — a "working" pipeline with degraded output is the hardest bug class; verify *which* code path actually ran, not just that no error was raised.
- **Workshop teaching opportunity:** The danger of graceful degradation hiding that a feature never ran.

---

#### 77. failed-context-silent-drop — FAILED context load silently treated as "no context"
- **Friction-type:** F5 (error state collapses into a benign-looking state)
- **Source traces:** A1 `todos/073-pending-p2-failed-context-silent-drop.md:14` (done), `context.py`, `context_result.py`; A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:83-87`, `context.py:98-100`
- **Corroboration:** 2
- **Cycle/arc:** Background Research Agents / Cycle 25
- **Date/source:** see traces
- **Tool used:** not clear (architecture-strategist sub-agent)
- **Project/topic:** `load_full_context()` failure handling
- **Original goal:** Load an optional context file.
- **Context provided:** `ContextResult.__bool__` returns False for both FAILED and NOT_CONFIGURED.
- **Files/tools used:** `research_agent/context.py`, `context_result.py`
- **Agent actions:** On `OSError`, `load_full_context()` returns FAILED, which is `__bool__`-false and thus indistinguishable from NOT_CONFIGURED — a permissions error becomes a silent "no context."
- **What worked:** Check `result.status == ContextStatus.FAILED` and log a visible warning.
- **What failed or caused friction:** A real failure produces no user-visible signal.
- **Human correction or steering:** Surface failures explicitly.
- **Final outcome:** P2; done.
- **Reusable lesson:** Don't let an error state and an "absent" state collapse into the same boolean; the user must tell "broken" from "not configured."
- **Workshop teaching opportunity:** Sentinel/truthiness design — overloaded falsy states hide failures.

---

#### 78. replace-all-corrupts-test-names — `replace_all` on a substring silently drops tests
- **Friction-type:** F5 (silent failure caught by a side-channel check)
- **Source traces:** A3 `LESSONS_LEARNED.md:19`, `docs/lessons/patterns-index.md:88-89`, `docs/lessons/operations.md:162-163`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 12
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** Refactor consolidating duplicate `_sanitize` helpers
- **Original goal:** Rename a function/identifier across the codebase via `replace_all`.
- **Context provided:** Cycle 12 "quick wins" — shared sanitize extraction.
- **Files/tools used:** test files, `sanitize.py` (inferred)
- **Agent actions:** Ran `replace_all` on the substring `_sanitize`, which also matched inside `test_sanitize`, corrupting test names to drop the `test_` prefix.
- **What worked:** Comparing collected test count against the documented count surfaced the silent drop.
- **What failed or caused friction:** Renamed test functions no longer matched pytest's `test_` collection — they silently stopped running. No error raised.
- **Human correction or steering:** "always run tests immediately" and "compare collected test count against documented count after refactoring."
- **Final outcome:** Corruption caught; rule established.
- **Reusable lesson:** Substring find-and-replace corrupts identifiers it partially matches. After any rename refactor, assert the test count is unchanged.
- **Workshop teaching opportunity:** A side-channel check (a count invariant) catching a failure that produces zero errors — "verify the work, don't trust it ran."

---

#### 79. auto-save-test-asserts-nothing — Auto-save test patches the writer but never asserts it
- **Friction-type:** F5 (test that runs but verifies nothing)
- **Source traces:** A2 `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md:11-16,50`, `docs/fixes/cycle-19-mcp-server/batch2.md:8-10`; A1 `todos/092-done-p2-auto-save-test-assert-gap.md:14`, `test_agent.py`
- **Corroboration:** 2
- **Cycle/arc:** Cycle 19, 26
- **Date/source:** see traces; fix commit `d68c72c`
- **Tool used:** Claude Code sub-agent (kieran-python-reviewer); A1 "Testing reviewer"
- **Project/topic:** MCP / standard-mode auto-save path
- **Original goal:** Auto-save reports.
- **Context provided:** Plan Session-3 feed-forward risk: "Whether test coverage is sufficient for the auto-save path."
- **Files/tools used:** `tests/test_mcp_server.py`, `test_agent.py`
- **Agent actions:** The test patches `atomic_write` but never asserts it was called with correct arguments — confirming the exact feed-forward risk; only verifies the metadata string contains the filename.
- **What worked:** The plan's own flagged risk pointed the reviewer at the gap.
- **What failed or caused friction:** A mock without an assertion provides false coverage confidence.
- **Human correction or steering:** Added `mock_write.assert_called_once_with(save_path, "# Saved Report")`.
- **Final outcome:** P2 closed in `d68c72c`.
- **Reusable lesson:** Patching a dependency is only half the test; without an assertion on the call, the test can't fail when the behavior breaks.
- **Workshop teaching opportunity:** Feed-forward in action — a risk flagged during work becomes a targeted review finding; "tests that pass but prove nothing."

---

#### 80. nonatomic-cli-write-marks-complete — Non-atomic CLI write lets a corrupt report be marked Completed
- **Friction-type:** F5 (silent corruption passing an existence check)
- **Source traces:** A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:70-74`, `cli.py:350`; A1 `todos/067-pending-p2-non-atomic-cli-file-writes.md:14` (done), `cli.py`, `safe_io.py`; A4 commit `92d2978` (atomic_write)
- **Corroboration:** 2
- **Cycle/arc:** Background Research Agents / Cycle 25
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (data-integrity-guardian)
- **Project/topic:** CLI `-o` output path
- **Original goal:** Write reports to a user-specified file.
- **Context provided:** The background queue skill marks items Completed based on file existence; `safe_io.atomic_write()` already exists.
- **Files/tools used:** `cli.py:350`, `safe_io.py`
- **Agent actions:** CLI uses non-atomic `Path.write_text()`; a partial file from an interrupted background agent passes the existence check and gets marked Completed with a corrupted report.
- **What worked:** Replace with `atomic_write(output_path, report)`.
- **What failed or caused friction:** The codebase had `atomic_write()` but this path didn't use it.
- **Human correction or steering:** Use the existing safe primitive.
- **Final outcome:** P2; done.
- **Reusable lesson:** Existence-based "done" checks require atomic writes; a crash mid-write yields a corrupt artifact that downstream treats as success; check whether a safe internal primitive already exists.
- **Workshop teaching opportunity:** Cross-layer reasoning — a single non-atomic write becomes a silent-corruption bug only when you consider the orchestrating workflow.

---

#### 81. self-critique-invisible — Self-critique works but is invisible to CLI/agent consumers
- **Friction-type:** F5 (silent action — results written but never surfaced)
- **Source traces:** A2 `docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md:18-35,254`, `agent.py:126-157`, `cli.py`, `context.py:228-285`
- **Corroboration:** 1
- **Cycle/arc:** Self-Enhancing Agent
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (agent-native-reviewer)
- **Project/topic:** Self-critique observability
- **Original goal:** Score report quality and feed it back into future runs.
- **Context provided:** Project principle that capabilities should be agent-accessible.
- **Files/tools used:** `agent.py`, `cli.py`, `context.py`
- **Agent actions:** Critique runs only as a hidden side effect, prints nothing, has no CLI invoke path, and history has no read path — "Classic 'silent action' anti-pattern."
- **What worked:** The agent-native lens identified an observability cluster (highest-impact theme) pure-correctness reviewers missed.
- **What failed or caused friction:** A working internal feature with no external surface is "arguably incomplete."
- **Human correction or steering:** Add `--critique`, one-line stdout summary, and `--critique-history`.
- **Final outcome:** Three P1s + two P2s; fixed (and this fix later made finding #13 moot — see episode 123).
- **Reusable lesson:** "It works" is not "it's usable"; silent successful actions are a defect for agent-operated tools.
- **Workshop teaching opportunity:** Observability as a first-class requirement when an agent is the operator.

---

#### 82. error-message-info-leakage — Sensitive info leaks via error text / partial path redaction
- **Friction-type:** F5 (sensitive info leaks via a side channel — error text)
- **Source traces:** A1 `todos/062-complete-p3-error-reason-leakage.md:14`, `todos/090-done-p2-path-stripping-regex-gaps.md:14`; A4 commit `6ca586c` (path regex broadened, finding 090)
- **Corroboration:** 1 (A4 records the same path-regex broadening)
- **Cycle/arc:** Cycle 22 (skill) and Cycle 26 (MCP)
- **Date/source:** see traces
- **Tool used:** not clear (Security sentinel)
- **Project/topic:** stderr recorded into queue file; MCP error path-redaction regex only strips `/Users/` & `/home/`
- **Original goal:** Redact sensitive substrings from surfaced error text.
- **Context provided:** "could contain API key prefixes, file paths, or internal URLs from stack traces."
- **Files/tools used:** `.claude/skills/research-queue.md`, MCP error path, `mcp_server.py`
- **Agent actions:** Found two leak channels; 090 enumerated the OS paths the regex misses (`/opt`, `/var`, `/app`, `/tmp`).
- **What worked:** Concrete enumeration of unredacted prefixes; broadened regex with URL-preserving negative lookbehind.
- **What failed or caused friction:** Partial redaction (allowlist of 2 prefixes) gives false confidence.
- **Human correction or steering:** Accepted (062 p3, 090 p2).
- **Final outcome:** complete/done.
- **Reusable lesson:** Redaction by enumerating "bad" prefixes is fragile; prefer denylist-of-secrets or whole-message scrubbing.
- **Workshop teaching opportunity:** Error messages are an exfiltration channel; partial regex redaction is a trap.

---

#### 83. mcp-critique-not-saved — MCP critique returns data but never persists
- **Friction-type:** F5 (silent gap: agent critiques vanish, invisible to history)
- **Source traces:** A1 `todos/135-pending-p2-critique-report-mcp-save-gap.md:14` (resolved), `mcp_server.py`, `cli.py:272-273`; A3 `docs/solutions/feature-implementation/novelty-decomposition-mcp-critique-history.md:30-89`
- **Corroboration:** 2
- **Cycle/arc:** Cycle 31
- **Date/source:** 2026-04-23
- **Tool used:** not clear (Agent-Native Reviewer); 7-agent review
- **Project/topic:** MCP `critique_report` vs CLI persistence
- **Original goal:** Persist critiques so `get_critique_history` sees them; full CLI↔MCP parity.
- **Context provided:** MCP `critique_report` returned the same data as the CLI but never called `save_critique()`; "Pre-existing gap... now more visible because `get_critique_history` was added."
- **Files/tools used:** `mcp_server.py`, `cli.py`, `decompose.py`, `modes.py`, `agent.py`, `results.py`
- **Agent actions:** Building `get_critique_history` exposed that agent critiques were never persisted; parity lint checks tool *existence*, not matching *side effects*.
- **What worked:** Add `save_critique()`; machine-enforce a comment coupling (magic `3`/`MAX_SUB_QUERIES`) with a cross-module invariant test.
- **What failed or caused friction:** Agent-initiated critiques silently didn't persist — a broken feedback loop; "frozen dataclass field = 6-file sync tax."
- **Human correction or steering:** All P2s resolved.
- **Final outcome:** Side-effect parity; comment couplings enforced by tests.
- **Reusable lesson:** Adding a "read" tool often reveals a missing "write" on the partner path; parity means side effects (writes/state), not just return values.
- **Workshop teaching opportunity:** Why feedback loops fail silently when one direction isn't wired; the limit of automated lint vs semantic parity.

---

#### 84. test-helper-accidental-compliance — Diversity-gate test passed by luck of the fixtures
- **Friction-type:** F5 (a test passed for the wrong reason)
- **Source traces:** A3 `docs/solutions/feature-implementation/summarization-context-preservation-diversity-truncation-abstention.md:16-23,134-138`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 30
- **Date/source:** 2026-04-21
- **Tool used:** not clear; Codex review caught the MCP-parity gap
- **Project/topic:** Domain-diversity gate
- **Original goal:** Require N unique domains among survivors.
- **Context provided:** `_make_summaries()` generates `example1.com`, `example2.com`… — unique by construction.
- **Files/tools used:** `relevance.py`, `summarize.py`, `modes.py`, `synthesize.py`
- **Agent actions:** Added a post-decision downgrade gate (FULL→SHORT only).
- **What worked:** Realizing the retry test passed because the *helper* generated unique domains, not because the gate was exercised; auditing test helpers.
- **What failed or caused friction:** A green test gave false assurance the gate worked.
- **Human correction or steering:** Audit rule added: check test *helpers*, not just assertions.
- **Final outcome:** Gate correctly tested; `min_domains` MCP parity added.
- **Reusable lesson:** When adding a gate, audit test helpers for accidental compliance — green ≠ exercised.
- **Workshop teaching opportunity:** Tests can pass for the wrong reason; verifying *why* a test passes is part of trusting AI-written tests.

---

#### 85. ci-only-proves-listtools — Required CI check proves less than the dependency range claims
- **Friction-type:** F5 (green check that doesn't cover the risk it implies)
- **Source traces:** A2 `docs/reviews/2026-03-10-cycle-26-code-review-findings.md:17-21`, `.github/workflows/mcp-lint.yml:1-17`, `scripts/lint_mcp_parity.py:10-22`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26
- **Date/source:** 2026-03-10
- **Tool used:** not clear (no tool token in filename)
- **Project/topic:** MCP parity CI workflow
- **Original goal:** Make CI prevent MCP tool/instruction drift.
- **Context provided:** The widened FastMCP range from the sibling blocker (episode 93).
- **Files/tools used:** `.github/workflows/mcp-lint.yml`, `scripts/lint_mcp_parity.py`
- **Agent actions:** The required check only runs `mcp.list_tools()` parity — so it can stay green while a different FastMCP 3.x change breaks MCP client calls, `ToolError`, or transport behavior.
- **What worked:** Separated "what the check proves" from "what the package now claims to support."
- **What failed or caused friction:** A required status check creates false confidence about a broader compatibility surface it never exercises.
- **Human correction or steering:** Narrow the dependency range (preferred), or add compatibility coverage beyond `list_tools()`.
- **Final outcome:** P3 advisory paired with the version-cap blocker.
- **Reusable lesson:** A required CI gate implies a guarantee; make sure the gate actually tests the surface its presence reassures people about.
- **Workshop teaching opportunity:** "Green checkmark theater" — the scope of a required check should match the confidence it creates.

---

#### 86. context-cache-shared-state — Module-level context cache: no thread safety / test pollution
- **Friction-type:** F5 (shared mutable global; test pollution + thread risk); A1/A2 also tag F6
- **Source traces:** A1 `todos/066-pending-p2-context-cache-module-level.md:14` (done), `context.py:23`; A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:47-51,253`, `context.py:23`; A3 `docs/solutions/architecture/codebase-hygiene-audit-driven-fixes.md` (thread-safe Tavily cache, 29H)
- **Corroboration:** 2 (plus the 29H Tavily-cache analogue in A3)
- **Cycle/arc:** Background Research Agents / Cycle 25 / Cycle 29H
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agents (6 converged)
- **Project/topic:** `_context_cache` module-level dict
- **Original goal:** Cache parsed context to avoid re-reading files.
- **Context provided:** Public API supports async/concurrent use.
- **Files/tools used:** `research_agent/context.py:23`
- **Agent actions:** Six agents flagged a module-level dict with no thread safety, no size bound, no eviction; `clear_context_cache()` cross-contaminates and tests rely on `tmp_path` uniqueness to avoid pollution.
- **What worked:** Move the cache to the `ResearchAgent` instance or use `functools.lru_cache(maxsize=32)`; (29H) thread-safe Tavily cache with a `Lock` + autouse reset fixtures.
- **What failed or caused friction:** Global mutable state breaks isolation in concurrent and test contexts.
- **Human correction or steering:** Instance-scope or bounded caches.
- **Final outcome:** P2.
- **Reusable lesson:** Module-level caches are a recurring trap in code that later becomes concurrent; instance-scope or bounded caches avoid cross-contamination; they need locks, bounds, and per-test reset fixtures.
- **Workshop teaching opportunity:** When 6 independent reviewers agree, the finding is structural; global caches as a hidden source of flaky tests.

---

#### 87. mock-data-triggers-quality-gate — New quality gate silently broke six existing tests
- **Friction-type:** F5 (silent side-effect of a new gate, caught by tests)
- **Source traces:** A4 HANDOFF history, `search.py`, multiple test files
- **Corroboration:** 1
- **Cycle/arc:** Cycle 29
- **Date/source:** HANDOFF "least confident" note
- **Tool used:** Claude (Opus trailers)
- **Project/topic:** Score-aware refinement noun-phrase fallback (`search.py`)
- **Original goal:** Add a noun-phrase fallback when snippet/summary quality is too low.
- **Context provided:** HANDOFF note.
- **Files/tools used:** `search.py`, multiple test files
- **Agent actions:** Added a quality gate (avg snippet <50 chars / avg summary <100 chars → noun-phrase fallback); had to lengthen mock data in six existing tests so they wouldn't trip the new gate.
- **What worked:** Reused the existing `STOP_WORDS` set instead of duplicating one.
- **What failed or caused friction:** The new gate had an invisible blast radius — short mock strings silently route into the fallback path, a trap for future test authors.
- **Human correction or steering:** HANDOFF documents the new constraint.
- **Final outcome:** Tests updated; constraint documented.
- **Reusable lesson:** A new threshold gate changes behavior for any input under the threshold, including tests — document the constraint.
- **Workshop teaching opportunity:** New guards have hidden blast radius; "all tests pass" can mask a changed code path.

---

#### 88. context-profile-funnel-leak — Blocked domains leaked into `refine_query` before the funnel
- **Friction-type:** F5 (filter applied at the funnel, but unfiltered data used upstream)
- **Source traces:** A2 `docs/reviews/2026-03-06-cycle-24-codex-findings.md:16-22`, `docs/reviews/2026-03-06-cycle-24-codex-review-handoff.md`, `agent.py:587,951`, commit range `201b012..e3667f7`; A3 `docs/solutions/feature-implementation/swappable-context-profiles.md:54-123,128-134`
- **Corroboration:** 1 (A2 and A3 are the same Cycle-24 Codex incident)
- **Cycle/arc:** Cycle 24 (Swappable Context Profiles)
- **Date/source:** 2026-03-06
- **Tool used:** Codex
- **Project/topic:** Per-context blocked-domain filtering
- **Original goal:** Filter blocked domains once at the single funnel `_fetch_extract_summarize()` so blocked sources never influence a report.
- **Context provided:** Codex review handoff listed 5 specific risks; results enter via 7+ paths; `_research_with_refinement()` builds `seen_urls`/`snippets` *before* the funnel; 920 tests passed.
- **Files/tools used:** `agent.py`, `context.py`, `search.py`, `synthesize.py`, `cli.py`
- **Agent actions:** Consolidated filtering to one funnel, but quick/standard mode built `seen_urls`/`snippets` from `pass1_results` *before* that filter — so a blocked domain could still shape `refine_query()`.
- **What worked:** Cross-module data-flow tracing surfaced a leak all 920 passing tests missed; add early filtering in `_research_with_refinement()`/`_research_deep()` as defense-in-depth; dot-boundary match; tone injected OUTSIDE `<instructions>`; per-field YAML try/except.
- **What failed or caused friction:** "the final report can be steered by a source the user explicitly blocked"; single-funnel was necessary but not sufficient; free-text tone double-sanitized until review caught it; `schema_path.parent` crash risk caught in plan deepening.
- **Human correction or steering:** Filter before `seen_urls`/`snippets` are built; trace ALL upstream consumers of the unfiltered data.
- **Final outcome:** P2 blocker fixed; all 4 review findings resolved.
- **Reusable lesson:** A correct filter in the wrong pipeline position is a silent leak; "single funnel" is necessary-not-sufficient — verify the filter sits upstream of *every* consumer.
- **Workshop teaching opportunity:** "All tests pass" ≠ "the data flow is correct" — flow bugs hide between modules that are each internally fine.

---

#### 89. schema-erd-not-enforced — ERD promised constraints the SQL migration didn't enforce (cross-project)
- **Friction-type:** F5 (silent: invalid data accepted, no runtime error)
- **Source traces:** A3 `docs/solutions/database-issues/schema-constraint-gaps-supabase.md:12-133`
- **Corroboration:** 1
- **Cycle/arc:** PF-Intel V1 (cross-project)
- **Date/source:** 2026-02-16
- **Tool used:** multi-agent review (9 agents, 92→38 findings)
- **Project/topic:** Supabase schema for PF-Intel
- **Original goal:** Implement `001_initial_schema.sql` matching the ERD.
- **Context provided:** ERD declared 1:1 relations, value ranges; migration compiled fine.
- **Files/tools used:** `pf-intel/supabase/migrations/001`, `002_schema_fixes.sql`
- **Agent actions:** Omitted UNIQUE on FK, CHECKs on enum/confidence/duration/file_size, and a storage UPDATE policy.
- **What worked:** Follow-up migration adding UNIQUE/CHECK/RLS; "sibling column" consistency rule.
- **What failed or caused friction:** Compiled, ran, silently allowed duplicate jobs, out-of-range confidence, negative sizes.
- **Human correction or steering:** 4-6 agents agreeing reliably flagged real gaps; single-agent finds were stylistic.
- **Final outcome:** Constraints enforced; schema checklist created.
- **Reusable lesson:** ERD cardinality/ranges don't auto-translate to SQL — verify each constraint; agent *consensus* predicts severity.
- **Workshop teaching opportunity:** "It compiled" ≠ "it's correct"; multi-agent agreement as a severity signal.

---

#### 90. insufficient-data-unsanitized — Fallback "insufficient data" response skipped sanitization
- **Friction-type:** F5 (silent gap on an error/edge path)
- **Source traces:** A4 commit `dff079b`, `relevance.py`, `agent.py`, `synthesize.py`, `modes.py`, `errors.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 6
- **Date/source:** commit `dff079b`
- **Tool used:** Claude (Opus 4.5 trailer)
- **Project/topic:** Relevance gate / insufficient-data path
- **Original goal:** Build the relevance gate and insufficient-data response.
- **Context provided:** Cycle 6 review fixes list.
- **Files/tools used:** `relevance.py`, `agent.py`, `synthesize.py`, `modes.py`, `errors.py`
- **Agent actions:** Among many Cycle-6 fixes: "Fix unsanitized content in `_fallback_insufficient_response`"; also converted relevance scoring to async, added a streaming disclaimer print, and `min_sources_short_report >= 1` validation.
- **What worked:** Sanitization applied on the fallback path.
- **What failed or caused friction:** The happy path was sanitized but the *fallback* response was not.
- **Human correction or steering:** (inferred) Cycle 6 review caught it.
- **Final outcome:** Edge path sanitized.
- **Reusable lesson:** Apply cross-cutting protections (sanitization) on every exit path, especially error/fallback branches.
- **Workshop teaching opportunity:** Agents secure the main path and forget the fallbacks.

---

#### 91. injection-regression-test-missing — Sanitization fix shipped without a regression test
- **Friction-type:** F5 (no test guards a security invariant — future regression risk)
- **Source traces:** A1 `todos/128-done-p2-missing-prompt-injection-regression-test.md:14`, `sanitize.py`, tests
- **Corroboration:** 1
- **Cycle/arc:** Cycle 27
- **Date/source:** see traces
- **Tool used:** not clear (Security)
- **Project/topic:** `html.unescape()` added to `sanitize_content()` to block pre-encoded XML boundary tags (`&lt;/research_context&gt;`)
- **Original goal:** Add a test that fails if the unescape-then-escape ordering breaks.
- **Context provided:** "If a future refactor breaks the unescape-then-escape ordering, no test would catch the regression."
- **Files/tools used:** `sanitize.py`, tests
- **Agent actions:** Identified an untested security invariant (the recurring sanitize bug from episode 1).
- **What worked:** Tied a missing test directly to the long-running sanitization saga; 4 entity-boundary regression tests added.
- **What failed or caused friction:** A security fix shipped without a guard test.
- **Human correction or steering:** Accepted.
- **Final outcome:** done.
- **Reusable lesson:** Every security fix needs a regression test naming the attack it blocks — especially for a bug that already recurred.
- **Workshop teaching opportunity:** Closing the loop on the sanitization saga with a test, not just a fix.

---

#### 92. rls-blocks-backend — RLS gates on auth.uid() but the AI pipeline has no JWT (cross-project)
- **Friction-type:** F5 (design gap that would silently block 9 of 13 backend operations)
- **Source traces:** A2 `docs/reviews/session-2-supabase/REVIEW-SUMMARY.md:18-22`, `001_initial_schema.sql:252-384,401-424`
- **Corroboration:** 1
- **Cycle/arc:** Session 2 (Supabase) — cross-project
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (agent-native-reviewer)
- **Project/topic:** PF-Intel — RLS vs. server-side pipeline
- **Original goal:** Secure data with row-level security.
- **Context provided:** AI pipeline (Whisper, Claude parsing, job updates) runs server-side in FastAPI with no auth JWT.
- **Files/tools used:** `pf-intel/supabase/migrations/001_initial_schema.sql`
- **Agent actions:** Every RLS/storage policy gates on `auth.uid()`, so the backend can't read audio, write transcripts, update job status, or insert entities (9/13 ops); the service_role bypass is "planned but nowhere documented."
- **What worked:** The reviewer reasoned about *who actually calls the database* (a no-JWT backend), not just whether policies are present.
- **What failed or caused friction:** Correct-looking RLS would block the core pipeline at runtime.
- **Human correction or steering:** Document the dual-access pattern (mobile = anon_key + RLS, backend = service_role bypass).
- **Final outcome:** P1.
- **Reusable lesson:** Access-control policies must account for *every* caller, including unauthenticated server processes.
- **Workshop teaching opportunity:** Threat/role modeling — "who is the principal?" for each code path.

---

### F6 — Other (consistency, duplication, architecture, process, reviewer dynamics)

---

#### 93. fastmcp-version-cap-walkback — FastMCP cap widened, then re-tightened on review (add→lose→re-find)
- **Friction-type:** F6 (decision decay / regression-of-a-fix); A2 tags the resurfacing F3
- **Source traces:** A2 `docs/reviews/2026-03-10-cycle-26-code-review-findings.md:11-15`, `2026-03-10-cycle-26-claude-code-review-findings.md:11`, `docs/fixes/cycle-19-mcp-server/batch3.md:23-25`, `cycle-19-mcp-server/REVIEW-SUMMARY.md:57`, `pyproject.toml:22`, `todos/099-done-p3-tighten-fastmcp-version.md:13-29`; A4 commits `e990902` (<4.0), `5fa7ea0` (>=3.0,<3.1), `96e3fe2` (C19 tighten); A1 `todos/035-complete-p3-dependencies-minimum-version-pins.md:14`, `todos/099-done-p3-tighten-fastmcp-version.md:14`
- **Corroboration:** 3
- **Cycle/arc:** Cycle 19 (tightened), Cycle 26 (regressed + re-tightened)
- **Date/source:** 2026-03-10; commits as above
- **Tool used:** Codex first, then Claude Code second review confirmed the fix; Claude authored the commits
- **Project/topic:** FastMCP dependency pin
- **Original goal:** Pin `fastmcp` to prevent silent breakage on a major bump.
- **Context provided:** Cycle 19 deliberately changed `>=2.0,<4.0` → `>=2.0,<3.0` (`96e3fe2`); the repo had tightened this pin once before; only `fastmcp 3.0.2` was validated.
- **Files/tools used:** `pyproject.toml`, `scripts/lint_mcp_parity.py`, `tests/test_mcp_server.py`
- **Agent actions:** The cap was later widened back to `<4.0` (`e990902`); every fresh install and the new required CI check would float to arbitrary future 3.x. Codex cross-referenced the repo's *own history* — this exact pin had been deliberately tightened in Cycle 19.
- **What worked:** Re-tighten to the deliberately tested 3.x line; Claude Code's second review confirmed `5fa7ea0` (`>=3.0,<3.1`).
- **What failed or caused friction:** A regression of a previously-fixed decision slipped back in; the passing 3.0.2 test suite masked it.
- **Human correction or steering:** Explicit "review blocker" reversed the loosening; grep your own todos/fixes before loosening a constraint.
- **Final outcome:** Narrow, tested version range; two-reviewer loop closed it.
- **Reusable lesson:** Dependency caps are decisions with history; widening one silently re-opens a previously-closed risk; a deliberate guard is only durable if future changes respect it — record the *why*.
- **Workshop teaching opportunity:** A full add→lose→re-find loop across two reviewers; institutional memory beats a reviewer that only sees the diff.

---

#### 94. stateful-agent-leaks-between-runs — Per-run state leaks across reused agent (recurring)
- **Friction-type:** F6 (state-management: per-run state leaks across reused agent); A4 tags F1
- **Source traces:** A1 `todos/009-complete-p2-mutable-instance-state.md:14`, `todos/056-pending-p2-state-mutation-research-async.md:14` (done), `todos/074-pending-p2-last-critique-not-reset.md:14` (done); A4 commits `c4716e0`, `dbd0b80`
- **Corroboration:** 2
- **Cycle/arc:** Cycles 17 → 25 (recurring); flexible-context fixes
- **Date/source:** see traces
- **Tool used:** Claude (Opus 4.6 trailer); not clear for todos
- **Project/topic:** Agent reusability / state hygiene (`agent.py`, `decompose.py`)
- **Original goal:** Allow the same agent instance to run multiple `research()` calls.
- **Context provided:** "Calling `research()` twice... produces different behavior on the second call"; "critique result from a previous run persisted on the agent instance"; "Six mutable run-state attributes are reset... but `_last_critique` is missing."
- **Files/tools used:** `agent.py`, `decompose.py`, `tests/test_decompose.py`
- **Agent actions:** `_research_async` mutated `self.context_path`/`self.no_context` without reset; `_last_critique` set but never cleared. `c4716e0` resets `_last_critique`; `dbd0b80` eliminates the `__no_context__` sentinel and `self`-mutation in auto-detect.
- **What worked:** Local variables instead of instance mutation; explicit reset.
- **What failed or caused friction:** Same class as the original temporal-coupling bug (episode 96); fixes were incomplete (one attr missed each time).
- **Human correction or steering:** Reset all per-run state at top of `_research_async`; prefer locals + explicit reset.
- **Final outcome:** Stateless-per-run agent; sentinel removed; done.
- **Reusable lesson:** "Reset all per-run state" is one rule with many fields; an incomplete reset list is a recurring bug source — consider a single reset method or a fresh instance per run; mutating `self` inside an orchestration method makes the object unsafe to reuse.
- **Workshop teaching opportunity:** Hidden state is the bug source agents most often introduce when "wiring things up" — a recurring-bug-class case study spanning Cycles 17→25.

---

#### 95. source-vs-chunk-relevance — Scoring chunks but deciding on sources
- **Friction-type:** F6 (architectural unit mismatch causing quality loss)
- **Source traces:** A3 `docs/solutions/logic-errors/source-level-relevance-aggregation.md:24-102`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 15
- **Date/source:** 2026-02-10
- **Tool used:** not clear; diagnosed with a custom script `diagnose_relevance.py`
- **Project/topic:** Relevance gate
- **Original goal:** Drop low-relevance content before synthesis.
- **Context provided:** Pages chunked into 5 → 5 independent scores; downstream `synthesize.py` already groups by URL.
- **Files/tools used:** `relevance.py`, `tests/test_relevance.py`, `diagnose_relevance.py`
- **Agent actions:** Gate filtered *per chunk*; boilerplate chunks (nav/footer) scored low and dropped relevant sources' other chunks.
- **What worked:** `_aggregate_by_source()` — group by URL, take max score; when a source passes, all chunks survive.
- **What failed or caused friction:** Unit of evaluation (chunk) ≠ unit of decision (source) → 11-41% chunk survival, thin reports.
- **Human correction or steering:** Diagnosed on 3 real deep-mode queries before fixing; +9 tests.
- **Final outcome:** Chunks reaching synthesizer doubled (31→62).
- **Reusable lesson:** Score the unit you decide on; if you must score finer, make aggregation explicit. Diagnose with real data, not fixtures.
- **Workshop teaching opportunity:** Measuring with real data before fixing, and aligning evaluation granularity with decision granularity.

---

#### 96. temporal-coupling-instance-state — Mutable instance state read in wrong order → fragility
- **Friction-type:** F6 (architecture/temporal-coupling fragility)
- **Source traces:** A1 `todos/009-complete-p2-mutable-instance-state.md:14` (set at 206-207, read in `_update_gap_states`/`_evaluate_and_synthesize`)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `_current_schema_result` / `_current_research_batch` set then read across methods in `ResearchAgent`
- **Original goal:** Remove temporal coupling: "if methods are called in wrong order, it silently uses stale/None state."
- **Context provided:** Set at lines 206-207, read later across methods.
- **Files/tools used:** `research_agent/agent.py`
- **Agent actions:** Offered Option A (pass through params) vs Option B (reset at start of each call).
- **What worked:** Named the failure mode (stale state on re-run).
- **What failed or caused friction:** Instance attributes used as cross-method scratch space.
- **Human correction or steering:** Accepted — temporal coupling creates fragile state management.
- **Final outcome:** complete.
- **Reusable lesson:** Don't store per-run scratch state on a reusable object without an explicit reset; prefer passing values through.
- **Workshop teaching opportunity:** Foreshadows episodes 18 and 94 — the "not reset between runs" bug class recurs across cycles.

---

#### 97. duplication-cleanup-cluster — DRY cleanups: budget pruning, disclaimers, test helpers, query validation
- **Friction-type:** F6 (duplication / DRY cleanup — grouped)
- **Source traces:** A1 `todos/006-complete-p2-duplicated-budget-pruning.md:14`, `todos/018-complete-p3-limited-disclaimer-duplication.md:14`, `todos/034-complete-p3-duplicated-test-sanitize-content.md:14`, `todos/048-pending-p2-query-validation-duplication.md:14` (done), `todos/052-pending-p3-overlap-threshold-constants.md:14` (done), `todos/053-pending-p3-tried-queries-duplication.md:14` (done); A3 `docs/solutions/performance-issues/redundant-retry-evaluation-and-code-deduplication.md:95-161` (commit `dccaa4a`)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17, 28/29
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** Duplicated budget-pruning, disclaimer template, `TestSanitizeContent` in 3 test files, `_validate_retry_queries` vs `_validate_sub_queries` + duplicated `_STOP_WORDS`, `tried_queries` block
- **Original goal:** Extract shared logic to a single source of truth.
- **Context provided:** Each cites exact duplicate line ranges; "The `_STOP_WORDS` set is also duplicated (as a frozenset and an inline set recreated per-call)"; slightly-different thresholds disguised the duplication initially.
- **Files/tools used:** `synthesize.py`, `coverage.py`, `decompose.py`, `agent.py`, new `query_validation.py`, test files
- **Agent actions:** Proposed helper extraction; `validate_query_list(...)` with keyword-only params; both callers became thin delegations (45→8/12 lines). All 88 existing tests passed unchanged.
- **What worked:** Mechanical, low-risk; output contract preserved.
- **What failed or caused friction:** Copy-paste drift; new pipeline stages tend to copy validation logic.
- **Human correction or steering:** All accepted.
- **Final outcome:** complete; single source of truth.
- **Reusable lesson:** "Same shape, different thresholds" = parameterize and extract, don't wait for the third copy; recognizing structural (not literal) duplication is a high-value review skill.
- **Workshop teaching opportunity:** The "long tail" of DRY cleanups review reliably produces, and recognizing structural duplication.

---

#### 98. duplicate-tavily-cache — Two Tavily client caches drift apart
- **Friction-type:** F6 (duplication causing two live clients)
- **Source traces:** A1 `todos/027-complete-p2-duplicate-tavily-client-cache.md:14`, `search.py`, `cascade.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** identical `_get_tavily_client()` in `search.py` and `cascade.py`
- **Original goal:** Single shared client; "Two separate TavilyClient instances exist."
- **Context provided:** Flagged by 4/6 review agents.
- **Files/tools used:** `search.py`, `cascade.py`
- **Agent actions:** Spotted duplicated globals + functions.
- **What worked:** High agent consensus (4/6).
- **What failed or caused friction:** Resource duplication and drift risk.
- **Human correction or steering:** Accepted (later made thread-safe in Cycle 29H).
- **Final outcome:** complete.
- **Reusable lesson:** Duplicated client/singleton setup is both a perf and a correctness smell.
- **Workshop teaching opportunity:** High-consensus findings (4/6 agents) are safe auto-accepts.

---

#### 99. async-blocking-in-event-loop — Sync file I/O and API calls block the event loop
- **Friction-type:** F6 (performance/correctness — sync work in async context)
- **Source traces:** A2 `docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md:52-56`, `batch3-data-integrity.md:28-32`, `agent.py:193,126-156`; A1 `todos/028-complete-p2-extract-all-blocks-event-loop.md:14`, `todos/029-complete-skeptic-sync-client.md:14`, `todos/031-complete-cascade-sequential-with-extraction.md:14`, `todos/103-complete-p2-sequential-mini-report-synthesis.md:14`, `todos/045-pending-p2-sequential-retry-searches.md:14`
- **Corroboration:** 1 (A1 records the broader async-perf cluster; A2 the self-enhancing instance)
- **Cycle/arc:** Self-Enhancing Agent; spans multiple cycles
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agents (performance-oracle + data-integrity-guardian converged)
- **Project/topic:** Async correctness across critique loading, extract_all, skeptic client, cascade, retry, mini-report
- **Original goal:** Load prior critiques / run independent work during an async research run.
- **Context provided:** Codebase uses `asyncio.to_thread` for blocking work; quantified savings per item (5-10s deep mode; "wastes 10-25s").
- **Files/tools used:** `agent.py`, `extract.py`, `skeptic.py`, `cascade.py`
- **Agent actions:** `load_critique_history` does ~20 blocking syscalls and `_run_critique` makes a synchronous 30s API call, both on the event loop; CPU-bound `extract_all` blocks; independent calls run serially.
- **What worked:** Wrap blocking work in `await asyncio.to_thread(...)`; use `AsyncAnthropic`/`gather`. Two independent agents converged on the same defect.
- **What failed or caused friction:** Blocking I/O in async code stalls concurrent work and causes timeouts.
- **Human correction or steering:** Respect the loop; any blocking syscall or sync SDK call needs `to_thread`.
- **Final outcome:** P2; fixed.
- **Reusable lesson:** "Independent + sequential = parallelizable" is the most reliable perf finding; new code inside an async method must respect the loop.
- **Workshop teaching opportunity:** A subtle correctness/perf trap unit tests rarely catch; convergence across two lenses raised confidence.

---

#### 100. model-string-scatter — Same model string defined in 4 modules
- **Friction-type:** F6 (config drift risk from organic growth)
- **Source traces:** A3 `docs/solutions/architecture/model-string-unification.md:14-87` (commit `9176aeb`)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17 (Session 6)
- **Date/source:** 2026-02-15, commit `9176aeb`
- **Tool used:** not clear
- **Project/topic:** Model configuration
- **Original goal:** Use one model across the pipeline.
- **Context provided:** `DECOMPOSITION_MODEL`, `REFINEMENT_MODEL`, `SCORING_MODEL`, `SKEPTIC_MODEL` all held the same value, nothing enforced it.
- **Files/tools used:** `modes.py` + 4 modules
- **Agent actions:** Each module defined its own constant as it was built.
- **What worked:** `model` field on the frozen `ResearchMode`, threaded as a parameter.
- **What failed or caused friction:** Updating the model meant editing 4+ files; a miss would silently use a different version.
- **Human correction or steering:** Removed all four constants.
- **Final outcome:** Single source of truth.
- **Reusable lesson:** Shared config belongs in a central frozen dataclass, not per-module constants.
- **Workshop teaching opportunity:** How "fine in isolation" local constants compound into coordination debt.

---

#### 101. none-conflation-status-modeling — `None`/boolean overloads hide "ran but empty" and "failed"
- **Friction-type:** F6 (overloaded status value hides a signal)
- **Source traces:** A3 `docs/solutions/architecture/gap-aware-research-loop.md:24-101` (None = "no config" vs "load failed"), `docs/solutions/architecture/parallel-async-synthesis-with-safety-barriers.md:284-352` (boolean success hid "ran but found nothing"); A1 `todos/107-complete-p2-overloaded-skipped-status.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17 (17A-17D), Cycle 20
- **Date/source:** 2026-02-15, 2026-03-02
- **Tool used:** multi-agent review (21 findings: 3 P1; later 14 issues: 2 P1)
- **Project/topic:** Gap-aware research loop; query-iteration status
- **Original goal:** Give the agent memory + safe state; report whether iteration enriched the report.
- **Context provided:** `load_full_context()` returned `None` for both "no file" and "read failed"; iteration could "succeed" but add nothing (all URLs duplicates); `iteration_status="skipped"` meant "never attempted" OR "ran but found nothing."
- **Files/tools used:** `context.py`, `agent.py`, `iterate.py`, `cli.py`, 8 new gap-loop modules
- **Agent actions:** Built a four-state `ContextResult`; a success boolean collapsed "added content" and "found nothing new"; "skipped" status conflated two outcomes.
- **What worked:** Four-value status (`skipped`/`completed`/`no_new_sources`/`error`); four-state result type; atomic writes; per-gap TTL.
- **What failed or caused friction:** Callers couldn't distinguish legitimate empty outcomes; silent degradation from None overloading.
- **Human correction or steering:** One enum value per distinguishable outcome; "ran but empty" is a legitimate state.
- **Final outcome:** One status value per real outcome.
- **Reusable lesson:** One enum value per distinguishable outcome; four-state result types over `None`; collapsing distinct outcomes into a boolean loses signal callers need.
- **Workshop teaching opportunity:** Status modeling — why `None`/boolean overloading hides bugs.

---

#### 102. print-in-library-code — CLI-first design printed and discarded all pipeline metadata
- **Friction-type:** F6 (agent-native API gap)
- **Source traces:** A3 `docs/solutions/architecture/agent-native-return-structured-data.md:24-138`
- **Corroboration:** 1
- **Cycle/arc:** not clear (planned)
- **Date/source:** 2026-02-13
- **Tool used:** not clear
- **Project/topic:** `research()` return contract
- **Original goal:** Return a research report.
- **Context provided:** Pipeline computed scores/decisions/timing but `print()`ed (~40 calls) then discarded them; returned bare `str`.
- **Files/tools used:** `agent.py`, `synthesize.py`, `__init__.py`
- **Agent actions:** Used `print()` as the progress channel and a string return; hid 13 composable modules.
- **What worked (planned):** `ResearchResult` dataclass, `on_progress`/`stream_callback`, export primitives.
- **What failed or caused friction:** Programmatic/agent callers got zero visibility; retrofitting is expensive.
- **Human correction or steering:** Design checklist proposed.
- **Final outcome:** not clear (doc is "Planned").
- **Reusable lesson:** Return structured data from day one; never `print()` in library code; export composable primitives.
- **Workshop teaching opportunity:** Building for agents vs humans — "if you print it and throw it away, future-agent needs it."

---

#### 103. codebase-hygiene-audit — 6-agent audit found 14 P2s + 1 real bug during dedup
- **Friction-type:** F6 (incomplete exception handling found while consolidating); tagged F5
- **Source traces:** A3 `docs/solutions/architecture/codebase-hygiene-audit-driven-fixes.md:1-84`; `errors.py`, `relevance.py`, `synthesize.py`, `sanitize.py`, `report_store.py`, `cascade.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 29H
- **Date/source:** 2026-04-07
- **Tool used:** 6 parallel specialized agents
- **Project/topic:** Codebase hygiene after 28 cycles
- **Original goal:** Pay down accumulated debt (type safety, exceptions, security).
- **Context provided:** 14 P2s, none individually urgent.
- **Files/tools used:** `errors.py`, `relevance.py`, `synthesize.py`, `sanitize.py`, `report_store.py`, `cascade.py`
- **Agent actions:** Consolidated 4 synthesis exception blocks into `_synthesis_errors(label)`.
- **What worked:** Dedup *uncovered* that `synthesize_mini_report` was missing 2 exception clauses — a real gap; `assert`→`RuntimeError` so SSRF pre-check survives `python -O`.
- **What failed or caused friction:** Thread-safe Tavily cache broke 2 test files (needed autouse reset fixtures); initial gate-rationale "suffix" approach was wrong, review caught it.
- **Human correction or steering:** 7 commits, 987→1040 tests, 14/14 resolved.
- **Final outcome:** Hygiene cycle; 1 latent bug fixed as a side effect.
- **Reusable lesson:** Audit-then-fix (parallel specialized agents) beats fix-while-building; consolidation surfaces hidden gaps; `assert` is stripped by `-O`.
- **Workshop teaching opportunity:** Periodic audit cycles and how refactoring-for-consistency exposes real bugs.

---

#### 104. stale-section-references — Magic "Section 11" / stale PFE strings after renumbering
- **Friction-type:** F6 (maintenance debt / intent-vs-implementation drift, no runtime error)
- **Source traces:** A3 `docs/solutions/logic-errors/stale-references-and-type-hint-fixes.md:15-58` (commit `a802b3d`); A1 `todos/078-done-p2-remove-legacy-pfe-fallbacks.md:14`, `todos/085-done-p2-stale-section-11-references.md:14`, `todos/086-done-p3-stale-test-name-section-11.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 20 / 24 (fixes 085-087)
- **Date/source:** 2026-02-28
- **Tool used:** not clear (flagged by review)
- **Project/topic:** Synthesis prompt/section numbering
- **Original goal:** Refactor final sections to start at constant `_DEFAULT_FINAL_START = 5`.
- **Context provided:** Section identifiers hardcoded as "Section 11" in prompts, comments, docstrings, a test name; PFE-specific "Competitive Implications"/"Positioning Advice" sections left in fallback branches.
- **Files/tools used:** `synthesize.py`, `critique.py`, `tests/test_synthesize.py`
- **Agent actions:** Refactored numbering but left "Section 11" strings; also a `dict[str, int]` hint not matching `dict[str, int | str]`.
- **What worked:** Replace position numbers with stable section *names*; correct the union hint; rename the test. 085 escalated to p2 because the stale text was *sent to the LLM*.
- **What failed or caused friction:** No test failures — but the LLM saw conflicting position references.
- **Human correction or steering:** Fixes 085/086/087; remaining root coupling (`_DEFAULT_FINAL_START`) tracked as todo 088.
- **Final outcome:** Prompts use names.
- **Reusable lesson:** Reference report sections by stable name, not position number; renames/decouples leave a trail of stale strings — especially dangerous when the stale text is in a prompt.
- **Workshop teaching opportunity:** Distinguishes harmless stale comments from prompt-affecting stale text; no-error ≠ no-problem for LLM prompts.

---

#### 105. frozen-mutable-dict / inconsistent-frozen — Frozen dataclass with a mutable dict; 5 dataclasses non-frozen
- **Friction-type:** F6 (immutability guarantee violated / consistency)
- **Source traces:** A1 `todos/005-complete-p2-mutable-gap-metadata.md:14`, `todos/032-complete-p2-inconsistent-frozen-dataclasses.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17/18
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `schema.py:39` `metadata: dict[str, str]` on frozen `Gap`; `SearchResult`/`FetchedPage`/`Summary`/`ExtractedContent`/`SkepticFinding` not frozen
- **Original goal:** Stop `gap.metadata["key"] = "value"` succeeding despite `frozen=True`; freeze value types to match convention.
- **Context provided:** "the field itself can't be reassigned, the dict is mutable"; "never mutated after construction."
- **Files/tools used:** `schema.py`, multiple model modules
- **Agent actions:** Flagged the shallow-immutability gap; inventoried convention violators.
- **What worked:** Correct understanding that `frozen` only blocks rebinding; convention-based inventory.
- **What failed or caused friction:** False sense of immutability; inconsistent discipline.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** `frozen=True` is shallow; mutable containers inside frozen dataclasses still mutate; conventions let reviewers do mechanical inventory passes.
- **Workshop teaching opportunity:** "The type system lied"; convention → automatable finding pipeline.

---

#### 106. cross-agent-consensus-severity — Cross-agent consensus and synthesis as a severity signal
- **Friction-type:** F6 (review-process insight)
- **Source traces:** A3 `docs/solutions/architecture/iterative-review-second-pass-patterns.md:168-212`
- **Corroboration:** 1
- **Cycle/arc:** not clear (second 9-agent review)
- **Date/source:** see traces
- **Tool used:** 9-agent review
- **Project/topic:** Multi-agent review triage
- **Original goal:** Prioritize findings.
- **Context provided:** Findings flagged by 3+ agents were always ≥P2; performance-oracle saw "redundant work," security-sentinel saw "architectural risk" for the same double-sanitization.
- **Files/tools used:** review summaries
- **Agent actions:** Each agent reported a partial view of the double-sanitization bug.
- **What worked:** Synthesizing the two views escalated it correctly to P1; weighting cross-agent consensus.
- **What failed or caused friction:** Single-agent findings tend to be P3 noise; severity is easy to under-rate per-agent.
- **Human correction or steering:** Triage rule adopted.
- **Reusable lesson:** Weight cross-agent consensus heavily; synthesize related-but-different findings — the combination often reveals higher severity.
- **Workshop teaching opportunity:** How to run and triage a multi-agent review — consensus as signal, synthesis over tallying.

---

#### 107. codex-records-negative-findings — Codex declines to elevate overstated prior claims
- **Friction-type:** F6 (reviewer correctly rejects/down-rates a finding)
- **Source traces:** A2 `docs/reviews/2026-03-11-codex-security-review.md:137-140,154-155`, `agent.py:62-94`, `mcp_server.py`
- **Corroboration:** 1
- **Cycle/arc:** Security review 2026-03-11
- **Date/source:** 2026-03-11
- **Tool used:** Codex
- **Project/topic:** `max_sources` and the programmatic `mcp` object
- **Original goal:** Validate or refute previously-claimed vulnerabilities.
- **Context provided:** Prior claims about "cost amplification through max_sources override" and `mcp` object exposure.
- **Files/tools used:** `agent.py`, `mcp_server.py`
- **Agent actions:** Codex found `max_sources` is exposed but "not actually applied by `ResearchAgent.__init__()`," making prior amplification claims "overstated"; declined to elevate the embeddable `mcp` object because the shipped console entrypoint enforces loopback-only binding.
- **What worked:** Codex resisted inflating severity; explicitly demoted stale/overstated findings.
- **What failed or caused friction:** Earlier framing treated these as security issues; current code did not support that.
- **Human correction or steering:** Reclassify as not-elevated.
- **Final outcome:** Both kept out of the findings list with rationale.
- **Reusable lesson:** Good review includes *negative* findings — recording what was checked and judged not-a-bug prevents stale claims from compounding.
- **Workshop teaching opportunity:** Calibration discipline; documenting rejected findings is a maturity signal.

---

#### 108. reviewer-false-positives-rejected — Fresh-context reviewer re-litigates settled decisions
- **Friction-type:** F6 (reviewer false positives, human rejects after cross-reference)
- **Source traces:** A2 `docs/reviews/2026-05-03-cycle-32-review-summary.md:33-43,72-78`, `modes.py`, `results.py`, `agent.py`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 32 (Hygiene Bundle)
- **Date/source:** 2026-05-03
- **Tool used:** Claude Code sub-agent (learnings-researcher) vs. review synthesizer
- **Project/topic:** `to_mode_info()` placement and `ANTHROPIC_ERRORS` adoption
- **Original goal:** Mechanical hygiene refactor.
- **Context provided:** Prior 7-agent deepening review that made the original decisions; commit messages documenting exclusions.
- **Files/tools used:** `modes.py`, `results.py`, `agent.py`
- **Agent actions:** learnings-researcher flagged three "violations"; the synthesizer assessed all three as non-issues — the Python reviewer had *recommended* the placement and the commit explicitly documented the exclusions ("False positive").
- **What worked:** The synthesizer cross-referenced findings against prior deliberation and commit messages before accepting them.
- **What failed or caused friction:** A fresh-context agent re-litigated decisions already made deliberately.
- **Human correction or steering:** "Chose to trust the prior deliberation because it had more context."
- **Final outcome:** Verdict PASS, 0 P0/P1.
- **Reusable lesson:** Fresh-context review generates false positives by re-questioning settled decisions; check findings against the record (commits, prior reviews) before acting.
- **Workshop teaching opportunity:** Fresh eyes vs. context — when a reviewer lacking history flags a deliberate choice as a bug.

---

#### 109. reviewer-severity-reconciliation — Synthesizer downgrades specialist "critical" gaps
- **Friction-type:** F6 (reviewer disagreement on severity, resolved)
- **Source traces:** A2 `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md:52-53,72` (agent-native P1→P2), `docs/reviews/p3-do-now-fixes/REVIEW-SUMMARY.md:9-12,16-24,99-101` (pattern-recognition P1→P2, comment-wrong-function-name)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 19, P3 "Do Now" Fixes
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agents (agent-native-reviewer / pattern-recognition vs. synthesizer)
- **Project/topic:** MCP tool/param parity; a sanitization-contract comment referencing a nonexistent function
- **Original goal:** Achieve CLI/MCP parity; document the "caller pre-sanitizes" contract.
- **Context provided:** Cycle 19 plan scoped exactly 5 tools; the comment at `relevance.py:122` referenced `score_and_filter_sources` instead of `evaluate_sources`.
- **Files/tools used:** `mcp_server.py`, `relevance.py:122`, `decompose.py`
- **Agent actions:** agent-native scored missing tools/params "critical"; pattern-recognition flagged the wrong-function-name comment P1. The synthesizer downgraded both to P2 ("real parity gaps but not regressions"; "a misleading comment is important but does not block merge"). The architecture agent's "re-add sanitization for defense-in-depth" suggestion was *rejected* because data-integrity proved double-sanitization is a bug.
- **What worked:** Severity reconciled against the cycle's documented scope and the ship decision; a plausible-but-wrong "add more safety" suggestion correctly rejected.
- **What failed or caused friction:** Specialist agents over-weight their own lens; a wrong comment about a security pre-condition risks a future dev skipping sanitization.
- **Human correction or steering:** Synthesizer sets final priority with documented rationale.
- **Final outcome:** P2s; comment fixed.
- **Reusable lesson:** Specialist reviewers optimize their own axis; a synthesis layer must reconcile severity against the actual ship decision and scope; "defense in depth" is the wrong argument when the extra layer is itself a corruption bug.
- **Workshop teaching opportunity:** Multi-agent review needs an arbiter — raw specialist severities aren't merge-ready until reconciled.

---

#### 110. reviewer-disagreement-developer-call — Two agents disagree → developer decides
- **Friction-type:** F6 (reviewer-vs-reviewer disagreement, left to developer)
- **Source traces:** A2 `docs/reviews/session-2-supabase/REVIEW-SUMMARY.md:194-196` (trigram), `:34-39` (TEXT-typed columns), `batch2-performance.md:46-50,58-62`; A1 `todos/021-complete-p3-inline-imports.md:14-16` (inline imports)
- **Corroboration:** 1
- **Cycle/arc:** Session 2 (Supabase, cross-project); Cycle 17 (inline imports)
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agents (code-simplicity vs. performance-oracle; architecture vs. PEP-8)
- **Project/topic:** GIN trigram indexes at small scale; TEXT vs typed columns for AI-extracted data; deferred imports
- **Original goal:** Enable fuzzy matching / store extracted fields / keep gap subsystem optional.
- **Context provided:** Tables at 50-200 rows; data is AI-extracted from messy voice transcripts; deferred imports keep the gap subsystem optional when `schema_path` is None.
- **Files/tools used:** `001_initial_schema.sql`, `agent.py`
- **Agent actions:** code-simplicity flagged trigram indexes + TEXT typing as premature; performance-oracle countered that at small scale overhead is immeasurable and TEXT is "correct for AI-extracted unstructured data."
- **What worked:** The synthesizer surfaced the disagreement explicitly rather than picking silently ("Disagreement between agents — developer's call").
- **What failed or caused friction:** Two valid lenses reach opposite conclusions; the minority often holds the domain constraint the majority overlooked.
- **Human correction or steering:** Left as a P3 developer decision with both rationales recorded; acceptance criteria allow either resolution.
- **Final outcome:** P3, unresolved-by-design.
- **Reusable lesson:** Not every finding has a single right answer; an honest review records genuine tradeoff disagreements instead of forcing a verdict; read the dissent — the minority may hold the domain constraint.
- **Workshop teaching opportunity:** YAGNI vs. cheap-optionality, and when to escalate to a human.

---

#### 111. process-no-plan-document — Work phase started with no plan + oversized commits
- **Friction-type:** F6 (process/workflow breakdown)
- **Source traces:** A2 `docs/reviews/self-enhancing-agent/batch3-git-history.md:28-32`, `REVIEW-SUMMARY.md:124-134`, commits `bad292e` (460 lines), `edc45f0` (334 lines)
- **Corroboration:** 1
- **Cycle/arc:** Self-Enhancing Agent
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (git-history-analyzer)
- **Project/topic:** compound-engineering workflow discipline
- **Original goal:** Follow Brainstorm → Plan → Work → Review → Compound.
- **Context provided:** A brainstorm existed but no `docs/plans/` document.
- **Files/tools used:** `docs/plans/` (absent); commits as above
- **Agent actions:** Flagged the missing plan and two commits 3-9x over the 50-100 line convention.
- **What worked:** A history/process reviewer caught workflow violations no code-correctness reviewer would.
- **What failed or caused friction:** Skipping the plan phase and oversized commits reduce reviewability and traceability.
- **Human correction or steering:** Document the gap; future features follow the full loop and split commits.
- **Final outcome:** P2 process findings.
- **Reusable lesson:** Process review is a distinct review type; "did we follow our own workflow" is worth a dedicated agent.
- **Workshop teaching opportunity:** Measuring agent process adherence (plan existence, commit size) as part of review.

---

#### 112. f-string-logging-recurs — f-string vs lazy logging recurs every cycle
- **Friction-type:** F6 (convention: eager f-string logging)
- **Source traces:** A1 `todos/013-complete-p3-logger-fstrings.md:14`, `todos/050-pending-p3-fstring-logging.md:14` (done), `todos/083-pending-p3-fstring-logging-context.md:14` (done), `todos/091-done-p2-fstring-logger-calls-agent.md:14`; A4 commit `6ca586c` (091, `%s` lazy formatting)
- **Corroboration:** 1
- **Cycle/arc:** spans Cycles 17 → 31
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** f-strings in `logger.*` calls instead of `%s` lazy formatting
- **Original goal:** Switch to `logger.x("msg %s", val)` lazy formatting.
- **Context provided:** "f-strings evaluate even when log level is disabled"; 091 rated p2 because it's mid-migration inconsistency.
- **Files/tools used:** `agent.py`, `coverage.py`, `context.py`, multiple modules
- **Agent actions:** Same finding re-raised in 4+ cycles as new modules appear.
- **What worked:** Consistent convention enforcement.
- **What failed or caused friction:** Each new module reintroduces f-string logging — a convention a linter should enforce, not a reviewer every cycle. (Contrast episode 63, where the same finding was *skipped* as churn when the diff was large.)
- **Human correction or steering:** Accepted every time.
- **Final outcome:** complete/done.
- **Reusable lesson:** A finding that recurs every cycle is a missing lint rule, not a review item — automate it.
- **Workshop teaching opportunity:** The clearest "automate this finding" signal in the corpus (4+ recurrences).

---

#### 113. magic-number-thresholds — Inline magic thresholds vs named constants (per new module)
- **Friction-type:** F6 (consistency / magic numbers)
- **Source traces:** A1 `todos/014-complete-p3-magic-number-priority-threshold.md:14`, `todos/052-pending-p3-overlap-threshold-constants.md:14` (done), `todos/110-complete-p3-named-constants-validation-thresholds.md:14`
- **Corroboration:** 1
- **Cycle/arc:** spans Cycles 18 → 30
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** hardcoded `6`, `0.8`/`0.7`, `min_words=3`/`max_words=10`/`0.6` inline
- **Original goal:** Extract named constants matching sibling modules.
- **Context provided:** magic `6` "will break silently if priorities change"; "`iterate.py` hardcodes... whereas `decompose.py` and `coverage.py` extract these."
- **Files/tools used:** `token_budget.py`, `coverage.py`, `iterate.py`
- **Agent actions:** Cross-module consistency comparison.
- **What worked:** Used sibling modules as the standard.
- **What failed or caused friction:** New modules reintroduce inline magic numbers.
- **Human correction or steering:** Accepted across the cluster.
- **Final outcome:** complete/done.
- **Reusable lesson:** Magic-number findings recur per new module; a lint or convention helps.
- **Workshop teaching opportunity:** The "p3 long tail" that recurs every cycle.

---

#### 114. type-hint-precision-cluster — Type-annotation precision findings (high-volume)
- **Friction-type:** F6 (type-hint accuracy / static-analysis hygiene)
- **Source traces:** A1 `todos/008-complete-p2-missing-type-annotations.md:14-17`, `todos/015-complete-p3-detect-stale-return-type.md:14`, `todos/016-complete-p3-select-batch-type-hint.md:14`, `todos/049-pending-p2-bare-list-type-hints.md:14-18`, `todos/082-done-p2-bare-list-type-hint.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17–22
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** missing/imprecise annotations (`SchemaResult | None`, `tuple[Gap, ...]` vs `list`, `Sequence[Gap]`, bare `list`)
- **Original goal:** Make hints match runtime convention and reality.
- **Context provided:** CLAUDE.md "Type hints on public function signatures."
- **Files/tools used:** `agent.py`, `staleness.py`, `synthesize.py`
- **Agent actions:** Recommended specific replacements (e.g., `Sequence[Gap]` "more Pythonic than union type").
- **What worked:** All accepted; consistent convention enforced.
- **What failed or caused friction:** Mild inconsistency, no runtime bug; high-volume.
- **Human correction or steering:** Accepted across the cluster.
- **Final outcome:** complete/done.
- **Reusable lesson:** Type-hint findings are easy wins but high-volume; a written convention keeps them consistent. (Contrast episode 17 where hints actively *lie* — a p1, not p3.)
- **Workshop teaching opportunity:** When to accept "stylistic" findings — they compound into static-analysis readiness.

---

#### 115. agent-native-parity-cluster — New config/feature ships dev-visible but agent-invisible
- **Friction-type:** F6 (agent-native parity: CLI features not reachable via API/MCP)
- **Source traces:** A1 `todos/068-pending-p2-api-parity-gaps.md:14` (done), `todos/080-done-p2-export-template-types.md:14`, `todos/060-pending-p2-high-level-api-context-param.md:14` (done), `todos/115-pending-p2-integration-test-planning-model-routing.md:14` (done), `todos/116-pending-p2-modeinfo-planning-model-visibility.md:14` (done), `todos/118-pending-p3-mcp-docstring-tiered-routing.md:14` (done), `todos/130-done-p3-temperature-invisible-in-list-modes.md:14`, `todos/131-done-p3-vague-query-hint-mcp-instructions.md:14`
- **Corroboration:** 1
- **Cycle/arc:** spans Cycle 25 → 31
- **Date/source:** see traces
- **Tool used:** not clear (Agent-Native Reviewer)
- **Project/topic:** missing exports, missing MCP tools, public API reading private attrs, model tier / temperature / vague-query behavior not surfaced to agents
- **Original goal:** Give agents the same capabilities/visibility as CLI users and developers reading `modes.py`.
- **Context provided:** "a developer reading `modes.py` can see these values, but an agent querying the MCP tool cannot"; "If someone reverts a call site... no test catches it."
- **Files/tools used:** `__init__.py`, `mcp_server.py`, `modes.py`, `cli.py`
- **Agent actions:** Systematic CLI-vs-API/MCP capability diff + routing regression-test asks for each new config dimension.
- **What worked:** A standing principle ("agents should see what developers see") generates consistent findings.
- **What failed or caused friction:** Every new config field ships dev-visible but agent-invisible; features keep shipping CLI-first.
- **Human correction or steering:** Mostly accepted.
- **Final outcome:** done.
- **Reusable lesson:** "Expose new config to agents + add a routing regression test" should be part of every config-adding feature's definition of done.
- **Workshop teaching opportunity:** Agent-native parity as a repeatable checklist, and routing tests that prevent silent reverts.

---

#### 116. auto-detect-new-feature-checklist — One new LLM feature, four friction types at once
- **Friction-type:** F1/F6 (unsanitized prompt + latency + brittle parsing + input normalization)
- **Source traces:** A1 `todos/057-pending-p2-unsanitized-auto-detect-prompt.md:14` (done), `todos/069-pending-p2-auto-detect-latency.md:14` (done), `todos/063-pending-p3-auto-detect-prompt-fragility.md:14` (done), `todos/097-done-p3-context-param-normalization.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 25
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `auto_detect_context()` — sends query + previews to LLM unsanitized (057); 1-3s Sonnet call per run (069); verbose replies fall through to None (063); `"None"`/`"null"` mis-handled (097)
- **Original goal:** Sanitize + XML-wrap the only unprotected prompt; reduce latency; robust parsing; normalize inputs.
- **Context provided:** 057: "the only LLM prompt that doesn't" use sanitize+XML; 069: "Uses full Sonnet for a trivial classification task."
- **Files/tools used:** `research_agent/context.py`, `mcp_server.py`
- **Agent actions:** Multi-angle critique of one new LLM feature (security, cost, robustness, input).
- **What worked:** Caught the lone prompt that skipped the project's defenses.
- **What failed or caused friction:** A convenience LLM classifier added an unsanitized prompt, per-run latency, and fragile output parsing all at once.
- **Human correction or steering:** All accepted.
- **Final outcome:** done.
- **Reusable lesson:** Every new LLM call inherits the whole checklist: sanitize, bound cost, parse defensively, normalize inputs.
- **Workshop teaching opportunity:** One feature, four friction types — a compact "review a new AI feature" exercise.

---

#### 117. new-llm-output-sanitize — LLM-output headings re-entering prompts (injection laundering)
- **Friction-type:** F6 (defense-in-depth: skip the sanitize boundary for "trusted" text)
- **Source traces:** A1 `todos/077-done-p2-sanitize-template-fields.md:14`, `todos/079-done-p2-validate-nonempty-sections.md:14`, `todos/102-complete-p2-unsanitized-headings-in-prompts.md:14`, `todos/112-complete-p3-section-title-sanitization.md:14`; A2 `docs/reviews/template-per-context/REVIEW-SUMMARY.md:40,97`; A3 `docs/solutions/logic-errors/defensive-yaml-frontmatter-parsing.md:39-41,97-108`
- **Corroboration:** 1 (A1, A2, A3 record the template-field-sanitization thread; folded here)
- **Cycle/arc:** Cycle 24, ~30
- **Date/source:** see traces
- **Tool used:** not clear (security-sentinel; learnings-researcher cross-ref)
- **Project/topic:** template `heading`/`description`/`context_usage` and report headings injected into prompts/markdown without `sanitize_content()`
- **Original goal:** Route LLM-derived and template text through the sanitization boundary.
- **Context provided:** 077 cites the documented "sanitize at the data boundary" pattern; 102: "a sophisticated attacker could craft web content that, after synthesis, produces headings containing prompt injection payloads"; 112 rates its own risk "very low."
- **Files/tools used:** `synthesize.py`, `context.py`
- **Agent actions:** Applied the three-layer defense even to LLM-output-derived and template text; learnings-researcher marked the documented boundary as bypassed.
- **What worked:** Reused a documented solution doc; honest low-severity tagging (112 p3).
- **What failed or caused friction:** "It's our own output" reasoning skipped sanitization; a new data source bypassed the established boundary.
- **Human correction or steering:** Sanitize every new field that flows into a prompt at the boundary.
- **Final outcome:** done.
- **Reusable lesson:** Every new data source into prompts is a new injection surface; treat LLM output that re-enters a prompt as untrusted (laundered injection); institutional patterns only help if new code is checked against them.
- **Workshop teaching opportunity:** "Injection laundering" — content → synthesis → heading → next prompt; the learnings-researcher role exists for exactly this.

---

#### 118. iteration-timeout-and-status — No global iteration timeout; overloaded "skipped" status
- **Friction-type:** F6 (reliability: missing overall timeout; ambiguous status value)
- **Source traces:** A1 `todos/104-complete-p2-no-iteration-timeout.md:14`, `todos/107-complete-p2-overloaded-skipped-status.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle ~30 (iteration feature)
- **Date/source:** see traces
- **Tool used:** not clear (Performance Oracle)
- **Project/topic:** chained timeouts (30s + 60s + 120s×3) with no overall cap; `iteration_status="skipped"` means two things
- **Original goal:** Add an iteration-phase timeout; disambiguate the status for API consumers.
- **Context provided:** "the total could reach ~8 minutes with no feedback"; "API consumers cannot distinguish these cases."
- **Files/tools used:** `agent.py` iteration pipeline, MCP response
- **Agent actions:** Summed per-stage timeouts to find the worst case; found a status enum conflating two outcomes.
- **What worked:** Composition-of-timeouts reasoning; consumer-perspective API critique.
- **What failed or caused friction:** Per-stage timeouts don't bound the whole; overloaded sentinel value.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Local timeouts don't imply a global bound — add an outer deadline; status values must map 1:1 to states.
- **Workshop teaching opportunity:** "The sum of safe parts can be unsafe"; agent-readable status design.

---

#### 119. token-cost-caps — Oversending draft input; unbounded mini-report output
- **Friction-type:** F6 (cost: oversending input, unbounded output)
- **Source traces:** A1 `todos/108-complete-p2-truncate-draft-for-refinement.md:14`, `todos/113-complete-p3-cap-iteration-max-tokens.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle ~30
- **Date/source:** see traces
- **Tool used:** not clear (Performance Oracle / cost)
- **Project/topic:** whole 30K-char draft sent to refined-query gen (108); `max_tokens//5`=1600 allows ~800-word mini-reports vs ~300 target (113)
- **Original goal:** Truncate input to what's needed; cap output to target length.
- **Context provided:** "`generate_followup_questions()` already truncates to 2000 chars."
- **Files/tools used:** `agent.py`, `iterate.py`, `synthesize.py`
- **Agent actions:** Compared against an existing truncation precedent.
- **What worked:** Pointed to an in-repo precedent (2000-char truncation).
- **What failed or caused friction:** Sending more context than the task needs.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Right-size both prompt input and output token caps to the task; reuse existing truncation patterns.
- **Workshop teaching opportunity:** Token-budget discipline as a first-class review concern.

---

#### 120. skill-guards-are-prose-not-code — Shell-escaping/budget guards are LLM prose, not enforced code
- **Friction-type:** F6 (security guard exists only as instructions to an LLM)
- **Source traces:** A2 `docs/reviews/background-research-agents/REVIEW-SUMMARY.md:107-129,280`, `batch2-security.md:16-31`, `.claude/skills/research-queue/SKILL.md:153-162,105-115`; A1 `todos/061-complete-p3-budget-validation.md:14` (budget validation)
- **Corroboration:** 1
- **Cycle/arc:** Background Research Agents
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (security-sentinel)
- **Project/topic:** Safely build shell commands and enforce a daily budget in a skill
- **Original goal:** Shell-escape and enforce a budget in a markdown skill.
- **Context provided:** Skills are markdown instructions interpreted by Claude Code, not executable code.
- **Files/tools used:** `SKILL.md`, `.claude/skills/research-queue.md`
- **Agent actions:** Shell escaping is described as prose for the LLM to follow (skippable under adversarial input); a corrupted `daily_spend.json` silently resets to `$0.00`, bypassing the limit; budget parsed with no validation (negative/non-numeric).
- **What worked:** Extract shell sanitization into Python (or a `--from-queue` CLI flag); re-estimate spend from `queue.md` on corruption; validate budget is positive numeric.
- **What failed or caused friction:** Guardrails enforced by LLM compliance, not code, can be bypassed by crafted inputs or corruption.
- **Human correction or steering:** Move real guards into deterministic code; the review's Three Questions note these are prompt-engineering risks pytest can't catch.
- **Final outcome:** P2s.
- **Reusable lesson:** A security control written as a natural-language instruction to an agent is advisory, not enforced; move real guards into deterministic code; validate any value reaching a spend guardrail.
- **Workshop teaching opportunity:** The boundary between "code review" and "prompt review" — skills need a different verification approach (negative-budget bypass is a great demo).

---

#### 121. inline-imports-tradeoff — Deferred imports: move to top-level or document the tradeoff
- **Friction-type:** F6 (style vs intentional design — two valid options)
- **Source traces:** A1 `todos/021-complete-p3-inline-imports.md:14-16`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 17
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** deferred imports in `agent.py` methods for `schema`/`state`/`staleness`
- **Original goal:** Top-level per PEP 8, OR document why deferred.
- **Context provided:** "the architecture reviewer argues these are intentional for keeping the gap subsystem optional when `schema_path` is None. Consider this tradeoff."
- **Files/tools used:** `agent.py`
- **Agent actions:** Two reviewers disagreed; the todo presents both Option A (move) and Option B (document).
- **What worked:** Surfaced an intra-review disagreement rather than asserting one answer.
- **What failed or caused friction:** PEP 8 default vs an intentional optionality design.
- **Human correction or steering:** Accepted — acceptance criterion allows either resolution.
- **Final outcome:** complete.
- **Reusable lesson:** When reviewers disagree, present the tradeoff and let acceptance criteria allow either fix.
- **Workshop teaching opportunity:** Healthy reviewer disagreement → a decision, not a forced "fix."

---

#### 122. input-validation-side-commands — Unvalidated subprocess target + budget value
- **Friction-type:** F1/F6 (input validation: subprocess target + budget value)
- **Source traces:** A1 `todos/036-complete-p3-subprocess-open-validate-extension.md:14` (`main.py:277`), `todos/061-complete-p3-budget-validation.md:14`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18 (036) / Cycle 22 (061)
- **Date/source:** see traces
- **Tool used:** not clear
- **Project/topic:** `subprocess.run(["open", path])` without `.md` validation (036); budget parsed from queue file with no validation (061)
- **Original goal:** Validate the file extension before `open`; validate budget is positive numeric.
- **Context provided:** "Negative budgets could cause all queries to appear 'over budget' or bypass the check."
- **Files/tools used:** `main.py:277`, `.claude/skills/research-queue.md`
- **Agent actions:** Validated inputs at the point they reach a side effect.
- **What worked:** Caught two unvalidated inputs reaching subprocess/guardrail logic.
- **What failed or caused friction:** Trusting hand-editable / path inputs.
- **Human correction or steering:** Accepted.
- **Final outcome:** complete.
- **Reusable lesson:** Validate any value that reaches a subprocess or a spend guardrail, even from "trusted" local files.
- **Workshop teaching opportunity:** Guardrails are only as good as their input validation.

---

#### 123. self-finding-became-wrong — A "dead code" finding was already false by fix time
- **Friction-type:** F6 (finding invalidated by an earlier fix)
- **Source traces:** A2 `docs/reviews/self-enhancing-agent/fix-batch4.md:25-28`, `REVIEW-SUMMARY.md:88-92`, `agent.py:70,151`, `cli.py:305`
- **Corroboration:** 1
- **Cycle/arc:** Self-Enhancing Agent
- **Date/source:** see traces
- **Tool used:** Claude Code (fix executor) vs. original code-simplicity-reviewer
- **Project/topic:** `_last_critique` attribute
- **Original goal:** Remove dead state (`_last_critique` stored but never read).
- **Context provided:** Finding #13 said `_last_critique` is "stored but never read."
- **Files/tools used:** `agent.py`, `cli.py:305`
- **Agent actions:** During fixes, the executor found `_last_critique` IS now read by `cli.py:305` (added in batch 1 to fix the visibility P1 — episode 81) — "the finding is now moot."
- **What worked:** The fix executor re-validated the finding against current code instead of blindly applying it.
- **What failed or caused friction:** Findings were generated against a snapshot; fixing other findings invalidated this one.
- **Human correction or steering:** Skip #13; keep the `last_critique` property.
- **Final outcome:** Explicitly skipped with rationale.
- **Reusable lesson:** A batch of findings has internal dependencies — fixing one can make another false; re-check each finding against the *current* tree, not the review snapshot.
- **Workshop teaching opportunity:** Review findings have a shelf life; ordering and re-validation matter when fixes interact.

---

#### 124. substring-bypass-lint-script — Lint `name not in instructions` false-positives on short names
- **Friction-type:** F1 (correctness: substring check passes on short tool names)
- **Source traces:** A1 `todos/122-pending-p2-substring-matching-false-positive-risk.md:14-21` (resolved), `scripts/lint_mcp_parity.py:15`, `tests/test_mcp_server.py:466`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26
- **Date/source:** see traces
- **Tool used:** not clear (Security Sentinel, Architecture Strategist, Agent-Native Reviewer)
- **Project/topic:** `lint_mcp_parity.py:15` substring match; same in `test_mcp_server.py:466`
- **Original goal:** Use word-boundary matching to avoid `list`/`report` passing trivially.
- **Context provided:** Cites a prior solution doc: "`docs/solutions/security/domain-matching-substring-bypass.md` documents the same structural risk for domain matching" (episode 12).
- **Files/tools used:** `scripts/lint_mcp_parity.py`, `tests/test_mcp_server.py`
- **Agent actions:** Recognized a recurring structural pattern from a different domain (domain matching); fixed with word-boundary regex.
- **What worked:** Cross-domain pattern transfer (domain-match bug → lint-match bug).
- **What failed or caused friction:** Substring containment used where exact/boundary match is required.
- **Human correction or steering:** Accepted (resolved).
- **Final outcome:** resolved.
- **Reusable lesson:** "Substring `in`" for identity checks is a recurring bug class; reuse the documented fix.
- **Workshop teaching opportunity:** Compounding knowledge — a solution doc from one feature catches a bug in another.

---

#### 125. ci-workflow-hardening — First CI workflow ships with security/perf gaps
- **Friction-type:** F6 (CI security/supply-chain/perf hardening)
- **Source traces:** A1 `todos/119-pending-p2-ci-workflow-missing-permissions-block.md:14`, `todos/120-pending-p2-ci-actions-pinned-to-mutable-tags.md:14`, `todos/121-pending-p2-ci-workflow-missing-pip-cache.md:14`, `todos/125-pending-p3-ci-python-version-mismatch.md:14` (all resolved), `.github/workflows/mcp-lint.yml`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 26 (first CI workflow)
- **Date/source:** see traces
- **Tool used:** not clear (Security Sentinel, Performance Oracle, Architecture Strategist)
- **Project/topic:** `.github/workflows/mcp-lint.yml` — no `permissions` block (119), mutable `@v4`/`@v5` tags (120), no pip cache (121), Python 3.12 vs project 3.14 (125)
- **Original goal:** Least-privilege token, SHA-pin actions, cache pip, align Python version.
- **Context provided:** 120: "A compromised or hijacked tag could point to arbitrary code."
- **Files/tools used:** `.github/workflows/mcp-lint.yml`
- **Agent actions:** Standard CI-hardening checklist applied to a brand-new workflow.
- **What worked:** Caught all four on the first CI file; all resolved (actions SHA-pinned).
- **What failed or caused friction:** First-time CI authoring missed standard hardening.
- **Human correction or steering:** All accepted/resolved.
- **Final outcome:** resolved.
- **Reusable lesson:** New CI workflows need a fixed checklist: permissions, pinned SHAs, caching, runtime-version parity.
- **Workshop teaching opportunity:** Reusable "review a GitHub Actions workflow" rubric.

---

#### 126. unauth-http-transport — MCP HTTP transport has zero auth (open proxy)
- **Friction-type:** F6 (security — exposed attack surface); A1 tags F1
- **Source traces:** A1 `todos/089-done-p1-unauthenticated-http-transport.md:14-16`; A2 `docs/reviews/cycle-19-mcp-server/REVIEW-SUMMARY.md:46-47`, `docs/fixes/cycle-19-mcp-server/batch1.md:14-18`
- **Corroboration:** 2 (closely related to episode 13; A1 records the standalone P1)
- **Cycle/arc:** Cycle 19 / 26 (MCP)
- **Date/source:** see traces
- **Tool used:** not clear (Security sentinel)
- **Project/topic:** `MCP_TRANSPORT=http` binds host/port with no authentication
- **Original goal:** Add a real auth control; "a warning is not a security control."
- **Context provided:** "open proxy for web research with API key consumption... other local processes can reach it."
- **Files/tools used:** MCP server
- **Agent actions:** Distinguished a log warning from an actual control.
- **What worked:** Rejected security-theater (warning) as insufficient (resolved via localhost-only fail-closed — see episode 13).
- **What failed or caused friction:** Network-exposed tool server with no gate.
- **Human correction or steering:** Accepted (p1).
- **Final outcome:** done.
- **Reusable lesson:** A warning is documentation, not enforcement; network surfaces need auth.
- **Workshop teaching opportunity:** "A warning is not a security control" — a quotable line for the workshop.

---

#### 127. retry-query-char-validation — LLM retry queries lack character-class validation (self-rated low)
- **Friction-type:** F1 (low-risk: LLM could emit search operators) — honestly rated low
- **Source traces:** A1 `todos/051-pending-p3-retry-query-character-validation.md:14-32` (done)
- **Corroboration:** 1
- **Cycle/arc:** Cycle 28/29
- **Date/source:** see traces
- **Tool used:** not clear (Security)
- **Project/topic:** `_validate_retry_queries()` doesn't validate characters; LLM queries go straight to `search()`
- **Original goal:** Optionally reject `site:`/`inurl:`/`filetype:` operators.
- **Context provided:** Reviewer enumerates why "The risk is low": system-prompt defense, SSRF blocks, worst case wasted credits.
- **Files/tools used:** retry/coverage module
- **Agent actions:** Raised a vector and then argued down its own severity with three mitigations.
- **What worked:** Self-calibrated severity (rated p3, listed existing defenses).
- **What failed or caused friction:** Theoretical operator-injection from a manipulated LLM.
- **Human correction or steering:** Accepted as p3.
- **Final outcome:** done.
- **Reusable lesson:** Good findings state their own mitigations and rate severity honestly.
- **Workshop teaching opportunity:** Model of a well-calibrated low-severity security note (contrast with over-flagging).

---

#### 128. tiered-model-routing-ab — A/B model swap measured against a hidden validation bug
- **Friction-type:** F6 (measure-before-promote process + a found bug)
- **Source traces:** A3 `docs/solutions/architecture/tiered-model-routing-planning-vs-synthesis.md:22-146`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 21
- **Date/source:** 2026-03-06
- **Tool used:** not clear (env-var A/B); 5 review findings
- **Project/topic:** Routing planning/relevance to Haiku, synthesis to Sonnet
- **Original goal:** Cut cost/latency on classification-like tasks.
- **Context provided:** 15+ calls all used Sonnet; 8 are classification-like.
- **Files/tools used:** `modes.py`, `agent.py`, `relevance.py`, `query_validation.py`
- **Agent actions:** Added `planning_model`/`relevance_model` (Haiku default); routed 7 planning + relevance sites.
- **What worked:** A/B compare *decisions* (gate outcomes) not raw scores — 0 flips over 14+9 queries; promote env var → permanent field only after validation.
- **What failed or caused friction:** Discovered `meaningful_words()` didn't strip punctuation/split hyphens (`"standards,"`≠`"standards"`), silently degrading validation — had to fix it *before* measuring (see episode 16).
- **Human correction or steering:** Bug fixed before A/B; all 5 review findings fixed.
- **Final outcome:** ~4-7% cost, ~3-5s latency saved.
- **Reusable lesson:** A/B test decisions not scores; clean the measurement instrument before measuring; classify the task before choosing the model.
- **Workshop teaching opportunity:** Disciplined empiricism for model changes — a hidden bug can invalidate an experiment.

---

#### 129. no-transaction-wrapper — Migration not wrapped in a transaction (cross-project)
- **Friction-type:** F6 (data-integrity gap — partial-failure leaves broken DB)
- **Source traces:** A2 `docs/reviews/session-2-supabase/REVIEW-SUMMARY.md:88-92`, `001_initial_schema.sql:1-424`
- **Corroboration:** 1
- **Cycle/arc:** Session 2 (Supabase) — cross-project
- **Date/source:** see traces
- **Tool used:** Claude Code sub-agent (data-integrity-guardian)
- **Project/topic:** PF-Intel — migration `001_initial_schema.sql`
- **Original goal:** Create the initial schema.
- **Context provided:** 424-line migration with extensions, tables, policies, triggers.
- **Files/tools used:** `001_initial_schema.sql`
- **Agent actions:** No `BEGIN; ... COMMIT;` wrapper — if any statement fails mid-way the database is left partially created with no rollback.
- **What worked:** data-integrity-guardian thought about the failure path of running the migration, not just its success path.
- **What failed or caused friction:** Non-transactional multi-statement DDL can strand the schema half-built.
- **Human correction or steering:** Wrap in a transaction; put `CREATE EXTENSION` before `BEGIN`.
- **Final outcome:** P2.
- **Reusable lesson:** Multi-statement migrations need transactional atomicity so a mid-run failure rolls back cleanly.
- **Workshop teaching opportunity:** Always design for the half-failed run, not just the clean apply.

---

#### 130. validation-questions-between-sessions — "What test would catch it?" feeds the next session
- **Friction-type:** F6 (process pattern preventing compounding bugs)
- **Source traces:** A3 `docs/solutions/workflow/validation-questions-between-sessions.md:24-65`
- **Corroboration:** 1
- **Cycle/arc:** Cycle 18 (observed)
- **Date/source:** 2026-02-15
- **Tool used:** not clear (process)
- **Project/topic:** Between-session validation questions
- **Original goal:** Catch design risks early in multi-session cycles.
- **Context provided:** A shaky Session-1 decision gets built on by Session 2, expensive to fix by Session 4.
- **Files/tools used:** n/a (process)
- **Agent actions:** none — process change.
- **What worked:** Q3 ("least confident + what test catches it") identified the `_last_source_count` private-attr risk, shaping the Session-2 prompt to test it; "deviations from plan" beats "alternatives rejected" for plan staleness.
- **What failed or caused friction:** Without it, issues surface only in post-cycle review.
- **Human correction or steering:** Adopted as a standing ritual.
- **Final outcome:** Forward-feeding risk identification.
- **Reusable lesson:** End each work session by naming the least-confident area and the test that would catch it; feed it into the next prompt.
- **Workshop teaching opportunity:** A concrete, low-cost habit for steering agents across sessions — the feed-forward chain in action.

---

#### 131. dependency-pinning-loose — Loose `>=`-only dependency constraints, no lockfile
- **Friction-type:** F6 (supply-chain / reproducibility)
- **Source traces:** A1 `todos/035-complete-p3-dependencies-minimum-version-pins.md:14`, `todos/099-done-p3-tighten-fastmcp-version.md:14`
- **Corroboration:** 1 (the fastmcp-specific instance is episode 93; this is the general pinning finding)
- **Cycle/arc:** Cycle 18 and Cycle 26
- **Date/source:** see traces
- **Tool used:** not clear (Security sentinel)
- **Project/topic:** `>=`-only pins, no lockfile (035); `fastmcp>=2.0,<4.0` too wide (099)
- **Original goal:** Tighten constraints to avoid untested upgrades / supply-chain risk.
- **Context provided:** "FastMCP major version bumps could break the `Client` test fixture"; tests catch breakage "only after it happens."
- **Files/tools used:** `requirements.txt`, `pyproject.toml`
- **Agent actions:** Flagged loose ranges twice across cycles.
- **What worked:** Specific breakage scenarios for fastmcp.
- **What failed or caused friction:** Reactive (tests) rather than proactive (pins).
- **Human correction or steering:** Accepted (Codex later forced `>=3.0,<3.1` — episode 93).
- **Final outcome:** complete/done.
- **Reusable lesson:** Pin young libraries tightly; lockfiles turn "future breakage" into "deliberate upgrade."
- **Workshop teaching opportunity:** Reactive (tests) vs proactive (pins) defense framing.

---

## Data-quality caveats

The extractors flagged several issues with the underlying records. They are surfaced here so a fact-checker can weigh the evidence appropriately:

- **Duplicate issue_ids 054–063.** In `todos/`, issue ids 054 through 063 each have **two distinct files** describing unrelated findings (e.g. `054-complete-p1-shell-injection-apostrophes` and `054-done-p1-path-traversal-resolve-context` are both "054"). Episodes disambiguate with `a`/`b` suffixes in the raw extraction. The id reuse is itself a real tracking-hygiene defect (it is the subject of episode 6's workshop note).
- **`*-pending-*` filenames carrying `status: done`.** Several todo files named `*-pending-*` carry `status: done`/`resolved` in their YAML frontmatter (e.g. 045, 066, 067, 119). Outcomes in this file follow the **frontmatter status**, not the filename. Treat the filename as unreliable.
- **Solution docs describing "Planned" fixes.** Several `docs/solutions/` docs describe a fix as **Planned** rather than shipped (e.g. `ssrf-bypass-via-proxy-services.md`, `agent-native-return-structured-data.md`). For those episodes the **Final outcome is `not clear`** — the doc records the intended remediation, not confirmation it landed. Where another tier (git commits) corroborates the fix, that is noted in Source traces.
- **Lessons docs are retrospective framing, not primary records.** A3 (`LESSONS_LEARNED.md`, `docs/lessons/`, distilled `docs/solutions/`) are **distilled retrospective writeups**. Their "Agent actions / Human correction" fields are reconstructed from the doc's narrative and are marked `(inferred)` where the doc does not state them as a primary record. Treat them as the project's own framing of events rather than a contemporaneous log.
- **Per-incident tool attribution is usually `not clear`.** Because the project used both Claude Code and Codex and most artifacts don't name the host tool, attribution is asserted only where a filename or body explicitly says so. Co-author trailers (`Claude Opus 4.5/4.6/4.8`) establish *authorship* but not which reviewer found a given issue.
- **`(sources differ)` markers.** A few merges surfaced genuine conflicts (e.g. the exact `synthesize.py` line numbers for double-sanitization differ between A2 and A3; SSRF remediation completion state differs between A1 "ready/complete" and A3 "Planned"). Both readings are preserved in the relevant episodes rather than reconciled.
