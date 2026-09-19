"""
Heading-aware chunker for parsed PDF content.

Strategy: Split by Markdown headings (H1, H2, H3), then enforce
max token limits per chunk. Preserves section context in metadata.
"""
import re
from dataclasses import dataclass, field
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """A single retrievable unit of text."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# Regex for Markdown headings
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def chunk_by_headings(
    markdown: str,
    source_path: str,
    max_chunk_tokens: int = 512,
    min_chunk_tokens: int = 50,
) -> list[Chunk]:
    """
    Split Markdown into chunks at heading boundaries.

    Args:
        markdown: Full Markdown content from parser.
        source_path: Original PDF path (for metadata).
        max_chunk_tokens: Soft limit per chunk (tokens).
        min_chunk_tokens: Minimum size before merging with next section.

    Returns:
        List of Chunk objects with section metadata.
    """
    chunks: list[Chunk] = []

    # Find all heading positions
    headings = list(HEADING_PATTERN.finditer(markdown))

    if not headings:
        # No headings: fall back to single chunk or character split
        if _estimate_tokens(markdown) <= max_chunk_tokens:
            return [Chunk(text=markdown.strip(), metadata={"source": source_path})]
        return _split_by_paragraphs(markdown, source_path, max_chunk_tokens)

    # Build sections between headings
    sections: list[tuple[str, str, int]] = []  # (heading_text, content, level)

    for i, match in enumerate(headings):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown)
        content = markdown[start:end].strip()
        sections.append((heading_text, content, level))

    # Merge small sections and split large ones
    current_text = ""
    current_heading = ""
    current_level = 1

    for heading_text, content, level in sections:
        section_text = f"## {heading_text}\n\n{content}" if level > 1 else f"# {heading_text}\n\n{content}"
        section_tokens = _estimate_tokens(section_text)

        if section_tokens > max_chunk_tokens:
            # Flush current buffer first
            if current_text:
                chunks.append(Chunk(
                    text=current_text.strip(),
                    metadata={"source": source_path, "heading": current_heading, "level": current_level},
                ))
                current_text = ""

            # Split large section by paragraphs
            sub_chunks = _split_by_paragraphs(
                section_text, source_path, max_chunk_tokens,
                heading=heading_text, level=level,
            )
            chunks.extend(sub_chunks)
            current_heading = heading_text
            current_level = level

        elif _estimate_tokens(current_text + "\n\n" + section_text) > max_chunk_tokens:
            # Would exceed limit: flush and start new
            if current_text:
                chunks.append(Chunk(
                    text=current_text.strip(),
                    metadata={"source": source_path, "heading": current_heading, "level": current_level},
                ))
            current_text = section_text
            current_heading = heading_text
            current_level = level

        else:
            # Accumulate
            if current_text:
                current_text += "\n\n" + section_text
            else:
                current_text = section_text
                current_heading = heading_text
                current_level = level

    # Flush remaining
    if current_text and _estimate_tokens(current_text) >= min_chunk_tokens:
        chunks.append(Chunk(
            text=current_text.strip(),
            metadata={"source": source_path, "heading": current_heading, "level": current_level},
        ))
    elif current_text and chunks:
        # Merge small tail into last chunk
        chunks[-1].text += "\n\n" + current_text.strip()

    logger.info(
        "chunking_complete",
        extra={"source": source_path, "chunk_count": len(chunks)},
    )
    return chunks


def _split_by_paragraphs(
    text: str,
    source_path: str,
    max_chunk_tokens: int,
    heading: str = "",
    level: int = 1,
) -> list[Chunk]:
    """Fallback splitter for sections without sub-headings."""
    paragraphs = text.split("\n\n")
    chunks: list[Chunk] = []
    current = ""

    for para in paragraphs:
        if _estimate_tokens(current + "\n\n" + para) > max_chunk_tokens:
            if current:
                chunks.append(Chunk(
                    text=current.strip(),
                    metadata={"source": source_path, "heading": heading, "level": level},
                ))
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current:
        chunks.append(Chunk(
            text=current.strip(),
            metadata={"source": source_path, "heading": heading, "level": level},
        ))

    return chunks