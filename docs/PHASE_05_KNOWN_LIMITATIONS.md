# Phase 05 Known Limitations & Boundaries

## 1. Scope Boundaries Preserved

### 1.1 Direct Programmatic Google Stitch API
- **Limitation**: Google Stitch does not currently provide a public, authenticated programmatic REST or GraphQL API for external generation triggers.
- **Handled By**: Forteux provides a complete handoff experience:
  1. The complete redesign brief is generated and structured specifically for Google Stitch.
  2. Single-click copy to clipboard with formatting preserved.
  3. Guidance directing users to open `https://stitch.withgoogle.com`, provide the original screenshot, and paste the generated brief.

### 1.2 Multi-Screen Flow Redesign
- **Limitation**: In Phase 05, prompt generation is focused on single-screen audits and individual screen contexts.
- **Status**: Multi-screen sequence redesign, transition continuity, and cross-screen consistency auditing are strictly planned for Phase 06.

### 1.3 Knowledge Base Document Retrieval (RAG)
- **Limitation**: Findings in Phase 05 do not yet dynamically cite uploaded PDF/guideline documents from the knowledge repository.
- **Status**: Design systems and guideline document ingestion with vector search/RAG is strictly planned for Phase 07.

### 1.4 Direct Figma Token Export
- **Limitation**: Direct bidirectional Figma plugin synchronization is not included in Phase 05.
- **Status**: Planned for Phase 08+.

---

## 2. Technical Limitations & Edge Cases

### 2.1 Empty Selection Guard
- Generating a prompt requires at least one selected finding. The frontend disables the generation button and displays a warning banner if all findings are deselected. The backend returns HTTP 400 (`invalid_findings`) if an empty array is submitted.

### 2.2 Client-Side Fallback for Demo Audits
- For unauthenticated users or local demonstration sessions where backend PostgreSQL storage is not active, the workspace falls back seamlessly to client-side structured prompt generation, ensuring offline usability.
