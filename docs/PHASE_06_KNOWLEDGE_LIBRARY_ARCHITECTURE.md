# Phase 06 Knowledge Library Architecture

## 1. System Overview

The Knowledge Library provides a multi-tenant, enterprise-grade Retrieval-Augmented Generation (RAG) framework for Forteux UI/UX Auditor. It enables organizations and product teams to upload, process, index, and retrieve authoritative design references (design systems, brand guides, component specifications, usability heuristics) and inject them directly into:
1. **Phase 04 AI Single-Screen Auditing**: Providing source-grounded visual observation evidence and domain standards.
2. **Phase 05 Google Stitch Prompt Generation**: Enforcing brand colors, layout grids, spacing units, and typography guidelines into actionable generative redesign briefs.

---

## 2. Multi-Tier Entity Architecture

The knowledge architecture follows a 5-table relational schema designed for strong data integrity, version history, and isolation:

```
  ┌────────────────────────────────────────────────────────┐
  │                   knowledge_documents                  │
  │ (id, tenant_id, project_id, scope, display_name, ...)  │
  └──────────────────────────┬─────────────────────────────┘
                             │ 1:N
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                    document_versions                   │
  │ (id, document_id, version_number, object_key, sha256) │
  └──────────────────────────┬─────────────────────────────┘
                             │ 1:N
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                    knowledge_chunks                    │
  │ (id, tenant_id, project_id, text, page_start, emb)     │
  └──────────────────────────┬─────────────────────────────┘
                             │ 1:N
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                    finding_evidence                    │
  │ (id, finding_id, chunk_id, document_id, score, rank)   │
  └────────────────────────────────────────────────────────┘
```

### Table Definitions

1. `knowledge_documents`:
   - Top-level document container representing a logical reference asset.
   - Scoped strictly by `tenant_id`. `project_id` is `NULL` for tenant-wide Global knowledge, or populated for Project-specific knowledge.
   - Tracks `active_version_id`, `status` (`uploaded`, `validating`, `extracting`, `chunking`, `embedding`, `indexing`, `ready`, `failed`, `deleting`, `deleted`), `error_message`, and soft-deletion timestamp.

2. `document_versions`:
   - Immutable version record created upon each upload or replacement.
   - Maintains `version_number` (1, 2, ...), S3 `object_key`, verified `sha256`, extracted `page_count`, generated `chunk_count`, `extractor_version`, and `embedding_model`.

3. `knowledge_chunks`:
   - Semantic text passages (~1200 characters) extracted from document pages.
   - Tracks `page_start`, `page_end`, `section_heading`, and character counts.
   - Stores dense vector embeddings as JSON float arrays (`embedding_json`), ensuring cross-database compatibility across SQLite dev/test and PostgreSQL production.

4. `finding_evidence`:
   - Citations linking audit `findings` to `knowledge_chunks`.
   - Records frozen snapshots of `document_display_name`, `page_number_snapshot`, `section_heading_snapshot`, retrieval similarity `score`, and `retrieval_rank`.
   - Distinguishes screenshot visual observations from document-backed design standards.

5. `deletion_tasks`:
   - Audit trail tracking asynchronous deletion and cleanup tasks, recording `chunks_deleted`, object storage cleanup status, and completion timestamps.

---

## 3. Storage Hierarchy

Object keys in private S3/MinIO storage enforce strict path isolation:

- **Global Documents**:
  `{tenant_id}/knowledge/{document_id}/{version_id}/original`
- **Project Documents**:
  `{tenant_id}/{project_id}/knowledge/{document_id}/{version_id}/original`

Direct access is disallowed; presigned URLs with short TTLs (300 seconds) are generated for uploads and downloads.
