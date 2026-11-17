# Phase 06 Security & Deletion Architecture

## 1. Multi-Tenant Authorization & Isolation

Security boundaries are strictly maintained across every layer of the Knowledge Library:

1. **Database Row-Level Scoping**:
   - Every read, update, and delete query requires `tenant_id == principal.tenant_id`.
   - Global documents require `project_id IS NULL`.
   - Project documents verify project ownership and membership before returning data or accepting uploads.
2. **Private File Storage**:
   - Raw documents are stored with private S3/MinIO permissions.
   - Presigned upload and download URLs expire after 300 seconds (`S3_UPLOAD_TTL_SECONDS`).
   - S3 object keys are never exposed in browser responses.
3. **No Cross-Tenant Retrieval**:
   - Vector chunks and full-text indexes are partitioned by `tenant_id`.
   - A tenant cannot retrieve or view passages belonging to another tenant under any circumstance.
4. **Duplicate Protection**:
   - Duplicate active document names within the same library scope return HTTP 409 (`duplicate_document_name`).
   - Duplicate file contents (matching SHA-256 within the same scope) return HTTP 409 (`duplicate_document`).

---

## 2. Document Deletion & Invalidation

When a document is deleted (`DELETE /knowledge/{id}` or `DELETE /projects/{id}/knowledge/{id}`):

1. **Immediate Vector Removal**: All `KnowledgeChunk` records for the document are immediately deleted from the database.
2. **Object Storage Cleanup**: Raw files for all document versions are deleted from S3 storage via `storage.delete(object_key)`.
3. **Soft-Deletion & State Tracking**: The `KnowledgeDocument` record is marked with `status = "deleted"` and `deleted_at = utc_now()`.
4. **Audit Trail**: A `DeletionTask` record is inserted with `status = "completed"` and the count of deleted chunks.
5. **Immediate Invalidation**: Deleted documents are immediately excluded from all future retrieval and search queries.

---

## 3. Document Replacement (Versioning)

When a document is replaced (`POST /knowledge/{id}/replace`):
1. A new `DocumentVersion` record is created with `version_number = current_max + 1`.
2. Upon upload completion, old chunks for previous versions are purged, and new chunks are indexed.
3. `active_version_id` points to the new version, ensuring immediate consistency.
