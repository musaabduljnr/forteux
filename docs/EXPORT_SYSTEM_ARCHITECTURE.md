# Export System Architecture

## 1. Overview
The Export System enables users to export audits, design systems, prompt specifications, and project archives in standardized formats suitable for engineering handoff, UX review, and external tooling.

---

## 2. Supported Export Matrix

| Resource Type | JSON | Markdown | CSV | ZIP Manifest |
|---|---|---|---|---|
| **Single-Screen Audit** | Full schema + bounding boxes | Formatted document with tables | Tabular finding rows | Package manifest |
| **Multi-Screen Flow** | Journey overview + screen sequence | Structured report with stages | Tabular cross-screen issues | Package manifest |
| **Design System** | Tokens, colors, typography scales | Complete design system handbook | Token key-value rows | Package manifest |
| **Google Stitch Prompt** | JSON envelope with instructions | Standalone Markdown prompt | N/A | N/A |
| **Project Archive** | Metadata + audits summary | High-level workspace summary | Audit inventory table | Archive manifest |

---

## 3. Data Flow & Security
1. **Request**: The client sends a `POST /projects/{project_id}/exports` request with the desired `export_type`, `format`, and optional `audit_id`.
2. **Authorization**:
   - Validates that the requesting principal belongs to the project's tenant.
   - Validates that any referenced audit belongs to the same project and tenant.
3. **Generation**:
   - `export_service.generate_export_content` renders the requested format from live database records.
   - Saves payload to `export_jobs.file_content` and records byte size.
4. **Download**:
   - `GET /projects/{project_id}/exports/{export_id}/download` validates project ownership and returns the payload with appropriate `Content-Type` and `Content-Disposition: attachment; filename=...`.
   - Prevents unauthorized cross-tenant downloads.
