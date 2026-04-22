"""Vocabulary only — canonical tier names for synthesis prompts and future C33 parsing.

This does not define the C33 ClaimConfidence data model.
"""

EVIDENCE_TIERS: tuple[str, ...] = (
    "Documented",
    "Inferred",
    "Illustrative",
    "Speculative",
)

EVIDENCE_TIER_INSTRUCTION = (
    "Label every factual claim with one of these evidence tiers:\n"
    "- [Documented] — directly stated in a cited source\n"
    "- [Inferred] — reasonable inference from sources, not directly stated\n"
    "- [Illustrative] — example or analogy used to explain, not a finding\n"
    "- [Speculative] — plausible but unverifiable from available sources\n"
    "Place the label inline after the claim, e.g. "
    '"Company X reported $10M revenue [Documented]."'
)

EVIDENCE_TIER_REMINDER = (
    "Remember: every factual claim must carry one of these evidence-tier "
    "labels: [Documented], [Inferred], [Illustrative], [Speculative]."
)
