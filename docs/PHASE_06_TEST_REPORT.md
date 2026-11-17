# Phase 06 Test Report: Knowledge Library & Document Intelligence

**Date:** November 17, 2026  
**Environment:** Python 3.14 (`.venv`), SQLite & PostgreSQL (SQLAlchemy + Alembic), Next.js 15.5.29  
**Status:** All 68 backend tests passing, frontend production build & typecheck 100% clean  

---

## 1. Test Suite Summary

The backend test suite was expanded with 24 dedicated automated tests in `backend/tests/test_knowledge_library.py`, testing document extraction, chunking, embeddings, full ingestion lifecycles, deduplication, versioning, deletion, cross-tenant isolation, cross-project isolation, ready-state retrieval gating, and RAG integrations with both Phase 04 analysis and Phase 05 Google Stitch prompt generation.

```
backend/tests/test_knowledge_library.py ........................          [ 35%]
backend/tests/test_prompt_generation.py .........                         [ 48%]
backend/tests/test_auth.py .....                                          [ 55%]
backend/tests/test_bounding_box_benchmark.py .....                        [ 63%]
backend/tests/test_migrations.py .                                        [ 64%]
backend/tests/test_projects_audits.py .....                               [ 72%]
backend/tests/test_storage.py .........                                   [ 85%]
backend/tests/test_vision_analysis.py ..........                          [100%]

============================== 68 passed, 1 warning in 74.80s ==============================
```

---

## 2. Test Details & Results

### 2.1 Extraction & Chunking Suite

#### `test_extract_markdown_and_txt`
- **Scenario**: Extract plain text and markdown documents containing section headers and paragraphs.
- **Verification**: Extracted text preserves structure; `page_count` is 1; word and character counts are accurate.
- **Result**: **PASS**

#### `test_extract_docx`
- **Scenario**: Ingest a Microsoft Word `.docx` file created via `docx.Document` with headings and body paragraphs.
- **Verification**: Text extraction captures paragraphs and headings cleanly; word count matches expected string.
- **Result**: **PASS**

#### `test_extract_pdf`
- **Scenario**: Extract text from a structured PDF document.
- **Verification**: `pypdf` parser extracts text streams across pages; page numbers and total page counts are recorded.
- **Result**: **PASS**

#### `test_extract_scanned_pdf_rejected`
- **Scenario**: Ingest a scanned image PDF containing empty text streams.
- **Verification**: Extraction raises `ExtractionError` with error code `scanned_pdf_not_supported` and friendly user guidance.
- **Result**: **PASS**

#### `test_chunker_paragraphs_and_headings`
- **Scenario**: Process raw document text with markdown headers into chunks (`chunk_size=1200`, `overlap=150`).
- **Verification**: Paragraph boundaries and headings are detected; `heading_context` is attached to chunks; `page_start` and `page_end` are recorded.
- **Result**: **PASS**

#### `test_chunker_token_limit`
- **Scenario**: Process oversized paragraphs without natural whitespace breaks.
- **Verification**: Chunker subdivides paragraphs at sentence and token boundaries without exceeding max size.
- **Result**: **PASS**

---

### 2.2 Embedding & Math Suite

#### `test_deterministic_embedding_provider`
- **Scenario**: Compute dense embeddings using `DeterministicEmbeddingProvider` and calculate pure-Python cosine similarity.
- **Verification**:
  - Deterministic vector dimensions: exactly 768 floats.
  - L2 normalized unit vectors: Euclidean norm equals $1.0 \pm 10^{-5}$.
  - Cosine similarity: identical text yields 1.0; orthogonal/opposite yields $\le 0.0$.
  - Runs with zero C-compiler dependencies on Windows.
- **Result**: **PASS**

---

### 2.3 Upload Intent & Document Lifecycle

#### `test_upload_intent_and_complete_lifecycle`
- **Scenario**: Submit upload intent for a 2.4KB design system guidelines document, calculate SHA-256, execute `/complete` pipeline.
- **Verification**:
  - Upload intent yields presigned S3/MinIO upload URL and secure storage path: `tenants/{tenant_id}/knowledge/{doc_id}/v1/{filename}`.
  - Completion pipeline extracts text, produces chunks, creates embeddings, and updates status to `ready`.
  - Database contains `KnowledgeDocument`, `DocumentVersion` (v1), and populated `KnowledgeChunk` records.
- **Result**: **PASS**

#### `test_file_too_large_rejected`
- **Scenario**: Submit upload intent for a 25MB document (exceeding 20MB limit).
- **Verification**: Server rejects with HTTP 413 `file_too_large`. Storage upload URL is denied.
- **Result**: **PASS**

#### `test_unsupported_mime_rejected`
- **Scenario**: Submit upload intent for an unsupported file format (`image/png` or `.exe`).
- **Verification**: Server rejects with HTTP 415 `unsupported_media_type`.
- **Result**: **PASS**

#### `test_duplicate_filename_rejected`
- **Scenario**: Submit upload intent for a document whose filename already exists in the same active library scope.
- **Verification**: Server rejects with HTTP 409 `duplicate_document_name` and points user to replacement workflow.
- **Result**: **PASS**

#### `test_duplicate_sha256_rejected`
- **Scenario**: Submit upload intent with an identical file hash (SHA-256) under a different filename.
- **Verification**: Server rejects with HTTP 409 `duplicate_content` and provides the existing document ID.
- **Result**: **PASS**

---

### 2.4 Document Replacement, Versioning & Deletion

#### `test_document_replacement_and_version_increment`
- **Scenario**: Call `/replace` endpoint on existing document with updated document content.
- **Verification**:
  - Increments version from v1 to v2.
  - Old v1 chunks are marked inactive (`is_active = False`).
  - New v2 chunks are indexed and set to `is_active = True`.
  - Version history reflects both v1 and v2 with timestamps and changelog.
- **Result**: **PASS**

#### `test_document_deletion_and_cleanup`
- **Scenario**: Call `DELETE /knowledge/{id}`.
- **Verification**:
  - Document `deleted_at` timestamp is set (soft delete).
  - Storage deletion task is dispatched.
  - All associated chunks are immediately purged from the vector search space.
  - Document is immediately excluded from `GET /knowledge` and retrieval queries.
- **Result**: **PASS**

---

### 2.5 Multi-Tenant & Project Isolation

#### `test_tenant_isolation_retrieval_and_endpoints`
- **Scenario**: Tenant A uploads sensitive brand guidelines. Tenant B attempts retrieval, search, read, replace, and delete.
- **Verification**:
  - Tenant B receives HTTP 404 for all direct accesses.
  - Tenant B search queries return 0 results from Tenant A's documents.
  - Zero cross-tenant leakage in vector index or database queries.
- **Result**: **PASS**

#### `test_project_isolation_retrieval_and_endpoints`
- **Scenario**: Tenant A has Project X and Project Y. Document uploaded to Project X. Query executed within Project Y.
- **Verification**:
  - Project Y query only retrieves Project Y and Global documents; Project X documents are strictly omitted.
  - Scoping rules enforced: `tenant_id == current_tenant AND (project_id IS NULL OR project_id == audit_project_id)`.
- **Result**: **PASS**

#### `test_project_scoped_knowledge_endpoints`
- **Scenario**: Upload, list, read, replace, search, and delete document scoped to a specific project (`/projects/{id}/knowledge`).
- **Verification**: Correctly associates `project_id`, validates project ownership, rejects foreign projects.
- **Result**: **PASS**

#### `test_project_knowledge_deletion`
- **Scenario**: Delete project-scoped document and verify exclusion from project searches.
- **Verification**: Purges chunks and marks document deleted.
- **Result**: **PASS**

#### `test_project_knowledge_search`
- **Scenario**: Search scoped specifically to project endpoint with semantic query.
- **Verification**: Returns relevant chunks matching project scope.
- **Result**: **PASS**

---

### 2.6 Retrieval Gating & Error Resilience

#### `test_retrieval_gating_unready_and_inactive_versions`
- **Scenario**: Execute search when documents are in `extracting`, `chunking`, or `failed` states, or chunks belong to v1 after v2 replacement.
- **Verification**:
  - Chunks in non-ready documents are strictly excluded.
  - Inactive version chunks are excluded.
  - Only `status == "ready"` and `is_active == True` chunks are retrieved.
- **Result**: **PASS**

#### `test_semantic_search_endpoint`
- **Scenario**: User submits semantic search query (`query="button touch target spacing"`) via `/knowledge/search`.
- **Verification**: Returns top-k ranked chunks with score, document name, page provenance, and snippet.
- **Result**: **PASS**

#### `test_retry_failed_document`
- **Scenario**: Ingestion fails due to temporary storage error. Call `/retry` endpoint.
- **Verification**: Document resets to `pending`, processing re-runs, and transitions to `ready`.
- **Result**: **PASS**

---

### 2.7 RAG Workflows: Analysis & Prompt Generation

#### `test_rag_integrated_with_analysis_findings`
- **Scenario**: Single-screen audit analysis executed with active knowledge library documents present.
- **Verification**:
  - Knowledge chunks relevant to detected issues are retrieved.
  - `FindingEvidence` rows are persisted linking `finding_id` to `chunk_id` with exact quotes and relevance scores.
  - Analysis API response includes `evidence_sources` alongside bounding box annotations.
- **Result**: **PASS**

#### `test_rag_integrated_with_stitch_prompt_generator`
- **Scenario**: Generate Google Stitch prompt with findings linked to knowledge document guidelines.
- **Verification**:
  - Prompt contains `## Applied Design References (Knowledge Base)` section.
  - Citations include document name, version, page number, and guidelines quotation.
  - Redesign instructions reference guidelines for concrete remediation directives.
- **Result**: **PASS**

---

## 3. Frontend Build & Quality Verification

| Check | Tool / Command | Result | Details |
|---|---|---|---|
| **Production Build** | `npm run build` | **PASSED** (0 errors) | Next.js 15.5.29 compiled 10 static & dynamic routes in 36.5s. `/knowledge` prerendered cleanly. |
| **Typecheck** | `npm run typecheck` (`tsc --noEmit`) | **PASSED** (0 errors) | Strict TypeScript validation passed across entire codebase. |
| **Lint** | `npx eslint app/knowledge/page.tsx` | **PASSED** (0 errors) | ESLint passed with zero warnings or errors. |

---

## 4. Conclusion

Phase 06 implementation meets 100% of the functional, security, isolation, and integration criteria. All 68 backend tests pass cleanly, and the frontend builds without errors.
