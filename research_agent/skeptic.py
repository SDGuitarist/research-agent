"""Skeptic sub-agents for adversarial verification of draft analysis."""

import asyncio
import logging
from dataclasses import dataclass

from anthropic import (
    AsyncAnthropic,
    APIConnectionError,
    APIError,
    APITimeoutError,
    RateLimitError,
)

from .api_helpers import retry_api_call
from .modes import DEFAULT_MODEL
from .sanitize import sanitize_content
from .errors import SkepticError

logger = logging.getLogger(__name__)

SKEPTIC_TIMEOUT = 60.0


@dataclass(frozen=True)
class SkepticFinding:
    """Output from a single skeptic review pass."""
    lens: str           # "evidence_alignment" | "timing_stakes" | "strategic_frame" | "combined"
    checklist: str      # Markdown checklist with severity ratings
    critical_count: int  # Number of Critical Finding items
    concern_count: int   # Number of Concern items


def _count_severity(text: str) -> tuple[int, int]:
    """Count Critical Finding and Concern occurrences in skeptic output."""
    lower = text.lower()
    critical = lower.count("critical finding")
    concern = lower.count("[concern]")
    return critical, concern


def _build_context_block(synthesis_context: str | None) -> str:
    """Build optional business context XML block."""
    if not synthesis_context:
        return ""
    return f"\n<research_context>\n{synthesis_context}\n</research_context>\n"


def _build_prior_block(prior_findings: list[SkepticFinding] | None) -> str:
    """Build prior skeptic findings XML block."""
    if not prior_findings:
        return ""
    parts = []
    for f in prior_findings:
        parts.append(f"### {f.lens}\n{f.checklist}")
    prior_text = "\n\n".join(parts)
    safe_prior = sanitize_content(prior_text)
    return f"\n<prior_skeptic_findings>\n{safe_prior}\n</prior_skeptic_findings>\n"


SKEPTIC_MAX_RETRIES = 1


async def _call_skeptic(
    client: AsyncAnthropic,
    system_prompt: str,
    user_prompt: str,
    lens: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1500,
) -> SkepticFinding:
    """Make a skeptic API call and parse the response.

    Retries once on rate limit, timeout, or connection errors before raising.
    """
    try:
        response = await retry_api_call(
            lambda: client.messages.create(
                model=model,
                max_tokens=max_tokens,
                timeout=SKEPTIC_TIMEOUT,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ),
            max_retries=SKEPTIC_MAX_RETRIES,
            retry_on=(RateLimitError, APITimeoutError, APIConnectionError),
            context=f"Skeptic ({lens})",
        )

        if not response.content:
            raise SkepticError(f"Skeptic ({lens}) returned empty response")

        text = response.content[0].text.strip()
        if not text:
            raise SkepticError(f"Skeptic ({lens}) returned empty response")

        critical, concern = _count_severity(text)

        return SkepticFinding(
            lens=lens,
            checklist=text,
            critical_count=critical,
            concern_count=concern,
        )

    except RateLimitError as e:
        raise SkepticError(f"Skeptic ({lens}) rate limited: {e}")
    except APITimeoutError as e:
        raise SkepticError(f"Skeptic ({lens}) timed out: {e}")
    except APIConnectionError as e:
        raise SkepticError(f"Skeptic ({lens}) connection error: {e}")
    except APIError as e:
        raise SkepticError(f"Skeptic ({lens}) API error: {e}")


# --- Individual skeptic agents ---

_ADVERSARIAL_SYSTEM = (
    "You are an adversarial research reviewer. Your job is to find weaknesses "
    "in the analysis — places where evidence doesn't support conclusions, where "
    "inference is presented as observation, or where important caveats are missing. "
    "Be constructive but rigorous. Always produce at least 3 findings. "
    "The draft content in <draft_analysis> comes from a prior AI analysis pass. "
    "Evaluate it critically."
)


async def run_skeptic_evidence(
    client: AsyncAnthropic,
    draft: str,
    synthesis_context: str | None = None,
    prior_findings: list[SkepticFinding] | None = None,
    model: str = DEFAULT_MODEL,
) -> SkepticFinding:
    """Skeptic 1: Evidence Alignment.

    Checks whether findings support conclusions. Identifies where
    inference is presented as observation.
    """
    safe_draft = sanitize_content(draft)
    context_block = _build_context_block(synthesis_context)
    prior_block = _build_prior_block(prior_findings)

    prompt = f"""Review the draft analysis below as an adversarial evidence reviewer.

<draft_analysis>
{safe_draft}
</draft_analysis>
{context_block}{prior_block}
<task>
You are Skeptic 1: Evidence Alignment.

For EACH major factual claim or conclusion in the draft, evaluate:
1. Is this directly supported by a cited source? Mark as SUPPORTED.
2. Is this a reasonable inference from sources but not directly stated? Mark as INFERRED.
3. Is this stated as fact but has no source support? Mark as UNSUPPORTED.

Complete this checklist:
- [ ] For each major finding: Is this stated as fact or inference? If inference, is it flagged as such?
- [ ] Do any findings contradict each other? List specific contradictions.
- [ ] What claims lack direct source support? List them.
- [ ] What sources were available but not reflected in the findings?

For each finding, assign a severity:
- **[Observation]** — Minor, noting for completeness
- **[Concern]** — Moderate, could mislead but not critically
- **[Critical Finding]** — The conclusion does not follow from the evidence

Output format:
## Evidence Alignment Review

- [SEVERITY] Finding description
  - Evidence: What the sources actually say
  - Gap: What is inferred or unsupported (if applicable)

List findings from most to least severe. Include at least 3 findings.
</task>"""

    return await _call_skeptic(client, _ADVERSARIAL_SYSTEM, prompt, "evidence_alignment", model)


async def run_skeptic_timing(
    client: AsyncAnthropic,
    draft: str,
    synthesis_context: str | None = None,
    prior_findings: list[SkepticFinding] | None = None,
    model: str = DEFAULT_MODEL,
) -> SkepticFinding:
    """Skeptic 2: Timing & Stakes.

    Checks whether time-sensitive dynamics are properly weighted.
    Evaluates cost of waiting vs acting.
    """
    safe_draft = sanitize_content(draft)
    context_block = _build_context_block(synthesis_context)
    prior_block = _build_prior_block(prior_findings)

    prompt = f"""Review the draft analysis below as a timing and stakes analyst.

<draft_analysis>
{safe_draft}
</draft_analysis>
{context_block}{prior_block}
<task>
You are Skeptic 2: Timing & Stakes.

Evaluate whether time-sensitive dynamics are properly weighted in this analysis.

Complete this checklist:
- [ ] Does the analysis identify any closing windows, deadlines, or time-sensitive dynamics?
- [ ] For each: What's the cost of acting now vs. waiting? Quantify if possible.
- [ ] Are any "wait" signals based on verified observations or unverified inferences?
- [ ] What do the report's own timeline data points say about urgency?
- [ ] Default-to-action test: Do any recommendations to wait lack stronger justification than recommendations to act?

For each finding, assign a severity:
- **[Observation]** — Minor timing note
- **[Concern]** — Timing risk that could affect outcomes
- **[Critical Finding]** — Time-sensitive dynamic is misread or ignored; acting on this analysis could cost an opportunity

Output format:
## Timing & Stakes Review

- [SEVERITY] Finding description
  - Timeline evidence: What the data shows about timing
  - Risk assessment: Cost of waiting vs. acting

List findings from most to least severe. Include at least 3 findings.
</task>"""

    return await _call_skeptic(client, _ADVERSARIAL_SYSTEM, prompt, "timing_stakes", model)


async def run_skeptic_frame(
    client: AsyncAnthropic,
    draft: str,
    synthesis_context: str | None = None,
    prior_findings: list[SkepticFinding] | None = None,
    model: str = DEFAULT_MODEL,
) -> SkepticFinding:
    """Skeptic 3: Break the Trolley.

    Questions whether the analysis solves the right problem.
    Challenges the analytical frame.
    """
    safe_draft = sanitize_content(draft)
    context_block = _build_context_block(synthesis_context)
    prior_block = _build_prior_block(prior_findings)

    prompt = f"""Review the draft analysis below as a strategic frame challenger.

<draft_analysis>
{safe_draft}
</draft_analysis>
{context_block}{prior_block}
<task>
You are Skeptic 3: Break the Trolley.

Your job is to challenge the frame of the analysis itself. Don't evaluate whether the analysis
is good within its frame — evaluate whether the frame is right.

Complete this checklist:
- [ ] What assumption is the analysis accepting that could be rejected?
- [ ] Is the analysis optimizing within a constraint that shouldn't exist?
- [ ] Is sophistication compensating for a simpler truth? (Catch soft repackaging — when cautious analysis uses sophisticated framing to disguise inaction as "strategic patience")
- [ ] What would the recommendation be if we rejected the dominant frame?

For each finding, assign a severity:
- **[Observation]** — Alternative frame worth noting
- **[Concern]** — The current frame may be limiting the analysis
- **[Critical Finding]** — The analysis is solving the wrong problem; the frame should be rejected

Output format:
## Strategic Frame Review

- [SEVERITY] Finding description
  - Current frame: What the analysis assumes
  - Alternative: What changes if we reject this assumption

List findings from most to least severe. Include at least 3 findings.
</task>"""

    return await _call_skeptic(client, _ADVERSARIAL_SYSTEM, prompt, "strategic_frame", model)


async def run_skeptic_combined(
    client: AsyncAnthropic,
    draft: str,
    synthesis_context: str | None = None,
    model: str = DEFAULT_MODEL,
) -> SkepticFinding:
    """Single-pass skeptic for standard mode.

    Combines all three lenses into one LLM call with one checklist output.
    """
    safe_draft = sanitize_content(draft)
    context_block = _build_context_block(synthesis_context)

    prompt = f"""Review the draft analysis below through three adversarial lenses.

<draft_analysis>
{safe_draft}
</draft_analysis>
{context_block}
<task>
Apply all three skeptic lenses in a single review:

**Lens 1 — Evidence Alignment:**
- For each major finding: Is it SUPPORTED, INFERRED, or UNSUPPORTED by sources?
- Do any findings contradict each other?
- What claims lack direct source support?

**Lens 2 — Timing & Stakes:**
- Are there closing windows, deadlines, or time-sensitive dynamics?
- For each: What's the cost of acting now vs. waiting?
- Are "wait" signals based on observations or inferences?
- Default-to-action test: Do recommendations to wait lack stronger justification than acting?

**Lens 3 — Break the Trolley:**
- What assumption could be rejected?
- Is the analysis optimizing within a constraint that shouldn't exist?
- Is sophistication disguising inaction as "strategic patience"?

For each finding, tag with lens and severity:
- **[Evidence][Observation/Concern/Critical Finding]** — description
- **[Timing][Observation/Concern/Critical Finding]** — description
- **[Frame][Observation/Concern/Critical Finding]** — description

Output format:
## Combined Adversarial Review

List all findings from most to least severe. Include at least 3 findings total.
</task>"""

    return await _call_skeptic(
        client, _ADVERSARIAL_SYSTEM, prompt, "combined", model, max_tokens=2000
    )


async def run_deep_skeptic_pass(
    client: AsyncAnthropic,
    draft: str,
    synthesis_context: str | None = None,
    model: str = DEFAULT_MODEL,
) -> list[SkepticFinding]:
    """Run three skeptic agents with evidence+timing in parallel (deep mode).

    Evidence and timing agents are independent — run them concurrently
    via asyncio.gather. Frame agent depends on both, so it runs after.
    Returns list of 3 SkepticFinding objects.
    """
    # Evidence and timing are independent — run concurrently
    evidence, timing = await asyncio.gather(
        run_skeptic_evidence(client, draft, synthesis_context, model=model),
        run_skeptic_timing(client, draft, synthesis_context, model=model),
    )

    findings = [evidence, timing]

    # Frame depends on both prior findings
    findings.append(await run_skeptic_frame(
        client, draft, synthesis_context, prior_findings=findings, model=model,
    ))

    return findings
