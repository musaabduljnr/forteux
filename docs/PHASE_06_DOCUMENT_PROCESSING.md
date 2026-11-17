# Phase 06 Document Processing

## 1. Document Extraction Pipeline

The document extraction subsystem is implemented in `backend/app/services/document_extractor.py` and supports four standard file formats:
- **PDF** (`application/pdf`) via `pypdf 5.5.0`
- **DOCX** (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`) via `python-docx 1.1.2`
- **Plain Text** (`text/plain`) via Python UTF-8/Latin-1 decoders
- **Markdown** (`text/markdown`) via Python UTF-8/Latin-1 decoders

---

## 2. Validation & Security Checks

Before extraction occurs, uploaded documents undergo three-layer validation:

1. **Size Validation**: Maximum document size is constrained to 20MB (`KNOWLEDGE_MAX_DOC_BYTES`). Larger payloads return HTTP 413 (`file_too_large`).
2. **MIME & Extension Validation**: Only whitelisted MIME types are accepted. Unsupported types return HTTP 415 (`unsupported_media_type`).
3. **Magic-Byte Header Verification**:
   - PDF uploads must start with `%PDF` bytes (`0x25 0x50 0x44 0x46`).
   - DOCX files must start with the standard ZIP header `PK\x03\x04` (`0x50 0x4B 0x03 0x04`).
   - Mismatches raise immediate validation errors preventing arbitrary file spoofing.
4. **Decompression Bomb Defense**:
   - Extraction stops if aggregate decompressed text exceeds 50MB.
   - Page extraction is capped at 500 pages per document.

---

## 3. Provenance & Page Tracking

- For PDFs, each page is processed independently, yielding `ExtractedPage(page_num, text, char_count)`.
- Scanned PDF detection: If average extracted characters per page is below 100, the extraction result records a `scanned_pdf_limited` warning alerting users that OCR is required for image-based PDFs.
- For DOCX documents, paragraphs and tables are extracted in order, retaining document structure and core property titles.
- For Plain Text and Markdown, character counts and utf-8 encodings are normalized with automatic fallback to Latin-1 if multi-byte decode exceptions occur.
