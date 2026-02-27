"""Research mode configurations."""

from dataclasses import dataclass

# Single source of truth for the default Claude model across all modules.
DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Lightweight model for simple classification tasks (e.g., auto-detect context).
AUTO_DETECT_MODEL = "claude-haiku-4-5-20251001"


@dataclass(frozen=True)
class ResearchMode:
    """Configuration for a research mode."""
    name: str
    max_sources: int
    search_passes: int
    word_target: int
    max_tokens: int
    auto_save: bool
    synthesis_instructions: str
    pass1_sources: int  # Sources for first search pass
    pass2_sources: int  # Sources for refined query search
    # Relevance gate thresholds
    min_sources_full_report: int  # Minimum survivors for full report
    min_sources_short_report: int  # Minimum survivors for short report (below = insufficient)
    relevance_cutoff: int = 3  # Minimum score (1-5) for a source to be kept
    decompose: bool = True  # Whether to attempt query decomposition
    retry_sources_per_query: int = 3  # Sources per retry query during coverage gap retry
    cost_estimate: str = ""  # Estimated cost per query (e.g., "~$0.20")
    model: str = DEFAULT_MODEL  # Claude model for all API calls

    @property
    def is_quick(self) -> bool:
        return self.name == "quick"

    @property
    def is_standard(self) -> bool:
        return self.name == "standard"

    @property
    def is_deep(self) -> bool:
        return self.name == "deep"

    def __post_init__(self) -> None:
        """Validate mode configuration."""
        errors = []

        if self.pass1_sources < 1:
            errors.append(f"pass1_sources must be >= 1, got {self.pass1_sources}")
        if self.pass2_sources < 0:
            errors.append(f"pass2_sources must be >= 0, got {self.pass2_sources}")
        if self.max_sources < 1:
            errors.append(f"max_sources must be >= 1, got {self.max_sources}")
        if self.max_tokens < 100:
            errors.append(f"max_tokens must be >= 100, got {self.max_tokens}")
        if self.word_target < 50:
            errors.append(f"word_target must be >= 50, got {self.word_target}")
        if not self.name:
            errors.append("name cannot be empty")
        # Relevance gate validation
        if not (1 <= self.relevance_cutoff <= 5):
            errors.append(f"relevance_cutoff must be between 1 and 5, got {self.relevance_cutoff}")
        if self.min_sources_short_report < 1:
            errors.append(f"min_sources_short_report must be >= 1, got {self.min_sources_short_report}")
        if self.min_sources_short_report > self.min_sources_full_report:
            errors.append(
                f"min_sources_short_report ({self.min_sources_short_report}) must be <= "
                f"min_sources_full_report ({self.min_sources_full_report})"
            )
        if self.min_sources_full_report > self.max_sources:
            errors.append(
                f"min_sources_full_report ({self.min_sources_full_report}) must be <= "
                f"max_sources ({self.max_sources})"
            )

        if errors:
            raise ValueError(f"Invalid ResearchMode: {'; '.join(errors)}")

    @classmethod
    def quick(cls) -> "ResearchMode":
        return cls(
            name="quick",
            max_sources=4,  # Increased to account for relevance filtering
            search_passes=2,
            word_target=300,
            max_tokens=600,
            auto_save=False,
            synthesis_instructions=(
                "Provide a brief, focused summary. Skip detailed analysis. "
                "Prioritize the single most important answer to the query. "
                "Use 2-3 short paragraphs max. No subsections needed unless essential. "
                "Target approximately 300 words."
            ),
            pass1_sources=4,  # was 2
            pass2_sources=2,  # was 1
            min_sources_full_report=3,
            min_sources_short_report=1,
            relevance_cutoff=3,
            decompose=False,  # Skip decomposition for speed
            retry_sources_per_query=2,
            cost_estimate="~$0.12",
        )

    @classmethod
    def standard(cls) -> "ResearchMode":
        return cls(
            name="standard",
            max_sources=10,  # Increased to account for relevance filtering
            search_passes=2,
            word_target=2000,
            max_tokens=3000,
            auto_save=True,
            synthesis_instructions=(
                "Provide a balanced report with clear sections. "
                "Include key details and supporting context. "
                "Cite sources where relevant. "
                "Note competitive implications and positioning insights where applicable. "
                "Include a 'Limitations & Gaps' section discussing what the sources don't cover. "
                "Target approximately 2000 words."
            ),
            pass1_sources=6,  # was 4
            pass2_sources=4,  # was 3
            min_sources_full_report=4,
            min_sources_short_report=2,
            relevance_cutoff=3,
            cost_estimate="~$0.35",
        )

    @classmethod
    def deep(cls) -> "ResearchMode":
        return cls(
            name="deep",
            max_sources=12,  # Increased to account for relevance filtering
            search_passes=2,
            word_target=3500,
            max_tokens=8000,
            auto_save=True,
            synthesis_instructions=(
                "Provide a thorough, comprehensive analysis organized into the following sections. "
                "Use each section as a markdown ## heading. Omit a section only if no source data supports it.\n\n"
                "1. **Executive Summary** — 2-3 paragraph overview of key findings.\n"
                "2. **Company Overview** — Factual: founding, location, team size, years in business, certifications.\n"
                "3. **Service Portfolio** — Factual: services offered, pricing if found, packages, service area.\n"
                "4. **Marketing Positioning** — Factual + analytical: how the company positions itself, brand voice, "
                "taglines, unique selling propositions, stated differentiators.\n"
                "5. **Messaging Theme Analysis** — Identify 3-5 persuasion patterns used across their website, "
                "ads, and social profiles. Quote exact phrases where possible. Categorize themes "
                "(e.g., authority, social proof, scarcity, emotional appeal, expertise).\n"
                "6. **Buyer Psychology** — What fears, desires, and emotional triggers does their marketing "
                "target? What objections do they preemptively address? Draw from reviews and testimonials.\n"
                "7. **Content & Marketing Tactics** — SEO patterns, social media presence, review platform "
                "strategy, referral networks, paid advertising signals, content marketing approach.\n"
                "8. **Business Model Analysis** — Revenue structure, pricing strategy, competitive moats, "
                "scalability, vulnerabilities, partnership dependencies.\n"
                "9. **Competitive Implications** — What do these findings mean for the reader? "
                "Reference <research_context> if provided for specific positioning insights. "
                "Identify threats, opportunities, and gaps in the competitor's approach.\n"
                "10. **Positioning Advice** — 3-5 actionable angles the reader could pursue based on findings. "
                "Reference <research_context> if provided to tailor recommendations.\n"
                "11. **Adversarial Analysis** — Synthesize findings from the skeptic review. "
                "For each adversarial lens, summarize the key challenges to the analysis. "
                "Include a synthesis paragraph explaining how challenges were addressed.\n"
                "12. **Limitations & Gaps** — What the sources don't cover, confidence levels, areas needing further research.\n"
                "13. **Sources** — All referenced URLs with [Source N] notation.\n\n"
                "For sections 5-10: If source data is insufficient for this analysis, state that explicitly "
                "rather than speculating. Ground all claims in source evidence.\n\n"
                "Target approximately 3500 words."
            ),
            pass1_sources=12,  # was 10
            pass2_sources=12,  # was 10
            min_sources_full_report=8,  # Increased for deep mode
            min_sources_short_report=5,  # Increased for deep mode
            relevance_cutoff=3,
            retry_sources_per_query=5,
            cost_estimate="~$0.85",
        )

    @classmethod
    def from_name(cls, name: str) -> "ResearchMode":
        """Get a mode by name."""
        modes = {
            "quick": cls.quick,
            "standard": cls.standard,
            "deep": cls.deep,
        }
        if name not in modes:
            raise ValueError(f"Unknown mode: {name}. Valid modes: {list(modes.keys())}")
        return modes[name]()
