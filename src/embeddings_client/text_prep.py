"""Text preparation for embedding generation."""

# BGE-M3: 8192 tokens max
# Using 24,000 chars as conservative limit (~3 chars per token)
MAX_TEXT_LENGTH_CHARS = 24000


def prepare_text_for_embedding(
    title: str, summary: str | None, content: str | None
) -> str:
    """
    Prepare text for embedding generation.

    Strategy: title + " " + summary (fallback to content if summary missing)

    BGE-M3 supports up to 8192 tokens (~24-32k chars).
    We use 24k chars as a safe limit.

    Args:
        title: News title
        summary: AI-generated summary from Cogfy (may be None for older news)
        content: Raw news content (fallback)

    Returns:
        Prepared text string (truncated to MAX_TEXT_LENGTH_CHARS)
    """
    text_parts = [title.strip() if title else ""]

    if summary and summary.strip():
        text_parts.append(summary.strip())
    elif content and content.strip():
        # Use more content than before (24k instead of 500 chars)
        # Will be truncated below if exceeds limit
        text_parts.append(content.strip())

    text = " ".join(part for part in text_parts if part)

    # Truncate to model's max length
    if len(text) > MAX_TEXT_LENGTH_CHARS:
        text = text[:MAX_TEXT_LENGTH_CHARS]

    return text
