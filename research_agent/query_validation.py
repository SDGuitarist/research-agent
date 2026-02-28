"""Shared query validation utilities for decompose and coverage modules."""

import logging
import re

logger = logging.getLogger(__name__)

# Stop words excluded from overlap checks
STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "of", "for", "and", "or",
    "to", "is", "how", "what", "why",
})


# Search operators that could be injected via LLM-generated queries
_SEARCH_OPERATOR_RE = re.compile(
    r"\b(site|inurl|filetype|intitle|cache|related):", re.IGNORECASE
)
MAX_QUERY_LENGTH = 120


def strip_query(text: str, extra_chars: str = "") -> str:
    """Strip whitespace, quotes, hyphens, and optional extra characters."""
    text = text.strip().strip('"').strip("'").strip("-")
    for ch in extra_chars:
        text = text.strip(ch)
    return text.strip()


def meaningful_words(text: str) -> set[str]:
    """Extract meaningful words (lowercase, excluding stop words)."""
    return set(text.lower().split()) - STOP_WORDS


def has_near_duplicate(words: set[str], valid_list: list[str], threshold: float = 0.7) -> bool:
    """Check if words overlap with any existing entry above threshold."""
    for existing in valid_list:
        existing_words = meaningful_words(existing)
        overlap = len(words.intersection(existing_words))
        if overlap >= len(words) * threshold:
            return True
    return False


def validate_query_list(
    queries: list[str],
    *,
    min_words: int,
    max_words: int,
    max_results: int,
    reference_queries: list[str] | None = None,
    max_reference_overlap: float = 0.8,
    require_reference_overlap: bool = False,
    dedup_threshold: float = 0.7,
    extra_strip_chars: str = "",
    label: str = "Query",
) -> list[str]:
    """Validate a list of queries: strip, word count, overlap, dedup, truncate.

    Args:
        queries: Raw queries to validate
        min_words: Minimum word count
        max_words: Maximum word count
        max_results: Maximum queries to return
        reference_queries: Reject if too similar to any of these
        max_reference_overlap: Threshold for "too similar" to reference (0.0-1.0)
        require_reference_overlap: If True, reject queries sharing zero words with reference
        dedup_threshold: Threshold for near-duplicate detection within results
        extra_strip_chars: Additional characters to strip (e.g., "•")
        label: Label for log messages

    Returns:
        Validated, deduplicated list of queries.
    """
    valid = []
    ref_word_sets = [meaningful_words(q) for q in (reference_queries or [])]

    for q in queries:
        q = strip_query(q, extra_strip_chars)
        if not q:
            continue

        # Strip non-printable characters
        q = "".join(ch for ch in q if ch.isprintable())

        # Block search operators (defense against LLM prompt injection)
        if _SEARCH_OPERATOR_RE.search(q):
            logger.warning("%s rejected (search operator): %s", label, q)
            continue

        # Cap total length
        if len(q) > MAX_QUERY_LENGTH:
            logger.warning("%s rejected (too long, %d chars): %s", label, len(q), q)
            continue

        word_count = len(q.split())
        if word_count < min_words or word_count > max_words:
            logger.warning("%s rejected (word count %d): %s", label, word_count, q)
            continue

        q_words = meaningful_words(q)
        if not q_words:
            continue

        # Check overlap with reference queries
        skip = False
        for ref_words in ref_word_sets:
            if not ref_words:
                continue
            if require_reference_overlap and not q_words.intersection(ref_words):
                logger.warning("%s rejected (no overlap with reference): %s", label, q)
                skip = True
                break
            overlap = len(q_words.intersection(ref_words))
            if overlap >= len(q_words) * max_reference_overlap:
                logger.warning("%s rejected (too similar to reference): %s", label, q)
                skip = True
                break
        if skip:
            continue

        # Near-duplicate detection within valid list
        if has_near_duplicate(q_words, valid, dedup_threshold):
            logger.warning("%s rejected (duplicate): %s", label, q)
            continue

        valid.append(q)

    return valid[:max_results]
