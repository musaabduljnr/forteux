# Phase 09 Known Limitations & Scope Boundaries

## 1. Export Processing Execution Model
- **Synchronous Generation**: Currently, exports are generated synchronously within the endpoint handler rather than offloaded to a background task runner (e.g. Celery or ARQ). For large audits with dozens of high-resolution screenshots and hundreds of findings, export generation will take several seconds. A background worker queue is scheduled for production scaling.
- **ZIP Binaries**: The ZIP format currently outputs a structured JSON package manifest rather than generating an in-memory `.zip` archive containing binary files. True compressed binary archiving with S3 presigned download URLs will be implemented in future infrastructure updates.
- **PDF Generation**: Native client-side / headless browser PDF generation is deferred; users can print or export Markdown/HTML reports to PDF via browser print stylesheets.

## 2. Analysis Comparison Heuristics
- **Category + Title Matching**: Comparison between analysis versions matches findings based on exact `category:title` string heuristics. If a subsequent AI run rephrases a finding title (e.g., "Low button contrast" to "Insufficient button contrast ratio"), the comparison engine classifies the earlier finding as "resolved" and the latter as "new".
- **Visual Diffing**: The comparison engine compares structured semantic finding records and severities; it does not compute pixel-by-pixel perceptual hash differences of the original screenshot images.
- **Design System Versioning**: Version comparison currently focuses on audit finding progressions. Comprehensive diffing of design system tokens across multiple extraction runs is planned for future iterations.

## 3. Project Deletion Safeguards
- **Soft Deletion**: Project deletion sets `deleted_at` timestamps on the project record, immediately revoking API and workspace access. Physical purging of raw S3 images and chunk embeddings occurs via dedicated asynchronous deletion worker tasks (`DeletionTask`).

## 4. Multi-Tenant Scope
- Projects belong to a single organization tenant and are scoped to authorized membership accounts. Cross-user team collaboration and fine-grained role-based sharing within projects are strictly reserved for Phase 10+.
