"""Fixed-size text chunker with overlap."""
from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap_ratio: float = 0.15,
) -> list[str]:
    """Split text into overlapping chunks by word count.

    Args:
        text: Input text.
        chunk_size: Target chunk size in words.
        overlap_ratio: Fraction of chunk_size to overlap between chunks.

    Returns:
        List of text chunks (may be empty if text is blank).
    """
    words = text.split()
    if not words:
        return []

    overlap = max(1, int(chunk_size * overlap_ratio))
    step = chunk_size - overlap

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step

    return chunks
