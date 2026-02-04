"""Research mode configurations."""

from dataclasses import dataclass
from enum import Enum


class ResearchModeType(Enum):
    """Available research modes."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


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

    @classmethod
    def quick(cls) -> "ResearchMode":
        return cls(
            name="quick",
            max_sources=3,
            search_passes=1,
            word_target=300,
            max_tokens=600,
            auto_save=False,
            synthesis_instructions=(
                "Provide a brief, focused summary. Skip detailed analysis. "
                "Prioritize the single most important answer to the query. "
                "Use 2-3 short paragraphs max. No subsections needed unless essential. "
                "Target approximately 300 words."
            ),
        )

    @classmethod
    def standard(cls) -> "ResearchMode":
        return cls(
            name="standard",
            max_sources=7,
            search_passes=1,
            word_target=1000,
            max_tokens=1800,
            auto_save=False,
            synthesis_instructions=(
                "Provide a balanced report with clear sections. "
                "Include key details and supporting context. "
                "Cite sources where relevant. "
                "Target approximately 1000 words."
            ),
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
