"""Shared query validation utilities for decompose and coverage modules."""

import logging
import re

from .errors import VagueQueryError

logger = logging.getLogger(__name__)

# Stop words excluded from overlap checks
STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "of", "for", "and", "or",
    "to", "is", "are", "how", "what", "why", "do", "does",
})


# Search operators that could be injected via LLM-generated queries
_SEARCH_OPERATOR_RE = re.compile(
    r"\b(site|inurl|filetype|intitle|cache|related):", re.IGNORECASE
)
MAX_QUERY_LENGTH = 120


_PUNCTUATION_CHARS = ",.?!;:\"'()[]"


def check_query_not_vague(query: str) -> None:
    """Reject queries too vague to produce useful research results.

    This is a UX quality gate, not a security control. Raises
    VagueQueryError if the query has fewer than 2 meaningful words
    (after stopword removal), unless the single word is a proper noun
    or acronym (starts uppercase or is all-caps with length >= 2).

    The proper-noun check uses the original token before lowercasing,
    with surrounding punctuation/quotes stripped first.
    """
    stripped = query.strip()
    if not stripped:
        raise VagueQueryError(
            "Query too vague for research. Please add specific terms "
            "— e.g., 'climate change policy' instead of 'stuff'."
        )

    words = meaningful_words(stripped)

    if len(words) >= 2:
        return  # enough content words

    if len(words) == 1:
        # Check original tokens for proper-noun/acronym heuristic
        for token in stripped.split():
            clean = token.strip(_PUNCTUATION_CHARS)
            if not clean:
                continue
            clean_lower = clean.lower()
            if clean_lower in STOP_WORDS:
                continue
            # This is the meaningful word — check original casing
            if clean[0].isupper() or (len(clean) >= 2 and clean.isupper()):
                return  # proper noun or acronym

    raise VagueQueryError(
        "Query too vague for research. Please add specific terms "
        "— e.g., 'climate change policy' instead of 'stuff'."
    )


def strip_query(text: str, extra_chars: str = "") -> str:
    """Strip whitespace, quotes, hyphens, and optional extra characters."""
    text = text.strip().strip('"').strip("'").strip("-")
    for ch in extra_chars:
        text = text.strip(ch)
    return text.strip()


def meaningful_words(text: str) -> set[str]:
    """Extract meaningful words (lowercase, stripped of punctuation, excluding stop words).

    Hyphenated words are included both whole and as components,
    so 'post-quantum' matches both 'post-quantum' and 'quantum'.
    """
    words = set()
    for w in text.lower().split():
        w = w.strip(",.?!;:\"'()[]")
        if w:
            words.add(w)
            if "-" in w:
                words.update(part for part in w.split("-") if part)
    return words - STOP_WORDS


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
