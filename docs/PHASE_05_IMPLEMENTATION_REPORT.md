# Phase 05 Implementation Report: Finding Review & Google Stitch Prompt Generation

**Date:** November 17, 2026  
**Status:** Completed & Validated  
**Scope:** Phase 05 of Forteux UI/UX Auditor  

---

## 1. Executive Summary

Phase 05 bridges the gap between diagnostic UI/UX auditing and active interface redesign. It provides a robust, multi-stage workflow:
1. **Finding Review & Management**: An interactive review surface where users inspect AI vision findings, view synchronized bounding boxes on the visual canvas, toggle individual findings, select/deselect all, and review high-level selection metrics (total, selected, critical, high, excluded).
2. **AI-Powered Google Stitch Prompt Generator**: A server-side engine that transforms selected findings into a comprehensive, structured redesign brief with 8 distinct, deterministic sections designed specifically for Google Stitch.
3. **Location Translation**: Automatic translation of normalized bounding box coordinates into human-readable layout regions (e.g. "Top-Right section (approx. x: 80%, y: 5%, width: 15%, height: 6%)") so the generative design model understands the spatial context.
4. **Prompt Versioning & Persistence**: A dedicated schema with `AuditPrompt` and `PromptVersion` database models and Alembic migrations, enabling version history tracking across regenerations, dirty manual edit detection, and single-click restoration of original AI-generated briefs.
5. **Interactive Prompt Editor Dialog**: In-browser prompt editing with copy-to-clipboard, version history chip navigation, optional user design preferences input, outdated-selection detection banners, and Google Stitch handoff instructions.
6. **Rigorous Test Validation**: 44 backend pytest tests (including 9 comprehensive Phase 05 tests covering tenant isolation, selection filtering, cross-audit finding rejection, versioning, manual editing/restoring, and prompt quality evaluation).

---

## 2. Key Components Delivered

### 2.1 Database Models & Migration
- **Models** ([backend/app/db/models.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/db/models.py)):
  - `AuditPrompt`: Persists the active prompt for an audit, storing `content`, `original_content`, `user_instructions`, `version_number`, and `selected_finding_ids_json`.
  - `PromptVersion`: Stores immutable historical snapshots of generated prompts with `version_number`, `content`, `selected_finding_ids_json`, and timestamp.
- **Alembic Migration** ([backend/migrations/versions/0003_audit_prompts_and_versions.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/versions/0003_audit_prompts_and_versions.py)):
  - Created tables `audit_prompts` and `prompt_versions` with foreign keys to `audits` and indexes on `audit_id`.
  - Upgrades and downgrades verified via test suite.

### 2.2 Prompt Generation Engine
- **Service** ([backend/app/services/prompt_generator.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/services/prompt_generator.py)):
  - `StitchPromptGenerator`: Formulates the 8-section redesign brief:
    1. Role & Objective (sets persona as Principal UI/UX Designer & Google Stitch prompt engineer)
    2. Existing Interface Context (product name, user goal, target audience, screen geometry, visual baseline)
    3. Core Design Objectives (derived dynamically from the categories of selected findings)
    4. Prioritized Issues & Solutions (ordered by severity: critical > high > medium > low, with translated spatial coordinates and design principles)
    5. Visual Design Requirements (8pt/4pt layout grid, typographic contrast scale, button hierarchy, perceptual contrast, visual economy)
    6. User-Specified Design Instructions (optional user preferences)
    7. Strict Design Constraints (preservation of product purpose, essential content, and avoiding unrelated layout churn)
    8. Expected Output for Google Stitch (handoff guidelines, screenshot upload advice, Figma token alignment note)
  - `describe_region(box)`: Maps normalized coordinates into intuitive layout descriptors (e.g. "Top-Left", "Center-Right", "Bottom-Center").

### 2.3 API Endpoints
- **Routes** ([backend/app/api/v1/routes.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/api/v1/routes.py)):
  - `POST /projects/{project_id}/audits/{audit_id}/prompt`: Generates or regenerates a Stitch prompt. Validates that every selected finding ID belongs to the target audit and current tenant. Tracks incrementing versions in `prompt_versions`.
  - `GET /projects/{project_id}/audits/{audit_id}/prompt`: Retrieves the active prompt and its complete version history list.
  - `PATCH /projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}`: Updates user manual edits to the prompt content.
  - `POST /projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}/restore-original`: Reverts content back to `original_content`.

### 2.4 Frontend Review & Generator Workspace
- **Workspace** ([components/audit-workspace.tsx](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/components/audit-workspace.tsx)):
  - **Selection Controls**: All findings selected by default on load. Support for toggling individual items, "Select all", and "Deselect all".
  - **Selection Summary Bar**: Displays selected vs total count, critical and high severity counts, and excluded count.
  - **Visual Canvas Synchronization**: Deselected findings show dimmed/dashed bounding boxes on the screenshot viewer (`.annotation-box-deselected`), providing clear visual feedback on what is included vs excluded.
  - **Prompt Editor Modal (`PromptDialog`)**:
    - Direct editing in a full-sized textarea.
    - Version history chips for switching between previous prompt versions.
    - Dirty edit indicator (`Edited manually`) with single-click `Restore original` action.
    - Warning banner when workspace selections change after a prompt has been generated.
    - Optional user instructions input field.
    - Copy to clipboard with success feedback.
    - Handoff instructions linking to `https://stitch.withgoogle.com`.

---

## 3. Verification & Test Summary

| Test Suite | Total Tests | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- |
| Database Migrations | 1 | 1 | 0 | **PASS** |
| Auth & Multi-Tenancy | 5 | 5 | 0 | **PASS** |
| Projects & Audits CRUD | 5 | 5 | 0 | **PASS** |
| Asset Storage & Validation | 9 | 9 | 0 | **PASS** |
| Single-Screen AI Vision | 10 | 10 | 0 | **PASS** |
| Bounding Box IoU Benchmark | 5 | 5 | 0 | **PASS** |
| **Phase 05 Prompt Generation** | **9** | **9** | **0** | **PASS** |
| **Total Backend Tests** | **44** | **44** | **0** | **PASS** |

---

## 4. Architectural Boundaries Observed

- **No Speculative Direct Stitch API**: Because Google Stitch does not offer a public programmatic API, the handoff relies on prompt generation, clipboard copy, and visual asset handoff guidance.
- **No Multi-Screen Flow Auditing**: Excluded from Phase 05 scope; strictly preserved for Phase 06.
- **No Knowledge Base RAG**: Excluded from Phase 05 scope; strictly preserved for Phase 07.
- **Tenant Isolation**: Strictly enforced at database query and API level; foreign finding IDs are rejected with HTTP 400 (`invalid_findings`).
