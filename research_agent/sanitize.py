"""Shared content sanitization for prompt injection defense."""

# Tag name used for research context blocks across all prompts.
CONTEXT_TAG = "research_context"


def sanitize_content(text: str) -> str:
    """
    Sanitize untrusted content before including in prompts.

    Escapes XML-like delimiters to prevent prompt injection attacks
    where malicious web content tries to break out of data sections.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_context_block(content: str | None) -> str:
    """Build an XML-wrapped research context block for LLM prompts.

    Args:
        content: Pre-sanitized context content, or None/empty to skip.

    Returns:
        XML block string, or empty string if no content.
    """
    if not content:
        return ""
    return f"\n<{CONTEXT_TAG}>\n{content}\n</{CONTEXT_TAG}>\n"
