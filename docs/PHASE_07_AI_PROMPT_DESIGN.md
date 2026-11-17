# Phase 07 Multi-Screen User-Flow Analysis Architecture

_See [`PHASE_07_MULTI_SCREEN_ARCHITECTURE.md`](./PHASE_07_MULTI_SCREEN_ARCHITECTURE.md) for the full system design._

This document provides supplementary details on the AI prompt design for multi-screen flow analysis.

---

## AI Prompt Architecture

### System Prompt (`MULTI_SCREEN_SYSTEM_PROMPT`)

The system prompt establishes the AI as a senior UX researcher specialising in multi-screen product evaluation. It instructs the model to:

1. Evaluate each screen independently for screen-level issues.
2. Compare all screens together for cross-screen patterns.
3. Produce a structured `JourneyReport` covering strengths, friction, and recommendations.
4. Respect static screenshot constraints — never infer interactions.
5. Calibrate evidence to only what is visually observable.

### User Prompt Template (`MULTI_SCREEN_USER_PROMPT_TEMPLATE`)

The user prompt includes:
- Journey context (name, product, intended user, objective, start, end).
- Screen inventory (index, label, description for each screen).
- RAG context from Phase 06 knowledge library (if available).
- Explicit output format specification with JSON schema.

### JSON Output Schema (abbreviated)

```json
{
  "screen_findings": [
    {
      "audit_screen_index": 0,
      "title": "...",
      "description": "...",
      "severity": "high",
      "category": "...",
      "recommended_fix": "...",
      "evidence": "...",
      "bounding_boxes": [
        { "screen_index": 0, "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.1 }
      ]
    }
  ],
  "cross_screen_findings": [
    {
      "affected_screen_indices": [0, 2, 4],
      "title": "...",
      "description": "...",
      "severity": "medium",
      "category": "...",
      "recommended_fix": "...",
      "evidence": "..."
    }
  ],
  "journey_report": {
    "journey_summary": "...",
    "apparent_flow_structure": "...",
    "overall_assessment": "...",
    "strengths": [{ "title": "...", "description": "..." }],
    "major_friction_points": [{ "title": "...", "description": "..." }],
    "recommended_improvements": ["...", "..."],
    "limitations": "..."
  }
}
```

### Index-to-UUID Mapping

The AI model references screens by their zero-based index (e.g. `audit_screen_index: 2`). The backend service maps these to actual `AuditScreen` UUIDs before persisting findings. `affected_screen_indices` in cross-screen findings are similarly mapped to `affected_screen_ids_json` (UUID array).
