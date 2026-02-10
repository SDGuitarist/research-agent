"""Shared content sanitization for prompt injection defense."""


def sanitize_content(text: str) -> str:
    """
    Sanitize untrusted content before including in prompts.

    Escapes XML-like delimiters to prevent prompt injection attacks
    where malicious web content tries to break out of data sections.
    """
    return text.replace("<", "&lt;").replace(">", "&gt;")
