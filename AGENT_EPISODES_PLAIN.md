# Managing AI Agents — Plain-Language Workshop Version

> A non-technical translation of the 12 curated episodes in `AGENT_EPISODES_SLIDES.md`.
> Each one has two layers:
>
> - **🟦 In plain terms (for you)** — what actually happened, explained without needing to read the code. Enough that you understand it and could answer a question about it.
> - **🎤 For the room** — a fully non-technical retelling for creatives & business owners: an everyday analogy, the management takeaway, and a question to spark discussion.
>
> The real technical detail and traces live in `AGENT_EPISODES.md` / `AGENT_EPISODES_SLIDES.md` if anyone wants to go deeper.
>
> **The throughline for the whole workshop:** AI doesn't fail loudly like a broken machine. It fails *quietly and confidently*. Managing it well is mostly about knowing where to look.

---

## Theme 1 — You can't trust that it worked just because nothing complained

### Episode 1 — "Everything passed" — but the checks had quietly vanished

**🟦 In plain terms (for you):**
The job had an automated safety net: a suite of tests that run and flag problems. Alex asked the AI to rename something throughout the project — a routine "find and replace it everywhere." The AI did exactly that, but the text it replaced *also appeared inside the names of some of the tests*. Renaming them broke the naming pattern the test-runner uses to *find* tests — so those tests stopped being picked up entirely. They didn't fail. They just silently stopped existing as far as the system was concerned. The safety net now had holes in it, and the screen still showed a reassuring green "all passed." It was caught only because someone noticed the *number* of tests had dropped.

**The lesson:** A green light proves the checks that ran passed — not that all your checks ran.

**🎤 For the room:**
> Imagine you tell an assistant, "Go through this 80-page contract and change every 'Jon' to 'John'." Reasonable. But they also turn "Jonathan" into "Johnathan," and — worse — three of your section headings contained "Jon," so when they got renamed, the items on your *review checklist* that pointed to those headings quietly fell off the list. You glance at the checklist: every remaining item is ticked. Looks perfect. You never notice three items disappeared.
>
> **Takeaway:** When you tell AI to do something "everywhere," it does *exactly* that — including the places you didn't mean. The danger is never a red error message. It's the thing that silently went missing. Always ask: *"How would I know if it did too much?"* — and when you can, count things before and after, don't just glance.
>
> **Discussion:** Where in your own work would an AI "helpfully" change something you didn't intend — and would you even notice?

---

### Episode 2 — The expensive tool you "switched on" was never actually running

**🟦 In plain terms (for you):**
The reports were coming out weak. The team had already added a premium search service two versions earlier specifically to fix this. But that service needs a password (an API key) to work, and the password had never been put in the settings file. So the system quietly used the free, lower-quality search instead — *every single time* — and never said a word, because it's designed to fall back gracefully when the premium one isn't available. For weeks they blamed the *wrong thing* (websites blocking them) and tried to fix that. The real problem was that the good tool was never switched on.

**The lesson:** A system that runs fine but produces mediocre results is the hardest kind of problem — because nothing is "broken."

**🎤 For the room:**
> You hire a premium overnight courier to fix your late deliveries. Weeks later, packages are still arriving slowly. You blame the warehouse, the packaging, the weather. Eventually you discover: you never gave the courier your account number, so every package quietly went out via cheap regular mail. The courier didn't complain — it just used the backup. Nothing was ever "broken." It was just never actually doing the premium thing you paid for.
>
> **Takeaway:** When an AI tool has a "backup plan," make the backup *loud*. A system that fails over silently will let you spend weeks fixing the wrong problem. Always confirm *which* path it actually took — not just that it didn't error out.
>
> **Discussion:** Have you ever assumed an AI tool was using your "good" settings/model/data when it had quietly fallen back to a default?

---

### Episode 7 — Turning the dial down a little, over and over, instead of fixing the cause

**🟦 In plain terms (for you):**
The system kept getting blocked for sending too many requests too fast to the AI service ("rate limited"). The fix attempts: turn the batch size down a bit (errors dropped from 651 to 303), then down a bit more, *then* finally someone added a proper limit on how many requests run at the same time — which is what actually solved it. The first two attempts were tuning a knob that could only ever *reduce* the problem, never end it, because the real cause was that the system fanned out into ~25 simultaneous requests regardless of the batch setting. The project's own notes later literally labeled this "symptom-chasing."

**The lesson:** When a tweak "helps a bit" but the problem keeps coming back, you're treating a symptom. Step back and find the real cause.

**🎤 For the room:**
> Your kitchen sink keeps overflowing. So you turn the tap down a little — "better, fewer overflows!" Turn it down more — "better still!" What you *haven't* done is unclog the drain, which is the actual problem. An AI is fantastic at confidently turning the tap and reporting "improved from 651 to 303!" That looks like progress. It isn't a fix.
>
> **Takeaway:** AI will happily iterate on a setting forever, and each step *looks* like it's working. Your job as the manager is to interrupt the dial-turning and ask: *"Is this the actual cause, or are we just making the symptom smaller?"*
>
> **Discussion:** When have you (or a team) kept tweaking a small setting because each change *felt* like progress?

---

## Theme 2 — The AI is not a tiny, reliable computer. It has blind spots you have to know.

### Episode 3 — The AI has no clock (and no real dice)

**🟦 In plain terms (for you):**
The system ran several research jobs at once, and each needed a unique filename so they wouldn't overwrite each other. The plan: stamp each one with the exact time down to the microsecond. The problem: the AI writes all of its output in *one breath* — it doesn't actually pause and look at a clock between items. So it just made up a time-*looking* number and reused the same one. Two jobs got identical stamps; one would have overwritten the other. The fix was to stop asking the AI for the time at all and instead have the regular (non-AI) code generate a simple counter (1, 2, 3).

**The lesson:** Don't ask the AI for facts about the real world — the current time, a truly random number, a genuinely unique ID. It can only *imitate* those.

**🎤 For the room:**
> Picture asking someone to fill out five forms all at once, in a single breath, and "write the exact current time on each." They can't glance at a clock five separate times — they're doing it all in one go — so they just write the same guessed time on all five. It *looks* like a real timestamp. It's a guess.
>
> This is the single most important thing to understand about AI: **it is not a tiny computer running your instructions.** It's more like an extremely well-read person answering in one continuous flow. Ask it for the time, a random number, or "a truly unique code," and you get something *plausible*, not something *real*.
>
> **Takeaway:** Anything that must be genuinely real — the actual date, a random winner, a unique order number — should come from a real source, not from the AI's imagination.
>
> **Discussion:** What's something you've asked an AI for that it can only *pretend* to know? (Today's news? A live price? A real citation?)

---

### Episode 4 — Its first draft hides problems — and a written rule isn't a lock

**🟦 In plain terms (for you):**
There's a common shortcut in code that means roughly "if *anything* goes wrong here, just ignore it and keep going." The AI's first draft used it widely — which means genuine failures (a wrong password, a network problem) were being silently swallowed instead of surfaced. The team fixed that and wrote down a rule: "never use the catch-all 'ignore everything.'" Later, a *different* AI session reintroduced the exact same shortcut — because the rule lived only in a document, not in anything that could stop it. It took a reviewer that actually *remembered the project's history* to say "wait, we deliberately fixed this exact thing before."

**The lesson:** AI's first draft reliably needs a "how could this hide a failure?" pass — and writing a rule down is not the same as enforcing it.

**🎤 For the room:**
> Two lessons in one. First: the AI's instinct was to put tape over the smoke detector so the kitchen smoke wouldn't keep setting it off — convenient, but now real fires are silent too. Second: someone took the tape off and put up a sign saying "do not tape the smoke detector"… and a week later a new person taped it again. A sign isn't a lock.
>
> **Takeaway:** Always review an AI's first draft specifically for *what it's quietly hiding*, not just whether it works. And don't assume a written policy will hold — the most valuable reviewer is one that *remembers your past mistakes*, because a fresh pair of eyes only sees today.
>
> **Discussion:** What's a "rule" your team wrote down that keeps getting broken anyway — and what would actually enforce it?

---

## Theme 3 — A problem that keeps coming back is a missing guardrail, not bad luck

### Episode 5 — "We have a document about that" didn't stop the same bug four times

**🟦 In plain terms (for you):**
There's a cleaning step that makes web text safe before it's fed to the AI. The rule was "clean it once." But every time a new part of the system was added, that part *also* cleaned the already-cleaned text "just to be safe." The cleaning isn't safe to repeat — running it twice corrupts the text. Real reports showed "R&D" turning into garbled "R&amp;amp;D." This same bug got found and fixed in *four separate versions* — even though a solution document existed describing it. The bug kept coming back because the document couldn't stop a new component from re-cleaning. The real fix was to make the cleaning step *smart enough to recognize already-cleaned text and leave it alone* — so it became impossible to corrupt by repeating.

**The lesson:** When the same bug returns across versions, the answer isn't "be more careful" — it's a guardrail that makes the mistake impossible.

**🎤 For the room:**
> Imagine running a document through Google Translate, English → French → English, "to be extra safe." Do it once, fine. But each new assistant who touches it runs it through *again* to be safe — and every round mangles it a little more. You had a written policy: "only translate once." It didn't help, because each person didn't know the last one already did it. The thing that finally worked: a translation machine smart enough to say "this is already in English — I'll leave it alone."
>
> **Takeaway:** Having documentation about a recurring problem *feels* like solving it. It isn't. If the same kind of mistake keeps happening, stop relying on people (or AIs) to remember the rule — change the system so the mistake can't happen.
>
> **Discussion:** What recurring mistake does your team keep "reminding everyone about" instead of designing out?

---

## Theme 4 — Left alone, AI over-builds. Your job is often to make it do less.

### Episode 9 — You asked for a coat hook; it designed a modular wall system

**🟦 In plain terms (for you):**
The task was small: add a backup search option in case the main one fails. The AI's plan was elaborate — a whole flexible framework, five new files, a new command-line option — built to support any number of future search providers nobody had asked for. It was about six times more code for zero extra capability *today*. Three separate reviewers independently said "this is too complicated." The actual solution was ~50 lines in a file that already existed, no new files, and a setting instead of a new command.

**The lesson:** Prefer the simplest thing that works. Before building a framework, ask "could a setting or a sentence of instruction do this?"

**🎤 For the room:**
> You ask a contractor to put up one coat hook by the door. They come back with blueprints for a modular, extensible, wall-mounted hanging system that could accommodate any future coat, hat, or bag configuration. It's beautiful. You needed a hook.
>
> **Takeaway:** Over-building is one of AI's *default* behaviors — it's eager and capable, so it gives you the deluxe version. A huge part of managing it is steering it to do *less*: "What's the simplest version of this?" is one of the most valuable instructions you can give.
>
> **Discussion:** When has "more powerful and flexible" actually cost you — in time, confusion, or things that broke?

---

### Episode 10 — A feature that sounded great but literally changed nothing

**🟦 In plain terms (for you):**
The idea: give "trusted" websites a small quality bonus — a +0.5 boost — so they're more likely to make it into a report. Sounds sensible. But the quality scores are whole numbers (1, 2, 3, 4, 5) and the cutoff to be included is 3. Do the arithmetic: a source scoring 2 gets bumped to 2.5 — still below 3, still excluded. A source scoring 3 was already getting in. The "+0.5 boost" couldn't actually change a single outcome. This was caught during *planning*, by someone doing the math before any code was written — and the feature was dropped entirely (an earlier draft had even started building it "for the future").

**The lesson:** Confirm a feature actually changes a real outcome before building it — or even before stubbing it out "for later."

**🎤 For the room:**
> A loyalty program proposes: "trusted customers get +0.5 bonus points." Sounds nice. But your reward tiers are whole numbers and you need 3 points to get a perk. +0.5 never moves anyone from one tier to the next — someone at 2 is now at 2.5 (still no perk), someone at 3 already had it. The perk *feels* generous and rewards literally no one. Five minutes of arithmetic before launch reveals it does nothing.
>
> **Takeaway:** AI (and humans!) generate ideas that *sound* good in words. Before you build, trace the idea through the real numbers and ask: *"Will this actually change what happens?"* A feature that can't change an outcome isn't a feature — it's clutter.
>
> **Discussion:** What's a well-intentioned policy or feature you've seen that, on inspection, changed nothing?

---

## Theme 5 — Brief it for *your* job; review it with memory

### Episode 11 — A template built for one kind of client, forced onto all of them

**🟦 In plain terms (for you):**
The tool was originally built for one job: business/competitor research. So the report template hard-baked business sections like "Buyer Psychology" and "Service Portfolio" — in seven different places. Later the tool was opened up to *any* topic. Now a purely technical question ("how does this programming feature work?") still got the business template slapped on it, producing empty or made-up business sections. It was completely invisible as long as only business questions were being asked. One test with a non-business question would have caught it. The fix was mostly *deletion* — removing the baked-in assumptions and only showing business sections when there's actually a business context.

**The lesson:** AI builds to the examples you give it. When you widen what a tool does, test the kind of case it was *never* built for — and expect the fix to be subtraction.

**🎤 For the room:**
> You design a gorgeous report template for your restaurant clients: "Menu Analysis," "Foot Traffic," "Local Competitors." It works beautifully — for restaurants. Then you take on a software client, and your system cheerfully generates them a "Menu Analysis" section, filled with nonsense, because that's the only template it knows. You never noticed, because until now every client was a restaurant.
>
> **Takeaway:** AI absorbs the assumptions baked into the examples you showed it. The moment you broaden your audience or use case, deliberately test the *new* kind — the one it was never shown. And notice: fixing this was mostly *removing* baked-in assumptions, not adding cleverness.
>
> **Discussion:** What assumptions are baked into how *you* brief your AI today — assumptions that come from your most common use case?

---

### Episode 12 — A phrase that's perfect for an essay is wrong for a search box

**🟦 In plain terms (for you):**
A research study found that prompting a model with "explore the mechanisms most people overlook" gets richer, less generic answers. The team wanted to use that. But the part of the system they wanted to use it in doesn't write essays — it generates *search queries* (the words you'd type into a search engine). "Mechanisms most people overlook" is a great *essay* instruction and a terrible *search query*. The AI itself flagged this during the thinking-it-through phase ("I'm least confident this phrasing fits search queries") — and the next phase rewrote it into search-appropriate wording and tested it before building.

**The lesson:** A prompt that works for one job doesn't copy-paste to another. Re-word it for the actual task — and reward the AI when it tells you what it's unsure about.

**🎤 For the room:**
> The words you'd write in an essay prompt are not the words you'd type into a Google search. "Explore the mechanisms most people overlook in X" is a wonderful essay starter and a useless search query. Copy-pasting a phrase that worked elsewhere, without adapting it to the job in front of you, quietly makes things worse.
>
> **Takeaway:** "Prompt best practices" are job-specific, not universal magic words. Always adapt borrowed phrasing to your actual task. And here's the healthy habit to model: this only went well because the AI *announced its own biggest doubt* ("I'm not sure this fits") — and that doubt got addressed before anything was built. Reward an AI (and a teammate) that says "here's what I'm least sure about."
>
> **Discussion:** Have you ever reused a prompt that "worked great last time" and gotten worse results — because the job was actually different?

---

## Bonus — two episodes about *reviewing* AI work (good for a Q&A or advanced segment)

### Episode 6 — The reviewer who remembers beats the reviewer who only sees today

**🟦 In plain terms (for you):**
A safety rule had locked a dependency to a specific, tested version. A later change quietly loosened it back to "use any version" — which would let the system silently jump to an untested future version. Someone reviewing only *today's* change sees nothing wrong. But a second AI reviewer cross-checked the project's own *history*, saw "we deliberately locked this down last month, on purpose," and blocked the loosening. A first reviewer caught it; a second confirmed the fix.

**🎤 For the room:**
> A safety lock got quietly unlocked. Anyone glancing at just *that* moment thinks "no problem, it's just an unlocked door." Only someone who knows *the door was deliberately locked last month, after an incident* understands why it matters.
>
> **Takeaway:** Some decisions carry invisible history. The best review of AI work isn't just a fresh pair of eyes — it's eyes that *remember why things are the way they are*. And a second independent reviewer is worth it when the stakes are real.

---

### Episode 8 — The "I'll get to it later" task that drifted for five rounds

**🟦 In plain terms (for you):**
A handful of "nice to have" tasks kept getting pushed to "next time" — one of them was deferred across five separate versions. The reason it kept getting deferred wasn't that it was wrong; it was missing *one specific thing* (a clear point at which it would actually be enforced). Once the team made a rule — "the second time something gets deferred, decide: do it or kill it" — the pile resolved fast: one task shipped, one was deliberately dropped because it turned out to be unnecessary.

**🎤 For the room:**
> The "I'll get to it" pile on your desk that never shrinks. A task survives there forever precisely because nobody ever decides its fate — deferring *feels* like a decision but it's actually avoiding one.
>
> **Takeaway:** AI-managed to-do lists accumulate zombie tasks the same way human ones do. The fix is a hard rule: the second time something slips, force the call — *do it or drop it*. "Later" is where work goes to never happen.

---

## Closing — Five things to remember about managing AI (plain version)

1. **Nothing complained ≠ it worked.** AI fails quietly and confidently. Check *what actually happened*, not just whether you got an error. *(Episodes 1, 2, 7)*
2. **It's not a tiny computer.** It can't tell time, can't be truly random, forgets written rules, and confidently makes up real-looking facts. Get real facts from real sources. *(Episodes 3, 4)*
3. **A bug that keeps coming back needs a guardrail, not a reminder.** Design the mistake out; don't keep asking everyone to be careful. *(Episode 5)*
4. **It over-builds by default.** Steer it to do *less*. "What's the simplest version?" is a power move. And check that a feature actually changes something before building it. *(Episodes 9, 10)*
5. **Brief it for your job; review it with memory.** Adapt borrowed prompts, test the cases it wasn't built for, force "do-it-or-drop-it" on stale tasks, and value a reviewer that remembers history. *(Episodes 6, 8, 11, 12)*

> Want the technical depth behind any of these? Each maps to a fully-traced episode in `AGENT_EPISODES.md`.
