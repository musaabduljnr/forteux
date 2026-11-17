"""
Document text extraction service.

Supports PDF (via pypdf), DOCX (via python-docx), and plain text/markdown.
Performs magic-byte MIME validation, resource limits, and scanned-PDF detection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING

EXTRACTOR_VERSION = "1.0.0"

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}

_PDF_MAGIC = b"%PDF"
_DOCX_MAGIC = b"PK\x03\x04"  # ZIP header

_MAX_PAGES = 500
_MAX_DECOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class ExtractedPage:
    page_num: int  # 1-indexed
    text: str
    char_count: int


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    page_count: int
    title: str | None
    warnings: list[str]
    extractor_version: str = EXTRACTOR_VERSION

    @property
    def total_chars(self) -> int:
        return sum(p.char_count for p in self.pages)

    @property
    def all_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())


class ExtractionError(Exception):
    """Raised when a document cannot be extracted."""


class DocumentExtractor:
    """Extract plain text from uploaded documents."""

    def extract(self, raw_bytes: bytes, mime_type: str, filename: str) -> ExtractionResult:
        if not raw_bytes:
            raise ExtractionError("Document is empty (zero bytes)")

        normalised_mime = mime_type.strip().lower().split(";")[0].strip()

        if normalised_mime not in SUPPORTED_MIME_TYPES:
            raise ExtractionError(
                f"Unsupported MIME type: {mime_type!r}. "
                f"Supported types: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
            )

        # Magic-byte validation
        if normalised_mime == "application/pdf":
            if not raw_bytes.startswith(_PDF_MAGIC):
                raise ExtractionError(
                    "File content does not match PDF format (missing %PDF header). "
                    "Ensure the uploaded file is a valid PDF."
                )
            return self._extract_pdf(raw_bytes)

        if normalised_mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if not raw_bytes.startswith(_DOCX_MAGIC):
                raise ExtractionError(
                    "File content does not match DOCX format (missing ZIP/PK header). "
                    "Ensure the uploaded file is a valid .docx document."
                )
            return self._extract_docx(raw_bytes)

        # text/plain or text/markdown
        return self._extract_txt(raw_bytes, filename)

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def _extract_pdf(self, raw_bytes: bytes) -> ExtractionResult:
        try:
            from pypdf import PdfReader
            from pypdf.errors import PdfReadError
        except ImportError:
            raise ExtractionError(
                "pypdf is not installed. Run: pip install pypdf==5.5.0"
            )

        warnings: list[str] = []

        try:
            reader = PdfReader(BytesIO(raw_bytes))
        except Exception as exc:
            raise ExtractionError(f"Could not open PDF: {exc}") from exc

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ExtractionError("PDF contains no pages")
        if total_pages > _MAX_PAGES:
            warnings.append(
                f"PDF has {total_pages} pages; only the first {_MAX_PAGES} were extracted."
            )
            total_pages = _MAX_PAGES

        pages: list[ExtractedPage] = []
        total_chars = 0

        for page_index in range(total_pages):
            if total_chars > _MAX_DECOMPRESSED_BYTES:
                warnings.append(
                    f"Extraction stopped at page {page_index + 1}: "
                    f"decompressed text exceeded {_MAX_DECOMPRESSED_BYTES // (1024 * 1024)} MB."
                )
                break

            try:
                page = reader.pages[page_index]
                text = page.extract_text() or ""
            except Exception as exc:
                warnings.append(f"Page {page_index + 1}: extraction error — {exc}")
                text = ""

            char_count = len(text)
            total_chars += char_count
            pages.append(ExtractedPage(page_num=page_index + 1, text=text, char_count=char_count))

        # Scanned-PDF detection: if average chars per page < 100
        actual_pages = len(pages)
        avg_chars = total_chars / actual_pages if actual_pages else 0
        if avg_chars < 100 and actual_pages > 0:
            warnings.append(
                "scanned_pdf_limited: This PDF appears to be scanned or image-based. "
                "Very little text could be extracted. OCR is not currently supported."
            )

        # Try to get metadata title
        title: str | None = None
        if reader.metadata and reader.metadata.title:
            title = str(reader.metadata.title).strip() or None

        return ExtractionResult(
            pages=pages,
            page_count=len(pages),
            title=title,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------------

    def _extract_docx(self, raw_bytes: bytes) -> ExtractionResult:
        try:
            import docx  # python-docx
        except ImportError:
            raise ExtractionError(
                "python-docx is not installed. Run: pip install python-docx==1.1.2"
            )

        warnings: list[str] = []

        try:
            doc = docx.Document(BytesIO(raw_bytes))
        except Exception as exc:
            raise ExtractionError(f"Could not open DOCX: {exc}") from exc

        # DOCX does not have page numbers natively; we treat it as a single "page"
        # and split into logical chunks by section breaks in the chunker.
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_texts:
                    paragraphs.append(" | ".join(row_texts))

        full_text = "\n\n".join(paragraphs)

        if not full_text.strip():
            raise ExtractionError("DOCX document contains no extractable text")

        if len(full_text) > _MAX_DECOMPRESSED_BYTES:
            full_text = full_text[:_MAX_DECOMPRESSED_BYTES]
            warnings.append(
                f"Document text truncated at {_MAX_DECOMPRESSED_BYTES // (1024 * 1024)} MB."
            )

        # Try to get title from core properties
        title: str | None = None
        try:
            core_props = doc.core_properties
            if core_props.title:
                title = str(core_props.title).strip() or None
        except Exception:
            pass

        page = ExtractedPage(page_num=1, text=full_text, char_count=len(full_text))
        return ExtractionResult(pages=[page], page_count=1, title=title, warnings=warnings)

    # ------------------------------------------------------------------
    # TXT / Markdown
    # ------------------------------------------------------------------

    def _extract_txt(self, raw_bytes: bytes, filename: str) -> ExtractionResult:
        warnings: list[str] = []

        # Try UTF-8 first, then latin-1 fallback
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("latin-1")
                warnings.append("File decoded as Latin-1 (not valid UTF-8).")
            except UnicodeDecodeError:
                raise ExtractionError("Could not decode file as text. Ensure the file is UTF-8 or Latin-1 encoded.")

        if not text.strip():
            raise ExtractionError("Text document contains no content")

        if len(text) > _MAX_DECOMPRESSED_BYTES:
            text = text[:_MAX_DECOMPRESSED_BYTES]
            warnings.append(f"Document text truncated at {_MAX_DECOMPRESSED_BYTES // (1024 * 1024)} MB.")

        page = ExtractedPage(page_num=1, text=text, char_count=len(text))
        return ExtractionResult(pages=[page], page_count=1, title=None, warnings=warnings)
