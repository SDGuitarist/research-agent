"""Coverage gap identification for iterative research loops."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Gap taxonomy
VALID_GAP_TYPES = frozenset({
    "QUERY_MISMATCH", "THIN_FOOTPRINT", "ABSENCE",
    "NONEXISTENT_SOURCE", "COVERAGE_GAP",
})
VALID_RECOMMENDATIONS = frozenset({"RETRY", "MAYBE_RETRY", "NO_RETRY"})
MAX_RETRY_QUERIES = 3

# Retry query limits
MIN_RETRY_QUERY_WORDS = 2
MAX_RETRY_QUERY_WORDS = 12


@dataclass(frozen=True)
class CoverageGap:
    """Result of coverage gap analysis."""
    gap_type: str              # QUERY_MISMATCH | THIN_FOOTPRINT | ABSENCE | NONEXISTENT_SOURCE | COVERAGE_GAP
    description: str           # Human-readable explanation of what's missing
    retry_recommendation: str  # RETRY | MAYBE_RETRY | NO_RETRY
    retry_queries: tuple[str, ...]  # Empty if NO_RETRY
    reasoning: str             # Why this gap type was chosen


_SAFE_DEFAULT = CoverageGap(
    gap_type="COVERAGE_GAP",
    description="Could not parse gap assessment",
    retry_recommendation="NO_RETRY",
    retry_queries=(),
    reasoning="Parse failure — skipping retry to avoid wasted API calls",
)

# Stop words excluded from overlap checks
_STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "of", "for", "and", "or",
    "to", "is", "how", "what", "why",
})


def _validate_retry_queries(
    queries: list[str],
    tried_queries: list[str] | None = None,
) -> list[str]:
    """Validate retry queries: word count, duplicates, overlap with tried queries."""
    valid = []
    tried_lower = [q.lower() for q in (tried_queries or [])]

    for q in queries:
        q = q.strip().strip('"').strip("'").strip("-").strip()
        if not q:
            continue

        word_count = len(q.split())
        if word_count < MIN_RETRY_QUERY_WORDS or word_count > MAX_RETRY_QUERY_WORDS:
            logger.warning(f"Retry query rejected (word count {word_count}): {q}")
            continue

        # Meaningful words for overlap checks
        q_words = set(q.lower().split()) - _STOP_WORDS
        if not q_words:
            continue

        # Check not too similar to tried queries
        too_similar = False
        for tried in tried_lower:
            tried_words = set(tried.split()) - _STOP_WORDS
            if not tried_words:
                continue
            overlap = len(q_words.intersection(tried_words))
            if overlap >= len(q_words) * 0.8:
                logger.warning(f"Retry query rejected (too similar to tried): {q}")
                too_similar = True
                break
        if too_similar:
            continue

        # Check for near-duplicates within valid list
        is_duplicate = False
        for existing in valid:
            existing_words = set(existing.lower().split()) - _STOP_WORDS
            overlap = len(q_words.intersection(existing_words))
            if overlap >= len(q_words) * 0.7:
                logger.warning(f"Retry query rejected (duplicate): {q}")
                is_duplicate = True
                break
        if is_duplicate:
            continue

        valid.append(q)

    return valid[:MAX_RETRY_QUERIES]


def _parse_gap_response(
    text: str,
    tried_queries: list[str] | None = None,
) -> CoverageGap:
    """Parse structured gap analysis response from Claude.

    Returns a valid CoverageGap in all cases — never raises.
    """
    if not text or not text.strip():
        return _SAFE_DEFAULT

    lines = text.strip().split("\n")

    gap_type = ""
    description = ""
    retry_recommendation = ""
    reasoning = ""
    raw_queries = []
    in_queries = False

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("GAP_TYPE:"):
            gap_type = stripped.split(":", 1)[1].strip().upper()
            in_queries = False
        elif stripped.upper().startswith("DESCRIPTION:"):
            description = stripped.split(":", 1)[1].strip()
            in_queries = False
        elif stripped.upper().startswith("RETRY_RECOMMENDATION:"):
            retry_recommendation = stripped.split(":", 1)[1].strip().upper()
            in_queries = False
        elif stripped.upper().startswith("REASONING:"):
            reasoning = stripped.split(":", 1)[1].strip()
            in_queries = False
        elif stripped.upper().startswith("RETRY_QUERIES:"):
            in_queries = True
        elif stripped.startswith("- ") and in_queries:
            raw_queries.append(stripped[2:].strip())

    # Validate gap type — default to COVERAGE_GAP if unrecognized
    if gap_type not in VALID_GAP_TYPES:
        if gap_type:
            logger.warning(f"Unknown gap type '{gap_type}', defaulting to COVERAGE_GAP")
        gap_type = "COVERAGE_GAP"

    # Validate recommendation — default to NO_RETRY if unrecognized
    if retry_recommendation not in VALID_RECOMMENDATIONS:
        if retry_recommendation:
            logger.warning(
                f"Unknown recommendation '{retry_recommendation}', defaulting to NO_RETRY"
            )
        retry_recommendation = "NO_RETRY"

    # Force empty queries for NO_RETRY
    if retry_recommendation == "NO_RETRY":
        validated_queries = ()
    else:
        validated = _validate_retry_queries(raw_queries, tried_queries)
        validated_queries = tuple(validated)

    if not description:
        description = "Gap assessment returned no description"

    return CoverageGap(
        gap_type=gap_type,
        description=description,
        retry_recommendation=retry_recommendation,
        retry_queries=validated_queries,
        reasoning=reasoning,
    )
