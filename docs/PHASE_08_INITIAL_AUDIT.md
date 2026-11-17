# Phase 08 Initial Audit: Design System Extraction & Cross-Screen Consistency

**Project**: Forteux UI/UX Auditor  
**Date**: November 17, 2026  
**Auditor**: Senior Full-Stack AI Engineer  
**Status**: Dependency Gate Passed — Ready for Implementation  

---

## 1. Executive Summary

Phase 08 introduces automated **Design System Extraction and Cross-Screen Consistency Intelligence**. This capability analyses multiple interface screenshots across an audit to discover and formalise the visual design language (colours, typography, spacing, border radii, surface treatments, repeated UI components, and design tokens), evaluate cross-screen visual consistency using a reproducible mathematical scoring model, and produce an exportable design system report and Google Stitch design refinement brief.

A comprehensive codebase audit was conducted prior to implementation. All prerequisite phases (Phase 01 through Phase 07) were verified through automated tests, database inspections, and route trace reviews.

---

## 2. Dependency Gate Verification

| Dependency | Required Phase | Status | Verification Evidence |
| :--- | :--- | :---: | :--- |
| **Screenshot Upload & Verification** | Phase 03 | **PASS** | `ScreenAsset` model with SHA256, verified MIME, dimensions, orientation, and presigned upload flow passing in `test_uploads.py`. |
| **Single-Screen AI Vision** | Phase 04 | **PASS** | `AIVisionService`, `DeterministicVisionProvider`, bounding box coordinates, and finding schemas passing in `test_analysis.py`. |
| **Finding Selection & Stitch Brief** | Phase 05 | **PASS** | `AuditPrompt`, `PromptVersion`, prompt versioning, and editable markdown passing in `test_prompts.py`. |
| **Knowledge Library & RAG** | Phase 06 | **PASS** | `KnowledgeDocument`, `KnowledgeChunk`, `DocumentVersion`, `FindingEvidence` retrieval passing in `test_knowledge.py`. |
| **Multi-Screen & User Flow Analysis** | Phase 07 | **PASS** | `AuditScreen` sequencing, `MultiScreenAIVisionService`, `JourneyReport`, `ck_finding_scope`, and 28 Phase 07 tests passing in `test_multi_screen_flow.py`. |
| **Full Backend Test Suite** | Phases 01–07 | **PASS** | **96/96 pytest tests passing** (130.34s execution time). |
| **Frontend Production Build** | Next.js 15 | **PASS** | `npx tsc --noEmit` clean; `next build` compiled 10/10 routes with exit code 0. |

**Verdict**: The dependency gate is **PASSED**. No blocking issues or missing dependencies exist.

---

## 3. Codebase Analysis: What Already Exists

### 3.1 Backend Data Models (`backend/app/db/models.py`)
- **`Tenant` & `User` & `Membership`**: Multi-tenant authorization and security boundaries.
- **`Project`**: Root container for audits and knowledge documents.
- **`Audit`**: Supports `mode IN ('single', 'multi')`, `context_json`, and project association.
- **`ScreenAsset`**: Stores dimensions (`width_px`, `height_px`), object keys, verified MIME types, and storage paths.
- **`AuditScreen`**: Multi-screen sequence representation (`sequence_index`, `screen_label`, `screen_description`).
- **`AnalysisJob`**: Stores status, AI provider/model, summary, and `flow_report_json`.
- **`Finding`**: Stores severity, category, title, description, why it matters, recommended fix, confidence, evidence type, evidence, bounding boxes, scope (`screen_level`, `cross_screen`), and `affected_screen_ids_json`.
- **`AuditPrompt` & `PromptVersion`**: Stores prompt templates, selected finding IDs, and user instructions.

### 3.2 Backend Services
- **`app/services/vision.py`**: Single-screen vision analysis service with provider abstraction.
- **`app/services/multi_screen_vision.py`**: Multi-screen journey and flow analysis service with `ScreenContext`, `MultiScreenFinding`, and `JourneyReport`.
- **`app/services/prompt_generator.py`**: Prompt generator for single-screen redesign and multi-screen flow redesign.
- **`app/services/knowledge.py`**: Semantic search, vector similarity, and citation extraction.

### 3.3 Frontend Architecture
- **`app/design-system/page.tsx`**: Existing stub placeholder with project picker and empty pattern library cards (`Colour palette`, `Typography`, `Spacing scale`, `Border radius`, `Buttons`, `Form elements`, `Cards and surfaces`, `Navigation patterns`).
- **`components/multi-screen-workspace.tsx`**: 3-panel workspace for multi-screen journey inspection.
- **`components/audit-page-router.tsx`**: Dynamically switches between single-screen and multi-screen workspaces based on audit mode.
- **`lib/types.ts`**: TypeScript definitions for all domain entities.

---

## 4. Gap Analysis: What Needs to Be Built for Phase 08

### 4.1 Database Models & Migration
We need a dedicated data model to persist extracted design systems, ensuring tenant isolation and audit association:
- **`DesignSystemAnalysis`**:
  - `id`: UUID (PK)
  - `tenant_id`: UUID (FK to tenants)
  - `project_id`: UUID (FK to projects)
  - `audit_id`: UUID (FK to audits)
  - `status`: String (`pending`, `analyzing`, `completed`, `failed`)
  - `consistency_score`: Float (0–100)
  - `score_breakdown_json`: Text (category scores: colour, typography, spacing, components, surfaces, navigation)
  - `extraction_coverage`: Float (0–1)
  - `confidence`: Float (0–1)
  - `summary`: Text
  - `color_palette_json`: Text (extracted colours with semantic name, hex, category, screens, frequency, confidence, evidence)
  - `typography_json`: Text (extracted typography patterns with size, weight, line-height, hierarchy, screens, confidence)
  - `spacing_layout_json`: Text (margins, padding, gaps, card padding, grid patterns, content widths)
  - `shapes_surfaces_json`: Text (border radii, button/input/card shapes, elevation, shadows, surface treatments)
  - `components_json`: Text (identified repeated components, visual variations, occurrences, recommended specs)
  - `tokens_json`: Text (proposed design tokens: `color.*`, `typography.*`, `spacing.*`, `radius.*`, `shadow.*`)
  - `consistency_issues_json`: Text (cross-screen inconsistencies, severity, affected screens, recommended fixes)
  - `recommendations_json`: Text (actionable steps to standardise the design system)
  - `limitations_json`: Text (missing evidence, uncertainty, approximate measurements)
  - `provider`: String
  - `model`: String
  - `created_at`, `updated_at`, `completed_at`

### 4.2 Design System Extraction Service (`backend/app/services/design_system.py`)
- Extraction algorithms:
  - Colour palette extraction with HEX measurement, semantic naming, frequency, confidence, and evidence classification (`observed`, `approximate`, `inferred`).
  - Typography analysis (hierarchy from `heading.large` down to `label` and `button`, approximate sizes, font weight categories).
  - Spacing & layout analysis (margins, padding, gaps, card padding, grid alignment).
  - Shape & surface analysis (border radii, button/input/card shapes, elevation, shadows).
  - Component clustering & pattern detection (buttons, text inputs, search fields, cards, navbars, sidebars, tabs, modals, badges, list items).
  - Design token generation with standard token names (`color.*`, `typography.*`, `spacing.*`, `radius.*`, `shadow.*`).
  - Cross-screen consistency evaluation across 10 dimensions, respecting intentional variations (destructive buttons, disabled states, modal spacing, responsive layouts).
  - Reproducible consistency scoring model with documented mathematical formula.
  - Deterministic test provider (`DeterministicDesignSystemProvider`) for reliable, quota-free test execution.

### 4.3 Google Stitch Prompt Generator Extension
- Add `generate_design_system_refinement_prompt()` to `app/services/prompt_generator.py` incorporating:
  1. Extracted visual foundations (colours, typography, spacing, radius).
  2. Identified component patterns and variations.
  3. Identified visual inconsistencies and targeted fixes.
  4. Proposed design tokens.
  5. Preservation directives for product identity.
  6. Clear instructions to standardise components across all screens.

### 4.4 API Endpoints
- `POST /projects/{project_id}/audits/{audit_id}/design-system/extract`: Trigger design system extraction for an audit.
- `GET /projects/{project_id}/audits/{audit_id}/design-system`: Retrieve the design system analysis report.
- `GET /projects/{project_id}/audits/{audit_id}/design-system/export/json`: Export tokens & components as JSON.
- `GET /projects/{project_id}/audits/{audit_id}/design-system/export/css`: Export design tokens as CSS Custom Properties (`:root { ... }`).
- `POST /projects/{project_id}/audits/{audit_id}/design-system/stitch-prompt`: Generate Google Stitch design system refinement brief.
- `GET /projects/{project_id}/design-systems`: List design system analyses for a project.

### 4.5 Frontend Implementation
- Update `app/design-system/page.tsx` to render the full interactive Design System intelligence suite:
  - Design System Overview (Consistency score gauge, coverage, confidence, summary).
  - Interactive Colour Palette (swatches, HEX values, copy-to-clipboard, categories, screen references).
  - Typography scale & visual hierarchy with uncertainty badges.
  - Spacing & Surface treatments (spacing scale, border radius preview, elevation/shadow cards).
  - Component pattern library with observed occurrences, variations, and recommended component specifications.
  - Cross-screen consistency issues list with severity, affected screens, and recommended fixes.
  - Design Tokens table with search, category filtering, copy token name/value, and "Copy All Tokens".
  - One-click export modal/actions for JSON and CSS custom properties.
  - Google Stitch Design System Refinement Prompt modal with copy-and-handoff instructions.
- Add "Extract Design System" entry point in `components/multi-screen-workspace.tsx`.

---

## 5. Architectural Risks & Mitigations

1. **Hallucination of Exact Font Families or Pixel Dimensions from Screenshots**:
   - *Risk*: A pure vision LLM might fabricate exact font names ("Inter Regular 14px") that cannot be verified from a compressed JPEG/PNG.
   - *Mitigation*: Strictly enforce evidence classification: `observed` (general shape/hierarchy), `approximate` (estimated size/rem/px), or `inferred` (likely font category e.g. "sans-serif neutral"). Mark exact font family as unknown unless backed by explicit visual/knowledge evidence.
2. **False Positives on Contextual Visual Variations**:
   - *Risk*: A red button on an account deletion screen being flagged as an "inconsistent primary button".
   - *Mitigation*: Embed explicit contextual rules into prompt and evaluation engine: destructive actions, disabled states, active tab highlights, and modal contexts are recognized as intentional design variations, not inconsistencies.
3. **Reproducibility of Consistency Score**:
   - *Risk*: An LLM hallucinating random arbitrary consistency numbers between runs.
   - *Mitigation*: The score must be computed deterministically via a documented mathematical formula (`docs/DESIGN_SYSTEM_SCORING.md`) based on quantifiable consistency infractions, weighted by category and severity, normalized by evaluated screen count and available evidence.

---

## 6. Audit Sign-Off

The existing codebase is in an exemplary state. All 96 tests pass, Next.js build is clean, and the multi-screen abstractions provide the exact foundation needed for design system extraction. Proceeding directly with Phase 08 implementation.
