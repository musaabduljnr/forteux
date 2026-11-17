# Phase 06 RAG Integration with Phase 04 & Phase 05

## 1. Grounding Single-Screen AI Analysis (Phase 04)

During single-screen AI auditing (`POST /projects/{id}/audits/{id}/analyze`):

1. The backend automatically queries relevant knowledge chunks using the audit name, user context, and UI inspection domains (typography, visual hierarchy, affordances, contrast).
2. For every detected usability/design issue:
   - If relevant knowledge chunks are retrieved, the backend links them to the finding via `FindingEvidence` records.
   - Evidence records snapshot:
     - `document_display_name`
     - `page_number_snapshot`
     - `section_heading_snapshot`
     - `quote_or_paraphrase` (first 250 characters)
     - `retrieval_score` and `retrieval_rank`
3. In API responses (`FindingRead`), findings expose an `evidence_sources` array, allowing the UI to display verified guideline citations alongside screenshot bounding boxes.
4. If no knowledge library documents are uploaded, Phase 04 analysis completes cleanly with zero degradation or error.

---

## 2. Grounding Google Stitch Prompt Generation (Phase 05)

During prompt generation (`POST /projects/{id}/audits/{id}/prompt`):

1. The prompt generator retrieves authoritative reference passages matching the audit context and the titles of all user-selected findings.
2. The brief generator appends a dedicated section:
   ```markdown
   ## Applied Design References (Knowledge Base)
   Align the redesign with these authoritative organizational design standards:
   - **tokens.txt** (Spacing Scale, Page 1):
     > "Use 8pt harmonic grid and #0052CC for primary actions."
   ```
3. Retrieved document text is treated strictly as **reference material** (enclosed in blockquotes and markdown sections), preventing prompt injection from overriding core system instructions or constraints.
4. When exported or copied into Google Stitch, the redesign prompt provides both screenshot defect geometry AND authoritative brand standards in a single, cohesive brief.
