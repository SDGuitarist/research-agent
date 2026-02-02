"""Chunk summarization using Claude Haiku."""

import asyncio
from dataclasses import dataclass

from anthropic import AsyncAnthropic, RateLimitError, APIError

from .extract import ExtractedContent


@dataclass
class Summary:
    """A summary of a content chunk."""
    url: str
    title: str
    summary: str


# Chunk size in characters (roughly 1000 tokens)
CHUNK_SIZE = 4000
MAX_CHUNKS_PER_SOURCE = 3


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks, trying to break at paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    current_pos = 0

    while current_pos < len(text):
        end_pos = current_pos + chunk_size

        if end_pos >= len(text):
            chunks.append(text[current_pos:])
            break

        # Try to find a paragraph break
        break_pos = text.rfind("\n\n", current_pos, end_pos)
        if break_pos == -1 or break_pos <= current_pos:
            # Try single newline
            break_pos = text.rfind("\n", current_pos, end_pos)
        if break_pos == -1 or break_pos <= current_pos:
            # Try space
            break_pos = text.rfind(" ", current_pos, end_pos)
        if break_pos == -1 or break_pos <= current_pos:
            # Force break
            break_pos = end_pos

        chunks.append(text[current_pos:break_pos])
        current_pos = break_pos + 1

    return chunks[:MAX_CHUNKS_PER_SOURCE]


async def summarize_chunk(
    client: AsyncAnthropic,
    chunk: str,
    url: str,
    title: str,
    model: str = "claude-sonnet-4-20250514",
) -> Summary | None:
    """Summarize a single chunk of content."""
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Summarize the key information from this content in 2-4 sentences. Focus on facts, findings, and actionable information. Be concise.

Title: {title}
URL: {url}

Content:
{chunk}

Summary:"""
            }]
        )

        summary_text = response.content[0].text.strip()

        return Summary(
            url=url,
            title=title,
            summary=summary_text,
        )

    except RateLimitError:
        raise
    except (APIError, Exception):
        return None


async def summarize_content(
    client: AsyncAnthropic,
    content: ExtractedContent,
    model: str = "claude-sonnet-4-20250514",
) -> list[Summary]:
    """
    Summarize extracted content, chunking if necessary.

    Args:
        client: Anthropic client
        content: Extracted content to summarize
        model: Model to use for summarization

    Returns:
        List of summaries (one per chunk)
    """
    chunks = _chunk_text(content.text)

    summaries = []
    for chunk in chunks:
        summary = await summarize_chunk(
            client=client,
            chunk=chunk,
            url=content.url,
            title=content.title,
            model=model,
        )
        if summary:
            summaries.append(summary)

    return summaries


async def summarize_all(
    client: AsyncAnthropic,
    contents: list[ExtractedContent],
    model: str = "claude-sonnet-4-20250514",
) -> list[Summary]:
    """
    Summarize multiple pieces of content in parallel.

    Args:
        client: Anthropic client
        contents: List of extracted content
        model: Model to use

    Returns:
        List of all summaries
    """
    tasks = [summarize_content(client, content, model) for content in contents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_summaries = []
    for result in results:
        if isinstance(result, list):
            all_summaries.extend(result)

    return all_summaries
