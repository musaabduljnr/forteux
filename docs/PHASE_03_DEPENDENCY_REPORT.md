# Phase 03 Dependency Gate Report

**Date:** 2026-11-16  
**Auditor:** Senior AI & Systems Engineer  
**Status:** **GATE FAILED — CRITICAL DEPENDENCIES MISSING**  
**Action:** Pausing implementation of Phase 04 pending user review and approval.

---

## 1. Executive Summary

In accordance with the mandatory **Phase 03 Dependency Gate** specified in the Phase 04 instructions:

> *"If any critical dependency is missing or broken, do not implement Phase 04 on top of assumptions. Produce a dependency report explaining what is missing and stop for approval."*

An exhaustive audit of the frontend and backend implementations was conducted. While the Foundation phase established basic API routing, authentication adapters, and relational schema models, **Phase 03 (Screenshot Processing, Storage Integration, and Image Normalization) has not been implemented**.

The application currently relies on frontend-only demo fixtures (`URL.createObjectURL(file)`) and mock issues (`lib/demo-data.ts`). The backend cannot receive, validate, measure, orient, link to audits, or retrieve screenshot image bytes. Proceeding to Phase 04 (AI Vision Analysis & Bounding Box Detection) without these prerequisites would violate the architectural boundaries and force Phase 04 to operate on mock assumptions.

---

## 2. Dependency Gate Audit Matrix

| Required Capability | Status | Evidence & Code Location | Impact on Phase 04 |
|---|---|---|---|
| **1. User can upload a screenshot** | **BROKEN / DEMO-ONLY** | `components/new-audit-form.tsx` line 16-28 creates local `URL.createObjectURL(file)`. Line 133 notes: *"Demo audit created. No AI analysis or backend upload has run."* Backend API `/projects/{id}/uploads` exists but is never invoked by the UI. | Frontend cannot send screenshots to S3/MinIO storage. |
| **2. Uploaded image stored securely** | **PARTIAL / UNCONNECTED** | `backend/app/services/storage.py` has `S3Storage.presign_upload` and `head`, but without a live container or connected frontend, real user uploads never reach storage. | No persistent image assets exist in storage for vision analysis. |
| **3. Backend can retrieve image for analysis** | **MISSING** | `backend/app/services/storage.py` provides `presign_upload`, `head`, `presign_download`, and `delete`. It **lacks** a `get_object(key)` method to read raw image bytes into memory for model inference. | AI Vision service cannot load image bytes to analyze. |
| **4. Image metadata & dimensions available** | **MISSING** | `backend/app/db/models.py` (`ScreenAsset`) contains only `declared_size` and `declared_content_type`. No `width`, `height`, or verified dimensions exist in the schema. `Pillow` is not installed in `requirements.txt`. | Normalized bounding boxes `[x, y, w, h]` cannot be validated or mapped against original dimensions. |
| **5. Image orientation handled correctly** | **MISSING** | No EXIF inspection, rotation handling, or Pillow image decoding exists anywhere in backend or frontend. | EXIF-rotated mobile screenshots will cause misplaced bounding box coordinates. |
| **6. Screenshot associated with user and audit** | **MISSING** | In `backend/app/db/models.py`, `ScreenAsset` references `tenant_id`, `project_id`, and `uploaded_by`, but has **no relationship or foreign key to `Audit`**. | Backend cannot identify which screenshot belongs to which audit. |
| **7. Backend accesses image without browser URL** | **MISSING** | The frontend currently relies entirely on ephemeral browser blob URLs. The backend has no access to the image bytes. | Server cannot execute server-side vision model analysis. |

---

## 3. Detailed Technical Analysis of Missing Capabilities

### A. Missing Audit-to-Screen Association
In `backend/app/db/models.py`:
- `Audit` has `id`, `tenant_id`, `project_id`, `created_by`, `name`, `mode`, `status`, `context_json`.
- `ScreenAsset` has `id`, `tenant_id`, `project_id`, `uploaded_by`, `object_key`, `declared_size`, `status`.
- There is **no `audit_id` on `ScreenAsset`** and no `audit_screens` junction table with ordering (`order_index`).
- The Foundation Implementation Report explicitly noted: *"Findings, analysis jobs, knowledge documents, embeddings, and audit-screen ordering remain future schema work"*.

### B. Missing Image Decoding & Dimension Extraction
- `backend/requirements.txt` contains: `fastapi`, `uvicorn`, `pydantic-settings`, `python-dotenv`, `SQLAlchemy`, `alembic`, `psycopg`, `boto3`, `PyJWT`.
- **`pillow` (PIL) is not installed.**
- The backend cannot verify magic bytes (`\x89PNG\r\n\x1a\n` or `\xff\xd8\xff`), extract width/height, verify color profiles, or protect against decompression bombs.

### C. Missing Storage Byte Retrieval
- `S3Storage` generates presigned URLs for browser PUT/GET and executes `HeadObject` for metadata check.
- `S3Storage` does not have a `download_bytes(key: str) -> bytes` or `get_object` method to supply raw bytes or base64 to vision APIs.

### D. Frontend Demo Disconnect
- `components/new-audit-form.tsx` stores uploads in client-side state with `URL.createObjectURL(file)`.
- `components/audit-workspace.tsx` renders static fixture findings from `lib/demo-data.ts`.
- No upload network requests or completion calls are triggered upon audit creation.

---

## 4. Phase 03 Remediation Plan (Required to Unblock Phase 04)

To satisfy the Phase 03 dependency gate and enable Phase 04 without relying on fake data:

1. **Schema & Migration**:
   - Add an Alembic migration creating `audit_screens` table (or adding `audit_id` and `order_index` to `screen_assets`).
   - Add `width: int`, `height: int`, `orientation: int`, and `verified_mime_type: str` columns to `screen_assets`.
   - Add `AnalysisJob` and `Finding` models as defined in `docs/DATABASE_SCHEMA.md` and `docs/AI_ENGINE_ARCHITECTURE.md`.
2. **Backend Image Processing**:
   - Add `Pillow` to `backend/requirements.txt`.
   - Implement an image verification service: magic bytes validation, dimension extraction, EXIF orientation inspection, and decompression limits.
   - Add `get_object(key) -> bytes` to `S3Storage` in `backend/app/services/storage.py`.
3. **Frontend Upload Integration**:
   - Update `components/new-audit-form.tsx` to call `POST /api/v1/projects/{project_id}/uploads`, PUT the file to S3/MinIO, and call `POST .../complete`.
   - Associate the uploaded asset with the created audit.

---

## 5. Recommendation

Do **not** implement Phase 04 AI analysis on top of missing screenshot infrastructure or browser-only mock objects.

**Next Action**: Awaiting user approval to either:
1. Implement the Phase 03 screenshot processing and storage prerequisites first, then immediately proceed to Phase 04; OR
2. Provide alternative instructions.
