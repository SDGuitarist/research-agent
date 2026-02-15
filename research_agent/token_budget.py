"""Token counting and budget allocation for synthesis prompts.

Provides token counting with graceful fallback and priority-based budget
allocation to prevent context window overflow (risk F5.2).
"""

from dataclasses import dataclass, field


def count_tokens(text: str, model: str = "claude-sonnet-4-20250514") -> int:
    """Count tokens in text using anthropic's token counting.

    Falls back to a conservative character-based estimate (1 token ≈ 4 chars)
    if the anthropic tokenizer is unavailable.
    """
    if not text:
        return 0

    # Conservative estimate: 1 token ≈ 4 characters.
    # Budget allocation is approximate — avoids per-call API round-trips.
    return max(1, len(text) // 4)


# Priority order for pruning (lowest priority number pruned first)
COMPONENT_PRIORITY: dict[str, int] = {
    "staleness_metadata": 1,  # Cut first
    "previous_baseline": 2,
    "gap_schema": 3,
    "business_context": 4,
    "sources": 5,  # Cut last — sources are the research
    "instructions": 6,  # Never cut — these control output quality
}


@dataclass(frozen=True)
class BudgetAllocation:
    """Result of budget allocation across prompt components."""

    allocations: dict[str, int]  # component -> allowed tokens
    pruned: list[str]  # components that were pruned
    total: int  # total tokens allocated


def allocate_budget(
    components: dict[str, str],
    max_tokens: int,
    reserved_output: int = 4096,
    priorities: dict[str, int] | None = None,
) -> BudgetAllocation:
    """Allocate token budget across prompt components.

    If total tokens exceed (max_tokens - reserved_output), prunes
    lowest-priority components first by truncating them.
    Each component keeps at least a minimum allocation (100 tokens)
    unless fully pruned.

    Args:
        components: component_name -> content text
        max_tokens: model context limit
        reserved_output: tokens reserved for model output
        priorities: override default priorities (higher number = higher priority)

    Returns:
        BudgetAllocation with per-component token counts.
    """
    if not components:
        return BudgetAllocation(allocations={}, pruned=[], total=0)

    available = max_tokens - reserved_output
    prio = priorities if priorities is not None else COMPONENT_PRIORITY

    # Count tokens for each component
    token_counts: dict[str, int] = {}
    for name, content in components.items():
        token_counts[name] = count_tokens(content)

    total_needed = sum(token_counts.values())

    # If everything fits, no pruning needed
    if total_needed <= available:
        return BudgetAllocation(
            allocations=dict(token_counts),
            pruned=[],
            total=total_needed,
        )

    # Need to prune — sort components by priority (lowest first = pruned first)
    # Components not in priority map get priority 0 (pruned before everything)
    sorted_components = sorted(
        token_counts.keys(),
        key=lambda name: prio.get(name, 0),
    )

    pruned: list[str] = []
    allocations: dict[str, int] = dict(token_counts)
    current_total = total_needed
    min_allocation = 100

    for name in sorted_components:
        if current_total <= available:
            break

        # Never prune components with highest priority (6 = instructions)
        if prio.get(name, 0) >= 6:
            continue

        overshoot = current_total - available
        component_tokens = allocations[name]

        if component_tokens <= min_allocation:
            # Already at or below minimum — fully prune
            current_total -= component_tokens
            allocations[name] = 0
            pruned.append(name)
        elif component_tokens - overshoot >= min_allocation:
            # Truncating this component is enough to fit
            allocations[name] = component_tokens - overshoot
            current_total -= overshoot
            pruned.append(name)
        else:
            # Truncate to minimum, continue pruning next component
            reduction = component_tokens - min_allocation
            allocations[name] = min_allocation
            current_total -= reduction
            pruned.append(name)

    # Remove zero-allocation components
    allocations = {k: v for k, v in allocations.items() if v > 0}

    return BudgetAllocation(
        allocations=allocations,
        pruned=pruned,
        total=sum(allocations.values()),
    )


def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget.

    Uses the conservative 4-chars-per-token estimate for truncation
    (avoids an API call per truncation). Appends "[truncated]" marker
    when content is cut.

    Args:
        text: Content to potentially truncate.
        max_tokens: Maximum allowed tokens.

    Returns:
        Original text if within budget, truncated text otherwise.
    """
    if not text:
        return text
    current = count_tokens(text)
    if current <= max_tokens:
        return text
    # Truncate by character estimate (conservative: 4 chars/token)
    max_chars = max_tokens * 4
    return text[:max_chars] + "\n\n[Content truncated to fit token budget]"
