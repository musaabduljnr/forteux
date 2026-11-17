# Phase 07 Known Limitations

## Static Screenshot Constraints

### 1. No Interaction Testing
Multi-screen analysis is based on static screenshots. The AI cannot observe:
- Hover states or focus rings
- Transition animations between screens
- Dynamic content loading (skeleton screens, spinners completing)
- Form validation on input
- Touch gestures or swipe patterns

**Impact:** Findings are based solely on what is visually present in each screenshot at a single moment in time.

### 2. No OCR or Text Extraction
The AI model processes screenshots as images. It does not perform structured OCR. Text content visible in screenshots is interpreted by the vision model, which may misread small or low-contrast text.

**Impact:** Findings about copy quality, error messages, and microcopy are approximate.

### 3. Assumed Screen Order
The AI evaluates screens in the user-defined sequence. If the user orders screens incorrectly, the cross-screen analysis will reflect that incorrect order and may produce misleading findings.

**Impact:** Users must verify screenshot order before running flow analysis.

### 4. No Deep Link Context
The analysis cannot determine whether a screen reached via a deep link (e.g. from an email) differs from the same screen reached through normal navigation. All screens are treated as reached through the declared journey sequence.

---

## AI Model Constraints

### 5. Rate Limits
Multi-screen analysis sends a larger payload (all screenshots + prompt) in a single API call. During peak usage, this may hit model rate limits more quickly than single-screen analysis.

**Impact:** Flow analysis may be slower or temporarily unavailable under high load.

### 6. Screen Count Limit
The current implementation supports a maximum of 10 screens per flow analysis. This is a practical limit to manage prompt size and API cost.

**Impact:** Journeys with more than 10 screens must be split into sub-flows.

### 7. Hallucination Risk on Dense UIs
Complex, information-dense screens (e.g. dashboards with many elements) increase the risk that the AI model misidentifies elements or misattributes bounding box coordinates.

**Impact:** Bounding box overlays may be imprecise on highly dense screens. Users should treat bounding boxes as approximate guides.

---

## Retrieval and RAG

### 8. RAG Coverage
Phase 06 knowledge retrieval is embedded into the multi-screen prompt, but the retrieved chunks are limited by the configured top-k and similarity threshold. Highly specific design guidelines may not surface if they are not semantically similar to the finding descriptions.

**Impact:** Knowledge library citations may not cover all relevant findings.

---

## Frontend

### 9. No Real-Time Reordering Drag-and-Drop (Multi-Screen Workspace)
The `MultiScreenWorkspace` component does not implement drag-and-drop reordering. Screen reordering is available through the backend API (`POST /screens/reorder`) but not exposed as a drag-and-drop interaction in the multi-screen workspace UI.

**Impact:** Users who need to reorder screens after uploading must use the audit creation flow.

### 10. No In-Place Screen Replacement
Replacing a screenshot for an existing screen requires deleting the screen and re-uploading a new one. There is no in-place image replacement in the current UI.
