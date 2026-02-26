"""Text preparation for embedding generation."""

MAX_TEXT_LENGTH = 512  # Model's max sequence length


def prepare_text_for_embedding(
    title: str, summary: str | None, content: str | None
) -> str:
    """
    Prepare text for embedding generation.

    Strategy: title + " " + summary (fallback to content if summary missing)

    Args:
        title: News title
        summary: AI-generated summary from Cogfy (may be None for older news)
        content: Raw news content (fallback)

    Returns:
        Prepared text string
    """
    text_parts = [title.strip() if title else ""]

    if summary and summary.strip():
        text_parts.append(summary.strip())
    elif content and content.strip():
        text_parts.append(content.strip()[:500])

    text = " ".join(part for part in text_parts if part)

    # Truncate to model's max length (~4 chars per token estimate)
    if len(text) > MAX_TEXT_LENGTH * 4:
        text = text[: MAX_TEXT_LENGTH * 4]

    return text
