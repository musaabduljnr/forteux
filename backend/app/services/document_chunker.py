"""
Document chunking service.

Splits extracted pages into overlapping chunks with:
- Paragraph-boundary awareness
- Page reference tracking
- Section heading detection and injection
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.document_extractor import ExtractedPage

_HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Z0-9 \t]{2,78}[A-Z0-9])$")


def _is_heading(line: str) -> bool:
    """Return True if the line looks like a section heading."""
    stripped = line.strip()
    if not stripped:
        return False
    # Markdown headings
    if re.match(r"^#{1,6}\s+\S", stripped):
        return True
    # ALL-CAPS short line (3-80 chars, no lowercase)
    if 3 <= len(stripped) <= 80 and stripped == stripped.upper() and re.search(r"[A-Z]", stripped):
        return True
    return False


@dataclass
class Chunk:
    chunk_index: int
    text: str
    page_start: int | None  # 1-indexed page number
    page_end: int | None
    section_heading: str | None
    char_count: int


class DocumentChunker:
    """Split a list of ExtractedPages into overlapping text chunks."""

    def chunk(
        self,
        pages: list[ExtractedPage],
        chunk_size: int = 1200,
        overlap: int = 150,
        min_chunk: int = 20,
    ) -> list[Chunk]:
        """
        Produce a list of Chunk objects from extracted pages.

        Strategy:
        1. Split each page's text on paragraph boundaries (double newlines).
        2. Accumulate paragraphs into chunks of ~chunk_size characters.
        3. Add overlap from the previous chunk at the start of each new chunk.
        4. Track page numbers and section headings.
        """
        if not pages:
            return []

        # Build list of (page_num, paragraph_text) with heading detection
        segments: list[tuple[int, str]] = []
        for page in pages:
            paragraphs = re.split(r"\n{2,}", page.text)
            for para in paragraphs:
                stripped = para.strip()
                if stripped:
                    segments.append((page.page_num, stripped))

        if not segments:
            return []

        chunks: list[Chunk] = []
        chunk_index = 0
        current_text = ""
        current_heading: str | None = None
        current_page_start: int | None = None
        current_page_end: int | None = None
        overlap_text = ""

        def _flush(text: str, heading: str | None, ps: int | None, pe: int | None) -> None:
            nonlocal chunk_index
            if len(text.strip()) < min_chunk:
                return
            chunks.append(
                Chunk(
                    chunk_index=chunk_index,
                    text=text.strip(),
                    page_start=ps,
                    page_end=pe,
                    section_heading=heading,
                    char_count=len(text.strip()),
                )
            )
            chunk_index += 1

        for page_num, para in segments:
            # Detect heading
            if _is_heading(para):
                current_heading = para

            # First segment initialises state
            if current_page_start is None:
                current_page_start = page_num

            current_page_end = page_num

            # Would adding this paragraph overflow the chunk?
            addition = ("\n\n" + para) if current_text else para
            if current_text and len(current_text) + len(addition) > chunk_size:
                # Flush current chunk
                _flush(current_text, current_heading, current_page_start, current_page_end)
                # Carry overlap
                if len(current_text) > overlap:
                    overlap_text = current_text[-overlap:]
                else:
                    overlap_text = current_text
                current_text = (overlap_text + "\n\n" + para).strip()
                current_page_start = page_num
                current_page_end = page_num
            else:
                current_text = (current_text + "\n\n" + para).strip() if current_text else para

        # Flush remaining
        _flush(current_text, current_heading, current_page_start, current_page_end)

        return chunks
