# Phase 07 Findings Schema

## Overview

Phase 07 extends the Phase 04 findings schema with two new fields to support multi-screen analysis: `scope` and `affected_screen_ids`. These fields are added to the `findings` table via migration `0005_multi_screen_flow`.

---

## Database Schema

### findings table (Phase 07 additions)

```sql
scope                 VARCHAR(20)  DEFAULT 'screen_level'
                      CHECK scope IN ('screen_level', 'cross_screen')

affected_screen_ids_json  TEXT     -- JSON array of audit_screen UUIDs
                                   -- NULL or [] for screen_level findings
```

### audit_screens table (Phase 07 addition)

```sql
screen_description  TEXT  -- Optional description of what this screen represents
```

### analysis_jobs table (Phase 07 addition)

```sql
flow_report_json  TEXT  -- Serialised JourneyReport JSON object
```

---

## Finding Scopes

| Scope | Meaning | `affected_screen_ids` |
|---|---|---|
| `screen_level` | Issue found on a single screen | `[]` or omitted |
| `cross_screen` | Issue spanning two or more screens | List of `AuditScreen` UUIDs |

All existing Phase 04 findings have `scope = 'screen_level'` by default (migration sets `DEFAULT 'screen_level'`).

---

## Multi-Screen Bounding Box Schema

Multi-screen bounding boxes extend the Phase 04 bounding box format with a `screen_id` field to identify which screen the box belongs to.

```typescript
interface MultiScreenBoundingBox {
  screen_id: string;   // UUID of the AuditScreen
  x: number;           // Normalised [0, 1] from left edge
  y: number;           // Normalised [0, 1] from top edge
  width: number;       // Normalised [0, 1]
  height: number;      // Normalised [0, 1]
  label?: string;
}
```

**Coordinate convention:** All values are normalised relative to the individual screen's dimensions (`[0, 1]`), not the viewport. The frontend scales boxes to the rendered image size.

---

## API Read Schema

### FindingRead (single-screen, unchanged)

```typescript
interface FindingRead {
  id: string;
  audit_id: string;
  audit_screen_id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  recommended_fix: string;
  evidence: string | null;
  bounding_boxes: BoundingBoxRead[];
  scope: "screen_level" | "cross_screen";
  affected_screen_ids: string[];
  created_at: string;
}
```

### MultiScreenFindingRead

```typescript
interface MultiScreenFindingRead {
  id: string;
  audit_id: string;
  audit_screen_id: string | null;    // null for pure cross-screen findings
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  recommended_fix: string;
  evidence: string | null;
  bounding_boxes: MultiScreenBoundingBoxRead[];
  scope: "screen_level" | "cross_screen";
  affected_screen_ids: string[];     // non-empty for cross_screen scope
  created_at: string;
}
```

---

## Migration

**File:** `backend/migrations/versions/0005_multi_screen_flow.py`

Adds all Phase 07 columns. Downgrade removes them. Both directions tested clean.
