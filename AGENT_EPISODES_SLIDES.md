# Managing AI Agents — 12 Real Episodes (Slide Deck)

> A one-slide-per-episode short-list pulled from `AGENT_EPISODES.md` (131 traced episodes).
> Chosen for teaching value and spread across all six friction types. Ordered as an arc:
> **verify → the AI's blind spots → review & history → getting stuck → over-engineering → briefing.**
> Every slide is faithful to the source; full field-by-field detail and citations live in `AGENT_EPISODES.md`.

**How to present each slide:** read *The setup*, let them guess what goes wrong, then reveal *The friction*. The bolded **Lesson** is the slide's takeaway; *Say to the room* is your talking point / audience question.

Friction codes: **F1** wrong/unsafe output · **F2** vague brief → bad output · **F3** stuck/deferred · **F4** over-engineering · **F5** silent failure · **F6** review/process.

---

## Slide 1 — "All tests pass" — but the tests were gone
**`replace_all` corrupted test names · F5 · Cycle 12**

- **The setup:** Asked the agent to rename a helper (`_sanitize` → `sanitize`) across the codebase. It used a global find-and-replace.
- **What the AI did:** Ran `replace_all` on the substring `_sanitize` — which also matched *inside* `test_sanitize_content`, turning it into `testsanitize_content`.
- ⚠️ **The friction:** Renamed tests no longer matched pytest's `test_` collection rule, so they **silently stopped running. No error. The suite still went green.**
- 🔧 **The human fix:** Compared the *collected test count* before vs. after the refactor — the count dropped. Reverted the bad renames. New rule: "always check test count after a rename."
- **Lesson:** **A green test run doesn't prove the tests ran. Substring find-replace corrupts anything that *contains* the string.**
- *Say to the room:* "When you tell an AI to 'rename it everywhere,' it does exactly that — including places you didn't mean. The danger isn't a loud error; it's the silent omission. Always ask: *how would I know if it did too much?*"
- *Trace:* `LESSONS_LEARNED.md:19`, `docs/lessons/patterns-index.md:88`

---

## Slide 2 — The feature you built was never running
**Tavily built but silently fell back to DuckDuckGo · F5 · Cycles 8–9**

- **The setup:** Reports were low-quality. The team had integrated Tavily (a better search API) two cycles earlier to fix exactly this.
- **What the AI did:** Kept producing weak reports. The team blamed bot-blocking and relevance scoring, and started "fixing" those.
- ⚠️ **The friction:** `TAVILY_API_KEY` was never in `.env`, so every run **silently fell back to DuckDuckGo.** The integration was *built but inactive* — and graceful fallback hid it. "Nothing threw an error, so we attributed it to site-level bot blocking, not the wrong search provider entirely."
- 🔧 **The human fix:** A side-channel check + `--verbose` logging revealed *which* provider actually ran. Activated Tavily; added logging whenever a fallback fires.
- **Lesson:** **A "working" pipeline with degraded output is the hardest bug class. Verify *which code path ran* — not just that nothing errored.**
- *Say to the room:* "Graceful degradation is great for users and terrible for debugging. If your AI system has fallbacks, make them *loud* — log every time the backup plan kicks in."
- *Trace:* `docs/lessons/operations.md:70-101`, commit `7b3c7f8`

---

## Slide 3 — The AI has no clock
**LLM-generated timestamps collided · F1 · Cycle 22**

- **The setup:** Parallel background research jobs each needed a unique output filename. The agent was told to use a microsecond timestamp.
- **What the AI did:** Wrote what *looked* like microsecond timestamps into each path.
- ⚠️ **The friction:** The model generates all values in **one inference pass — it has no real clock between them.** Two parallel jobs got the *identical* timestamp (`005243522271`); uniqueness happened only by luck. One would have overwritten the other.
- 🔧 **The human fix:** Generate real-world facts (time, randomness, IDs) **in code, not in the model.** Switched to a deterministic counter (1, 2, 3) + atomic file writes.
- **Lesson:** **Never delegate real-world facts to the model. It can't observe time, generate true randomness, or produce truly unique IDs within a single response.**
- *Say to the room:* "This is the single most important mental-model shift: the AI isn't a tiny computer that runs your code. Asking it for a 'unique timestamp' gets you a *plausible-looking constant*. Anything that must be real — time, a random token, a DB id — generate it in actual code."
- *Trace:* `todos/055-complete-p1-timestamp-collision-parallel.md:124`, commit `f2efd83`

---

## Slide 4 — First-draft AI code needs a hardening pass (and it regresses)
**Bare `except Exception` swallowed real failures · F1 · Cycles 1 → "self-enhancing"**

- **The setup:** Pipeline stages need to run without crashing. The agent wrapped risky calls in `except Exception`.
- **What the AI did:** Used broad catches that **silently swallowed config errors, auth failures, and network issues** — even catching `MemoryError`/`SystemExit`. Later, *after this was fixed and the rule written down,* a new agent re-introduced `except (CritiqueError, Exception)` — a **regression of a documented past fix.**
- ⚠️ **The friction:** Broad catches hide failures that never surface as errors. And the anti-pattern came *back* because the rule lived only in prose. 8 of 9 review agents flagged the regression.
- 🔧 **The human fix:** Narrow to specific exceptions + a DEBUG log. A *git-history-aware* reviewer recognized "we fixed this exact thing before."
- **Lesson:** **First-draft AI code reliably needs an error-handling + secret-handling pass. And a convention that lives only in prose will be violated again.**
- *Say to the room:* "Two lessons in one: always do a dedicated 'how does this fail?' review of AI code, and know that writing a rule down isn't the same as enforcing it. The most valuable reviewer is one that remembers your past mistakes."
- *Trace:* `todos/001-complete-p1-bare-except-exception.md`, `docs/reviews/self-enhancing-agent/REVIEW-SUMMARY.md:11-16`

---

## Slide 5 — "We have a doc for that" doesn't stop a recurring bug
**Non-idempotent sanitization double-encoded text · F1 · Cycles 18/20/24/27 (corroboration 5/5)**

- **The setup:** A shared `sanitize_content()` escapes untrusted web text before it enters prompts. Convention: sanitize once. A solution doc *documented* the rule.
- **What the AI did:** Each new pipeline stage defensively re-sanitized already-sanitized input. `& → &amp; → &amp;amp;`. Real reports showed `AT&T` and `R&D` corrupted into `R&amp;amp;D`.
- ⚠️ **The friction:** The bug **came back in four separate cycles** despite a written solution doc. "Defense in depth by re-running a non-idempotent transform" is itself corruption. One review even found "the PR fixed the third pass, but two remain."
- 🔧 **The human fix:** Stop spot-fixing. Make the function **idempotent** (`html.unescape()` before escaping) + enforce a single boundary + 13 invariant tests. Bonus: the planning agent *falsified the roadmap's own suggested fix* (`html.escape` would also double-encode) before coding.
- **Lesson:** **A defect that recurs across cycles signals a missing invariant — not a need for more vigilance. Fix the property, not the instances.**
- *Say to the room:* "Institutional memory ('we wrote it down') feels like a fix. It isn't. If the same class of bug keeps reappearing, the durable answer is to make it *impossible* (an idempotent operation, a single chokepoint), not to keep catching it in review."
- *Trace:* `docs/solutions/security/non-idempotent-sanitization-double-encode.md`, commits `fa4daaf`→`5060e63`

---

## Slide 6 — The reviewer that remembers beats the reviewer that only sees the diff
**FastMCP version cap: add → lose → re-find · F6 · Cycles 19 & 26**

- **The setup:** A dependency (`fastmcp`) was deliberately pinned to a tested range to prevent a surprise major-version break. Only `3.0.2` was ever validated.
- **What the AI did:** A later change quietly **widened the cap back** to `<4.0`. Every fresh install — and a new required CI check — would now float to arbitrary, untested future versions. The passing `3.0.2` test suite masked the risk entirely.
- ⚠️ **The friction:** A previously-closed decision silently re-opened. A reviewer looking only at *this diff* sees nothing wrong.
- 🔧 **The human fix:** **Codex cross-referenced the repo's own history**, saw this exact pin had been tightened in Cycle 19, and blocked the loosening. Claude Code's second review confirmed the re-fix (`>=3.0,<3.1`).
- **Lesson:** **Dependency caps (and many "small" choices) are decisions *with history*. Record the *why*, and have review check it — diff-only review can't catch a regression of a past decision.**
- *Say to the room:* "Two AI reviewers with different strengths caught this together: one remembered the history, one confirmed the fix. When the stakes are real, a second independent set of eyes — ideally one with memory of past decisions — is worth it."
- *Trace:* `docs/reviews/2026-03-10-cycle-26-code-review-findings.md:11-15`, commits `96e3fe2`→`e990902`→`5fa7ea0`

---

## Slide 7 — Tuning a knob instead of finding the cause
**Four commits chased rate-limit errors before the real fix · F3 · Cycles 10–11**

- **The setup:** Summarization kept hitting the API rate limit (HTTP 429s). Goal: stop the 429s.
- **What the AI did:** Reduced batch size 12→8. Still 429s. Reduced 8→5 + added more batching. *Then* finally added a concurrency semaphore — *then* raised batch size back to 8.
- ⚠️ **The friction:** The first two commits **treated a symptom.** The real cause was multiplicative: `5 sources × 5 chunks = 25 simultaneous calls` via `asyncio.gather`. Batch size barely touched it. The project's own lesson file later labeled this "symptom-chasing."
- 🔧 **The human fix:** Put concurrency control at the **leaf API-call layer** (`MAX_CONCURRENT_CHUNKS` semaphore), not the task-organization layer. App-level 429s dropped ~30 → 1.
- **Lesson:** **When a knob "helps a bit" but never fixes it, you're tuning a symptom. Step back and find the multiplicative root cause.**
- *Say to the room:* "Agents are *great* at confidently turning a dial and reporting 'improved from 651 to 303.' Half-fixing looks like progress. Your job as the human is to ask: 'is this the cause, or a symptom?' — and to stop the dial-turning loop."
- *Trace:* `docs/lessons/operations.md:129-135`, commits `0c49066`→`ed59318`

---

## Slide 8 — Zombie backlog items drift forever without a kill rule
**MCP parity + lint deferred ~5 cycles · F3 · Cycles 19 → 31 (corroboration 5/5)**

- **The setup:** A few "nice to have" tasks (MCP tool parity, an enforcement lint script) kept getting bundled into cycles.
- **What the AI did:** Deferred them. Again. And again — the lint script was punted across cycles 19, 20, 22, and 25 as "least ready."
- ⚠️ **The friction:** "Items deferred 2+ times drift indefinitely." The recurrence wasn't because the work was wrong — it was **missing one concrete attribute** (an *enforcement gate*: where/when the check actually runs).
- 🔧 **The human fix:** A **"promote-or-drop at deferral #2"** rule. Outcome: one tool shipped, one was *explicitly dropped* (already covered elsewhere), and the lint finally shipped with a CI gate that was green on first run. "Every enforcement mechanism ships with its feature."
- **Lesson:** **A perpetually-deferred item is usually missing one specific thing. Name it, supply it, or kill the item — don't let it drift.**
- *Say to the room:* "AI-managed backlogs accumulate zombies. 'We'll get to it' is how a task survives forever doing nothing. Force the decision: what exactly is blocking this, and are we doing it or dropping it?"
- *Trace:* `todos/123-pending-p2-mcp-missing-cost-and-critique-history-tools.md`, `docs/solutions/workflow/mcp-parity-lint-ci-enforcement.md`

---

## Slide 9 — When reviewers say "too complex," believe them
**300-line provider abstraction cut to ~50 lines · F4 · Cycle 7**

- **The setup:** Add a search-provider fallback (Tavily + DuckDuckGo).
- **What the AI did:** Designed a full abstraction — a `SearchProvider` Protocol, a `MultiProvider` class, **5 new files, and a CLI flag.**
- ⚠️ **The friction:** It was **~6× the code for zero additional capability.** Three independent reviewers all said: too complex.
- 🔧 **The human fix:** ~50 lines, one function (`_search_tavily`) in the existing file, zero new files. Env vars instead of a CLI flag. A *prompt instruction* instead of new code for comparison bias.
- **Lesson:** **Prefer the simplest thing that works. Before building an abstraction, ask: "can a prompt or a config value solve this?"**
- *Say to the room:* "Left alone, an AI will happily build you a beautiful, extensible, six-file framework for something that needs fifty lines. Over-engineering is a default failure mode — your steering job is often to make it do *less*."
- *Trace:* `docs/lessons/operations.md:38-69`, `LESSONS_LEARNED.md:13`

---

## Slide 10 — Verify the feature actually *does* something
**A "+0.5 relevance boost" that was arithmetically a no-op · F4 · Cycle 24**

- **The setup:** A brainstorm proposed a `preferred_domains` field that would give trusted sources a **+0.5 nudge** on a 1–5 relevance scale.
- **What the AI did (in brainstorm):** It sounded reasonable, so an early plan revision even parsed and stored the field "for forward compatibility."
- ⚠️ **The friction:** During planning, someone did the **arithmetic against the real type system**: scores are *integers*, the cutoff is an *integer* (3). `2 + 0.5 = 2.5` still fails; a `3` already passes. **The boost literally couldn't change any outcome.**
- 🔧 **The human fix:** Removed the field entirely. "Storing a no-op field confuses future readers (YAGNI). Adding it later costs ~2 lines."
- **Lesson:** **Confirm a proposed feature changes real behavior before building — or even stubbing — it. "Forward-compatible" stubs are anti-YAGNI.**
- *Say to the room:* "This is the best example of *planning* catching what *brainstorming* missed. Ideas sound great in prose; trace them through the actual data types before you commit. A feature that can't change an output isn't a feature."
- *Trace:* `docs/plans/2026-03-06-feat-swappable-context-profiles-plan.md:37-39`

---

## Slide 11 — Early "reasonable" assumptions harden into coupling
**Business-report template forced onto every query · F2/F4 · Cycles 20–23**

- **The setup:** The tool was built for one use case (competitive business intel), so synthesis prompts hardcoded sections like "Buyer Psychology" and "Service Portfolio" in 7 places.
- **What the AI did:** When the tool was generalized, those business sections got **forced onto every query** — including "how does Python asyncio work," producing hallucinated or empty business sections.
- ⚠️ **The friction:** Completely **invisible while only business queries were run.** A single technical-query test would have caught it. The fix even had to be applied *twice* — a legacy `elif context` branch survived the first pass.
- 🔧 **The human fix:** Gate domain-specific structure behind an explicit `has_business_context` flag; use generic field names; **test outside the original domain.** Net result: **−210 lines** (the fix was deletion).
- **Lesson:** **Reasonable single-use assumptions become coupling. When you expand scope, grep for original-domain vocabulary and test the new domain — and the fix is often subtraction.**
- *Say to the room:* "AI builds to the examples you give it. Show it only business queries and it bakes 'business' into the foundation. Whenever you broaden what a tool does, deliberately test the case it was *never* built for."
- *Trace:* `docs/solutions/logic-errors/conditional-prompt-templates-by-context.md`, `docs/solutions/architecture/domain-agnostic-pipeline-design.md`

---

## Slide 12 — A borrowed prompt must be re-grounded in your task
**Research-study phrasing was wrong for search queries · F2 · Cycle 31**

- **The setup:** A study found that prompts like "mechanisms most people overlook" push a model past generic answers. The team wanted to apply that to generate more novel sub-queries.
- **What the AI did (caught in brainstorm):** The brainstorm's *"least confident"* note flagged the gap: that phrasing produces interesting *explanations* — but this module generates **search-engine queries**, where it would degrade results.
- ⚠️ **The friction:** Lifting a prompt that worked in one task framing (explanation) into a different output type (search query) would have quietly hurt decomposition quality.
- 🔧 **The human fix:** The plan re-grounded it as "angles that typical searches would miss," and **validated it with three offline trace-throughs** before any code.
- **Lesson:** **A prompt that works for one task doesn't transfer verbatim. Re-ground borrowed phrasing in your target's actual output type — and verify before shipping.**
- *Say to the room:* "Prompt 'best practices' are task-specific, not universal. And notice the healthy loop here: the brainstorm *named its own biggest uncertainty*, and the next phase addressed exactly that. Reward an AI that says 'here's what I'm least sure about.'"
- *Trace:* `docs/brainstorms/2026-04-22-cycle-31-novelty-decomposition-mcp-tools-brainstorm.md:88`, plan `:26-30`

---

## Closing recap — Five rules from these 12 episodes

1. **Verify *what ran*, not that it ran.** Green tests, no errors, "improved" — none prove correctness. Check counts, check which code path executed. *(Slides 1, 2, 7)*
2. **The AI is not a computer.** It can't keep time, can't be truly random, regresses written rules, and hallucinates plausible constants. Generate real facts in code. *(Slides 3, 4)*
3. **A recurring bug means a missing invariant.** Fix the property (idempotent, single boundary), don't keep catching instances. *(Slide 5)*
4. **Steer it to do *less*.** Over-engineering and no-op features are default failure modes. Ask "can a prompt or config solve this?" and trace features through real types. *(Slides 9, 10)*
5. **Brief for your task; review with memory.** Re-ground borrowed prompts, test outside the original domain, force promote-or-drop on stale items, and use a history-aware second reviewer. *(Slides 6, 8, 11, 12)*

> Full episode set (131, all traced): `AGENT_EPISODES.md`.
