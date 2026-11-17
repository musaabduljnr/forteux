# Phase 07 Multi-Screen Architecture

## Overview

The multi-screen analysis system extends the existing single-screen AI vision pipeline to reason across an ordered sequence of screenshots representing a complete user journey. It introduces three layers of analysis: individual screen assessment, cross-screen pattern detection, and journey-level evaluation.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        POST /analyze-flow                           │
│                  (mode=multi, ≥2 screens required)                  │
└─────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   MultiScreenAIVisionService                        │
│                                                                     │
│  1. Load ordered AuditScreens (sequence_index ASC)                  │
│  2. Fetch signed URLs for each screenshot                           │
│  3. Build ScreenContext list (id, label, description, dimensions)   │
│  4. Retrieve RAG citations from KnowledgeService                    │
│  5. Build MULTI_SCREEN_USER_PROMPT_TEMPLATE                         │
│  6. Send all screen images + prompt to AI provider                  │
│  7. Parse MultiScreenAnalysisResult                                 │
│  8. Persist findings (screen_level + cross_screen)                  │
│  9. Store flow_report_json on AnalysisJob                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Screen Sequencing

Screens are ordered by `AuditScreen.sequence_index` (integer, unique per audit). The sequence is maintained through:

- **Attach**: each new screen receives `max(sequence_index) + 1`.
- **Reorder**: two-pass assignment avoids unique constraint violations.
  - Pass 1: set all to `-(idx + 1)` (temporary negatives).
  - Pass 2: set all to final target indices.
- **Delete**: gaps are allowed; ordering is preserved by relative index.

---

## Multi-Screen Vision Service

### `MultiScreenAIVisionService`

```python
class MultiScreenAIVisionService:
    async def analyze_flow(
        self,
        audit_id: UUID,
        screens: list[AuditScreen],
        db: Session,
        rag_context: str | None = None,
    ) -> MultiScreenAnalysisResult
```

**Inputs:**
- Ordered list of `AuditScreen` objects with signed screenshot URLs.
- Optional RAG context from Phase 06 KnowledgeService.

**Outputs:**
- `screen_findings: list[MultiScreenFinding]` — per-screen issues.
- `cross_screen_findings: list[MultiScreenFinding]` — cross-screen issues.
- `journey_report: JourneyReport` — overall flow evaluation.

### Provider Strategy

The service uses the existing AI provider abstraction from Phase 04. The same provider that handles single-screen vision (Google Gemini 2.0 Flash, with deterministic fallback for tests) handles multi-screen analysis.

A `DeterministicMultiScreenProvider` is injected in tests to return structured fixture data without hitting the AI API.

---

## Image Batching

All screen images are sent in a single API call. The prompt instructs the model to reason about each screen individually (screen-level findings) and then across all screens together (cross-screen findings).

This avoids a fan-out approach (one call per screen) that would miss cross-screen patterns. The trade-off is a larger prompt, constrained by model context limits.

**Current limit:** 10 screens per flow analysis. The API returns a 400 error if more than 10 screens are submitted.

---

## Data Persistence

### AuditScreen

```
screen_description: TEXT  (phase 07 addition)
```

### Finding

```
scope: VARCHAR(20)  CHECK IN ('screen_level', 'cross_screen')
affected_screen_ids_json: TEXT  (JSON array of audit_screen UUIDs)
```

### AnalysisJob

```
flow_report_json: TEXT  (serialised JourneyReport)
```

---

## API Endpoints (Phase 07)

| Method | Path | Description |
|---|---|---|
| `PATCH` | `/projects/{pid}/audits/{aid}/screens/{sid}` | Rename screen / set description |
| `DELETE` | `/projects/{pid}/audits/{aid}/screens/{sid}` | Remove screen from audit |
| `POST` | `/projects/{pid}/audits/{aid}/screens/reorder` | Reorder screen sequence |
| `PATCH` | `/projects/{pid}/audits/{aid}/context` | Set journey context |
| `POST` | `/projects/{pid}/audits/{aid}/analyze-flow` | Run multi-screen analysis |
| `GET` | `/projects/{pid}/audits/{aid}/flow-report` | Retrieve journey report |

All endpoints enforce JWT authentication and audit ownership via the existing `get_current_user` dependency.

---

## Frontend Architecture

### Component: `MultiScreenWorkspace`

Three-panel layout:

```
┌──────────────────────────────────────────────────────────────┐
│  Left Panel         │  Centre Panel       │  Right Panel     │
│  Screen Sequence    │  Screenshot Viewer  │  Findings Panel  │
│  (ordered list)     │  + Bounding Box     │  Tabs:           │
│                     │  Overlay            │  · Screen Issues  │
│  [Analyse Flow]     │                     │  · Cross-Screen  │
│  [Generate Brief]   │  ← Prev / Next →   │  · Journey View  │
└──────────────────────────────────────────────────────────────┘
```

### Component: `AuditPageRouter`

Reads `audit.mode` from `useAppState()` and conditionally renders:
- `mode === "multi"` → `<MultiScreenWorkspace />`
- otherwise → `<AuditWorkspace />` (single-screen, unchanged)
