"""Cycle configuration for research batch limits."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CycleConfig:
    """Configuration for a single research cycle's resource limits.

    Controls batch sizes and token budgets to prevent overload.
    Follows the frozen dataclass pattern from ResearchMode.
    """

    max_gaps_per_run: int = 5
    max_tokens_per_prompt: int = 100_000
    reserved_output_tokens: int = 4096
    default_ttl_days: int = 30

    def __post_init__(self) -> None:
        """Validate configuration."""
        errors = []

        if self.max_gaps_per_run < 1:
            errors.append(
                f"max_gaps_per_run must be >= 1, got {self.max_gaps_per_run}"
            )
        if self.max_tokens_per_prompt < 1000:
            errors.append(
                f"max_tokens_per_prompt must be >= 1000, got {self.max_tokens_per_prompt}"
            )
        if self.reserved_output_tokens < 256:
            errors.append(
                f"reserved_output_tokens must be >= 256, got {self.reserved_output_tokens}"
            )
        if self.default_ttl_days < 1:
            errors.append(
                f"default_ttl_days must be >= 1, got {self.default_ttl_days}"
            )
        if self.reserved_output_tokens >= self.max_tokens_per_prompt:
            errors.append(
                f"reserved_output_tokens ({self.reserved_output_tokens}) must be < "
                f"max_tokens_per_prompt ({self.max_tokens_per_prompt})"
            )

        if errors:
            raise ValueError(f"Invalid CycleConfig: {'; '.join(errors)}")
