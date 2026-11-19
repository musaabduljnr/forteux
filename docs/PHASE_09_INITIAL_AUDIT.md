# Phase 09 Initial Audit — Project History, Versioning & Exports

## Audit Date
2026-11-17

## Dependency Gate: Phases 03–08

All prior phases verified present:

| Phase | Key Artifact | Status |
|-------|-------------|--------|
| 03 | ScreenAsset upload, AuditScreen, identity/tenancy | ✅ Present |
| 04 | AnalysisJob, Finding, AIVisionService | ✅ Present |
| 05 | AuditPrompt, PromptVersion, StitchPromptGenerator | ✅ Present |
| 06 | KnowledgeDocument, DocumentVersion, KnowledgeChunk, FindingEvidence | ✅ Present |
| 07 | Multi-screen flow, AuditScreen reorder, FlowReport | ✅ Present |
| 08 | DesignSystemAnalysis, consistency scoring, design export | ✅ Present |

---

## Existing Models (Verified in `backend/app/db/models.py`)

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | OIDC-linked user identity |
| `Tenant` | `tenants` | Org-level multi-tenant isolation |
| `Membership` | `memberships` | User↔Tenant membership with role |
| `Project` | `projects` | Top-level workspace grouping audits |
| `Audit` | `audits` | Named audit run (single or multi mode) |
| `ScreenAsset` | `screen_assets` | Uploaded image with S3 object key |
| `AuditScreen` | `audit_screens` | Join: Audit ↔ ScreenAsset with sequence |
| `AnalysisJob` | `analysis_jobs` | AI run record (status, provider, model) |
| `Finding` | `findings` | Individual UX issue from an AI job |
| `AuditPrompt` | `audit_prompts` | Generated stitch prompt for an audit |
| `PromptVersion` | `prompt_versions` | Versioned history of prompt edits |
| `KnowledgeDocument` | `knowledge_documents` | Uploaded reference doc for RAG |
| `DocumentVersion` | `document_versions` | Versioned doc upload |
| `KnowledgeChunk` | `knowledge_chunks` | RAG-ready text chunks with embeddings |
| `FindingEvidence` | `finding_evidence` | RAG evidence linking findings to chunks |
| `DeletionTask` | `deletion_tasks` | Async document deletion tracker |
| `DesignSystemAnalysis` | `design_system_analyses` | Full design system extraction result |

---

## Missing Fields on Existing Models

### Project model — Missing fields (confirmed absent in models.py lines 70–84)
| Field | Type | Purpose |
|-------|------|---------|
| `category` | `VARCHAR(100)` nullable | Project category (e.g. "mobile", "web") |
| `platform_type` | `VARCHAR(100)` nullable | Platform type (iOS, Android, web, etc.) |
| `thumbnail_url` | `VARCHAR(900)` nullable | Optional thumbnail image URL |
| `context_text` | `TEXT` nullable | Free-form context for AI analysis |
| `archived_at` | `TIMESTAMP WITH TZ` nullable | Soft-archive timestamp |

### Audit model — Missing fields (confirmed absent in models.py lines 87–111)
| Field | Type | Purpose |
|-------|------|---------|
| `version_number` | `INTEGER NOT NULL DEFAULT 1` | Monotonic version counter for audit |
| `parent_job_id` | `UUID nullable FK analysis_jobs.id` | Link to triggering AnalysisJob |

---

## Missing Infrastructure

### No ExportJob model or table
- No `export_jobs` table exists anywhere in `models.py` or in migration `0001`–`0006`
- No export endpoint exists in `routes.py` beyond the per-design-system JSON/CSS export (lines 2795–2871)
- No download mechanism for packaged audit exports

### No ProjectActivityEvent model or table
- No `project_activity_events` table in `models.py`
- No activity logging in create_project, create_audit, or analysis endpoints
- No GET activity endpoint in `routes.py`

### No Analysis Version Comparison Logic
- `AnalysisJob` records exist per audit but no version grouping/comparison
- No endpoint `GET /projects/{project_id}/audits/{audit_id}/versions`
- No endpoint `GET /projects/{project_id}/audits/{audit_id}/versions/compare`
- Each `AnalysisJob` already serves as a version (created_at ordering) but is not surfaced

### History Endpoint Gap
- `GET /projects/{project_id}/audits` exists (list_audits, line 253) — per-project only
- No cross-project history endpoint (e.g. `GET /projects/history`)
- No pagination on audits listing

### Extended Project CRUD Missing
- No PATCH endpoint for project fields
- No archive/restore endpoints
- No project soft-delete endpoint (DELETE)
- No project stats endpoint
- No project activity listing endpoint

---

## Existing Route Summary (relevant)

| Method | Path | Handler |
|--------|------|---------|
| GET | `/projects` | list_projects |
| POST | `/projects` | create_project |
| GET | `/projects/{id}` | read_project |
| POST | `/projects/{id}/audits` | create_audit |
| GET | `/projects/{id}/audits` | list_audits |
| GET | `/projects/{id}/audits/{aid}` | read_audit |
| POST | `/projects/{id}/audits/{aid}/analyze` | analyze_audit_screen |
| POST | `/projects/{id}/audits/{aid}/analyze-flow` | analyze_audit_flow |
| POST | `/projects/{id}/audits/{aid}/design-system/extract` | extract_design_system |
| GET | `/projects/{id}/audits/{aid}/design-system` | read_audit_design_system |
| GET | `/projects/{id}/audits/{aid}/design-system/export/json` | export_design_system_json_endpoint |
| GET | `/projects/{id}/audits/{aid}/design-system/export/css` | export_design_system_css_endpoint |
| POST | `/projects/{id}/audits/{aid}/design-system/stitch-prompt` | generate_design_system_stitch_prompt_endpoint |
| GET | `/projects/{id}/design-systems` | list_project_design_systems |

---

## Phase 09 Deliverables Plan

1. **Migration 0007** — Add columns to `projects` and `audits`, create `project_activity_events` and `export_jobs`
2. **Models** — Add `ProjectActivityEvent`, `ExportJob`; patch `Project` and `Audit` class definitions
3. **Schemas** — Append Phase 09 Pydantic schemas
4. **Routes** — Append project CRUD, audit versions, history, and export endpoints
5. **Tests** — 30 tests across 5 groups
6. **Docs** — Implementation report, known limitations, architecture docs
