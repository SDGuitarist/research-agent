"""Research mode configurations."""

from dataclasses import dataclass


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

        if errors:
            raise ValueError(f"Invalid ResearchMode: {'; '.join(errors)}")

    @classmethod
    def quick(cls) -> "ResearchMode":
        return cls(
            name="quick",
            max_sources=3,
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
            pass1_sources=2,
            pass2_sources=1,
        )

    @classmethod
    def standard(cls) -> "ResearchMode":
        return cls(
            name="standard",
            max_sources=7,
            search_passes=2,
            word_target=1000,
            max_tokens=1800,
            auto_save=True,
            synthesis_instructions=(
                "Provide a balanced report with clear sections. "
                "Include key details and supporting context. "
                "Cite sources where relevant. "
                "Target approximately 1000 words."
            ),
            pass1_sources=4,
            pass2_sources=3,
        )

    @classmethod
    def deep(cls) -> "ResearchMode":
        return cls(
            name="deep",
            max_sources=10,
            search_passes=2,
            word_target=2000,
            max_tokens=3500,
            auto_save=True,
            synthesis_instructions=(
                "Provide a thorough, comprehensive analysis. "
                "Include nuanced discussion of conflicting viewpoints. "
                "Add a 'Limitations & Gaps' section discussing what the sources don't cover. "
                "Discuss confidence levels where appropriate. "
                "Explore edge cases and caveats mentioned in sources. "
                "Target approximately 2000 words."
            ),
            pass1_sources=10,
            pass2_sources=10,
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
