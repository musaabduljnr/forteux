# Design System Extraction & Cross-Screen Consistency Architecture

**Document Version**: 1.0  
**Phase**: Phase 08 — Design System Intelligence  
**Author**: Forteux AI Core Team  

---

## 1. Architectural Overview

The **Design System Extraction Engine** is a core intelligence capability of Forteux that analyzes collections of interface screenshots to discover, extract, and formalize the underlying visual design language.

Rather than treating interface screens as disconnected static bitmaps, the system evaluates screens collectively across 6 foundational visual dimensions and 10 cross-screen consistency dimensions.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        UPLOADED SCREENSHOTS                            │
│                 (Multi-Screen Sequence or Audit Set)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 DesignSystemExtractionService                          │
│                                                                        │
│   1. Multi-modal Computer Vision Analysis                              │
│   2. Palette & HEX Extraction (Color Tokens)                           │
│   3. Typography Hierarchy & Weight Scaling (Type Tokens)               │
│   4. Spacing Scale & Layout Rhythm Analysis (Spacing Tokens)           │
│   5. Shape, Border Radii & Elevation Analysis (Radius/Shadow Tokens)   │
│   6. Repeated Component Pattern Clustering                             │
│   7. Cross-Screen Visual Inconsistency Detection                       │
│   8. Contextual Immunity Rules (Filters intentional variations)        │
│   9. Mathematical Consistency Score Calculation                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   STRUCTURED EXTRACTION REPORT                         │
│                                                                        │
│  - Consistency Score (0–100) & Category Breakdown                      │
│  - Extraction Coverage & Confidence Metrics                            │
│  - Proposed Semantic Design Tokens (color.*, typography.*, etc.)       │
│  - Reusable Component Specifications                                   │
│  - Target Cross-Screen Inconsistencies & Fixes                         │
└──────────────┬────────────────────┬───────────────────┬────────────────┘
               │                    │                   │
               ▼                    ▼                   ▼
    ┌────────────────────┐ ┌────────────────┐ ┌─────────────────────────┐
    │  CSS Custom Props  │ │  JSON Export   │ │ Google Stitch Redesign  │
    │  (:root { ... })   │ │  Tokens Schema │ │ Prompt Brief (10 Parts) │
    └────────────────────┘ └────────────────┘ └─────────────────────────┘
```

---

## 2. Foundational Visual Extraction Domains

### 2.1 Colour Analysis
- **HEX Measurement**: Primary, secondary, accent, surface, background, text, border, and status hues.
- **Semantic Naming**: Human-intelligible token roles (e.g. `Brand Primary Blue`, `Canvas Surface Background`).
- **Evidence Classification**:
  - `observed`: Direct high-confidence pixel measurement on solid background.
  - `approximate`: Color subject to subtle anti-aliasing or overlay compression.
  - `inferred`: Estimated token role based on context.

### 2.2 Typography Hierarchy
- **Hierarchy Mapping**: Scales from `display`, `h1`, `h2`, `h3` down to `body`, `caption`, and `button`.
- **Measurement**: Font size estimates (`24px / 1.5rem`), font weight categories (`bold`, `semibold`, `regular`), alignment, and estimated line-heights.
- **Safety Rule**: Font families are classified as neutral system sans-serif unless explicitly attested by visual branding or project guidelines.

### 2.3 Spacing & Layout Rhythm
- **Rhythm Identification**: Page margins, content padding, section spacing, component gaps, card internal padding, and grid arrangements.
- **Token Harmonization**: Maps observed pixel spacing to proposed semantic step scale (`spacing.1` [4px], `spacing.2` [8px], `spacing.4` [16px], `spacing.6` [24px]).

### 2.4 Shapes, Radii & Surface Treatments
- **Corner Curves**: Border radii clustering (e.g. `6px` subtle, `8px` container, `9999px` pill).
- **Surfaces & Shadows**: Borders (color, width, style), elevation shadows, card containers, and modal layers.

### 2.5 Repeated Component Clustering
- **Pattern Recognition**: Groups visually similar interactive elements across screens (primary buttons, secondary buttons, text inputs, search fields, cards, navbars, tab bars, badges).
- **Variations Tracking**: Identifies intentional vs unintentional drift (e.g. padding variance between screen 1 and screen 2).
- **Target Component Specification**: Canonical specification for developers and designers to standardize implementations.

---

## 3. Data Model & Entity Relationship

### `DesignSystemAnalysis`
- Stored in `design_system_analyses` table.
- Multi-tenant security: strictly scoped to `tenant_id` and `project_id`, cascading from `audit_id`.
- Stores raw structured extractions in verified JSON text columns.
- Stores deterministic score, category breakdown, coverage, confidence, and generated Google Stitch refinement prompt.

---

## 4. Google Stitch Prompt Integration

The extraction service generates an actionable 10-section design refinement brief for Google Stitch:
1. Executive Directive & Audit Context.
2. Core Directives for Google Stitch (preserve identity, standardize components, strict token uniformity).
3. Color Palette & Token System.
4. Typography Hierarchy Scale.
5. Spacing, Shapes & Surface Treatments.
6. Reusable Component Standards & Specifications.
7. Targeted Cross-Screen Inconsistencies to Resolve.
8. User Custom Instructions (if provided).
9. Design System Harmonization Action Plan.
10. Google Stitch Handoff & Generation Protocol.
