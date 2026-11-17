# Phase 06 Known Limitations & Boundaries

## 1. Scope Boundaries Preserved

### 1.1 Multi-Screen Flow Auditing (Phase 07)
- **Boundary**: Phase 06 strictly focuses on knowledge library ingestion, chunking, semantic retrieval, and grounding single-screen audits and Google Stitch prompt generation.
- **Status**: Multi-screen sequence auditing, screen transitions, state consistency, and user journey flow analysis are strictly reserved for Phase 07.

### 1.2 Automated Google Stitch API Sync
- **Boundary**: As established in Phase 05, Google Stitch does not currently offer a public authenticated REST/GraphQL API for programmatic screen generation.
- **Status**: Forteux generates structured, grounded redesign instructions with exact knowledge guideline citations for manual handoff into `https://stitch.withgoogle.com`.

### 1.3 Direct Figma Plugin Bidirectional Sync
- **Boundary**: Automated bidirectional synchronization of design tokens and components to live Figma files is not included in Phase 06.
- **Status**: Reserved for Phase 08+.

---

## 2. Technical Limitations & Architectural Trade-offs

### 2.1 Scanned Image PDFs (Lack of OCR)
- **Limitation**: PDF documents that consist entirely of raster images without embedded text streams cannot be parsed by `pypdf`.
- **Handling**: The document extractor analyzes total extracted character count against page count. If characters per page fall below the threshold (< 20 characters), the pipeline fails gracefully with the error code `scanned_pdf_not_supported` and informs the user to provide an OCR-processed or searchable PDF.
- **Future Roadmap**: Integration with cloud OCR services (Google Cloud Vision OCR or AWS Textract) can be added as an optional document processing plugin.

### 2.2 Embedding Storage & Pure-Python Vector Similarity
- **Limitation**: Vector embeddings (768 dimensions) are stored as JSON strings in the database and vector similarity scoring is evaluated in-application using pure Python.
- **Trade-off Justification**: This architecture provides cross-platform portability without requiring external C compilers (e.g. MSVC on Windows) or database-specific extensions, allowing 100% test compatibility with SQLite and seamless operation with PostgreSQL.
- **Scale Horizon**: For enterprise libraries exceeding 100,000 active chunks per tenant, migrating the `knowledge_chunks.embedding` column to the native `pgvector` extension and using IVFFlat or HNSW indexes will provide sub-millisecond retrieval at scale without modifying the service interfaces.

### 2.3 Synchronous Ingestion for Local Development
- **Limitation**: In the current local development setup, document processing (`extracting` $\to$ `chunking` $\to$ `embedding` $\to$ `indexing`) runs in-process.
- **Handling**: 20MB file size limits and 500-page limits keep processing times well under 5 seconds for typical design system manuals.
- **Future Roadmap**: In production Kubernetes/ECS environments, document completion can be offloaded to an asynchronous worker queue (Celery, RQ, or AWS SQS) using the already provisioned status states (`pending`, `extracting`, `chunking`, `embedding`, `ready`, `failed`).

### 2.4 Tokenizer Estimation
- **Limitation**: Word-to-token count conversion uses a heuristic ratio ($\approx 1.3$ tokens per whitespace word) when exact model tokenizer bindings are not installed locally.
- **Impact**: Chunk boundaries are safely sized at 1,200 characters with 150-character overlap, providing plenty of buffer below LLM context limits while preserving complete sentence and paragraph boundaries.
