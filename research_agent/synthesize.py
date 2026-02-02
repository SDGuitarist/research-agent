"""Report synthesis using Claude Sonnet."""

from anthropic import Anthropic, RateLimitError, APIError

from .summarize import Summary
from .errors import SynthesisError


def synthesize_report(
    client: Anthropic,
    query: str,
    summaries: list[Summary],
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """
    Synthesize a research report from summaries.

    Args:
        client: Anthropic client
        query: Original research query
        summaries: List of source summaries
        model: Model to use for synthesis

    Returns:
        Markdown report string

    Raises:
        SynthesisError: If synthesis fails
    """
    if not summaries:
        raise SynthesisError("No summaries to synthesize")

    # Build sources context
    sources_text = _build_sources_context(summaries)

    # Build the prompt
    prompt = f"""You are a research assistant. Based on the following source summaries, write a comprehensive research report answering this query:

**Query:** {query}

## Source Summaries

{sources_text}

## Instructions

Write a well-structured markdown report that:
1. Directly answers the query with a clear summary at the top
2. Organizes findings into logical sections with headers
3. Cites sources using [Source N] notation where N corresponds to the source number above
4. Notes any conflicting information or gaps in the research
5. Ends with a "Sources" section listing all referenced URLs

Keep the report focused and concise (500-1500 words). Use bullet points for lists of items.

## Report
"""

    try:
        # Use streaming for longer responses
        full_response = ""

        with client.messages.stream(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                print(text, end="", flush=True)

        print()  # Newline after streaming
        return full_response.strip()

    except RateLimitError as e:
        raise SynthesisError(f"Rate limited: {e}")
    except APIError as e:
        raise SynthesisError(f"API error: {e}")
    except Exception as e:
        raise SynthesisError(f"Synthesis failed: {e}")


def _build_sources_context(summaries: list[Summary]) -> str:
    """Build formatted sources context for the prompt."""
    # Group summaries by URL to consolidate multiple chunks from same source
    by_url: dict[str, list[Summary]] = {}
    for s in summaries:
        if s.url not in by_url:
            by_url[s.url] = []
        by_url[s.url].append(s)

    parts = []
    for i, (url, url_summaries) in enumerate(by_url.items(), 1):
        title = url_summaries[0].title or "Untitled"
        combined_summary = " ".join(s.summary for s in url_summaries)

        parts.append(f"""**[Source {i}]** {title}
URL: {url}
Summary: {combined_summary}
""")

    return "\n".join(parts)
