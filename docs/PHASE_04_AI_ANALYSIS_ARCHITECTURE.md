# Phase 04: AI Vision Analysis Architecture

## 1. Overview

The Forteux Vision Analysis Engine delivers structured, evidence-based UI/UX evaluation of static interface screenshots. It operates under strict grounding constraints, separating visible observations from behavioral inferences.

---

## 2. Component Diagram

```mermaid
flowchart TD
    Client["Next.js Workspace\n(Browser)"] -->|POST /audits/{id}/analyze| API["FastAPI Route Handler\n(/api/v1/.../analyze)"]
    API -->|Retrieve Image Bytes| S3["Storage Service\n(MinIO / S3)"]
    API -->|Fetch Screen Dimensions| DB["PostgreSQL Database\n(ScreenAsset & AuditScreen)"]
    API -->|Dispatch Job| Service["AIVisionService"]
    Service -->|Execute Prompt & Image| Provider["VisionProvider Protocol"]
    subgraph Vision Implementations
        Provider --> LLM["Cloud LLM Provider\n(Gemini 1.5 Pro / GPT-4o)"]
        Provider --> Det["DeterministicVisionProvider\n(Local Structural CV Engine)"]
    end
    Provider -->|Parse & Clamp Boxes| Validation["Pydantic Validation\n(BoundingBox, FindingResult)"]
    Validation -->|Persist Job & Findings| DB
    Validation -->|Structured JSON Response| Client
    Client -->|Render Canvas Overlay| Overlay["Bounding Box & Annotation Overlay"]
```

---

## 3. Evaluation Dimensions

The AI Vision Engine inspects screenshots across 7 structured domains:

| Category | Identifier | Description | Visual Locatability |
| :--- | :--- | :--- | :--- |
| **Visual Hierarchy** | `visual_hierarchy` | Prominence, primary vs. secondary action competition, reading order | Yes (Bounding Box) |
| **Layout & Spacing** | `layout_spacing` | Alignment, padding inconsistency, crowded cards, edge density | Yes (Bounding Box) |
| **Typography** | `typography` | Font size scale differentiation, line-length, heading hierarchy | Yes (Bounding Box) |
| **Color & Contrast** | `color_contrast` | Visual legibility, background separation, emphasis cues | Yes (Bounding Box) |
| **Components & Consistency** | `components_consistency` | Border radii variations, button styling discrepancies | Yes (Bounding Box) |
| **Usability** | `usability` | Ambiguous affordances, action placement, cognitive load | Yes (Bounding Box) |
| **Accessibility Indicators**| `accessibility_indicator`| Small text, low luminance distinction, reliance on color | Yes (Bounding Box) |

---

## 4. Bounding Box Geometry & Normalization

Coordinates are strictly normalized as floating-point decimals within $[0.0, 1.0]$:
- $x$: Horizontal offset from the left edge of the image, divided by image width.
- $y$: Vertical offset from the top edge of the image, divided by image height.
- $width$: Box width divided by image width.
- $height$: Box height divided by image height.

### Boundary Clamping Rules
Every bounding box passes through Pydantic field validators:
```python
@field_validator("width")
@classmethod
def clamp_width(cls, v: float, info: Any) -> float:
    x = info.data.get("x", 0.0)
    if x + v > 1.0:
        return round(max(0.01, 1.0 - x), 4)
    return v
```
This guarantees that no bounding box can clip outside the rendered image frame.

---

## 5. Grounding & Anti-Hallucination Rules

1. **Evidence Typing**: Findings are partitioned into:
   - `observed`: Direct visual facts verifiable from pixel data (e.g. "two buttons in the top navbar have equal 40px height and identical primary blue fills").
   - `inferred`: Expected usability friction derived from human-computer interaction heuristics (e.g. "equal prominence increases decision latency under Hick's Law").
2. **Contrast Measurement Guardrail**: LLMs must never invent numeric contrast ratios (e.g. "Contrast is 3.2:1"). Unless exact pixel sampling is performed, contrast is flagged as an observable perceptual indicator:
   - *Valid*: "Small helper text in light gray against a pale background exhibits potentially low visual contrast."
   - *Forbidden*: "Fails WCAG 2.1 AA with 3.1:1 ratio."
3. **Static Screenshot Boundaries**: The engine never claims to evaluate:
   - Screen-reader navigation or ARIA accessibility trees.
   - Keyboard tab order or focus management.
   - Network loading states or server response times.
   - Hidden views, dropdown menus, or hover tooltips.
