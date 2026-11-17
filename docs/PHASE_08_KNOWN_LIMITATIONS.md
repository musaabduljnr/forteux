# Phase 08 Known Limitations & Boundaries

**Document Version**: 1.0  
**Phase**: Phase 08 — Design System Extraction & Consistency  
**Author**: Forteux AI Core Team  

---

## 1. Visual & Computer Vision Boundaries

### 1.1 Font Family Attribution
- **Limitation**: Typeface font families (e.g. *Inter*, *Roboto*, *SF Pro*) cannot be determined with mathematical certainty from raster screenshots due to glyph compression, anti-aliasing, and platform font smoothing.
- **System Behavior**: The system classifies typography as `approximate` or `inferred` (e.g. "geometric sans-serif") and does not claim exact font family names unless substantiated by uploaded project brand guidelines.

### 1.2 Exact Pixel Precision
- **Limitation**: Screen dimensions, padding, margins, and line heights are measured from rendered viewport pixels. Minor sub-pixel rendering variances (e.g. 15.5px vs 16px) may occur based on display device scaling (1x, 2x, 3x DPR).
- **System Behavior**: Spacing tokens are rounded to the nearest standard 4px/8px modular scale and flagged with confidence scores.

### 1.3 State Unobservability
- **Limitation**: Static screenshots cannot capture hover transitions, active press states, focus rings, disabled transitions, skeleton loaders, or keyboard focus styling.
- **System Behavior**: Extracted components reflect only the visual states captured in the uploaded screenshots.

### 1.4 Dynamic Shadows & Glassmorphism
- **Limitation**: Multi-layered backdrop filters, blur radiuses, and complex composite shadows cannot be decompiled into exact CSS box-shadow formulas from flat pixels alone.
- **System Behavior**: Shadows are classified as `inferred` elevation approximations based on visual spread.

---

## 2. Scope Boundaries (Strict Phase 08 Constraints)

In compliance with Phase 08 requirements, the following capabilities are explicitly out of scope:
1. **Figma API Integration**: No bidirectional Figma token synchronization or automated Figma file creation.
2. **Automated Production Code Generation**: The engine extracts tokens, components, and CSS custom properties; it does not generate full React, Vue, or Angular production code components.
3. **Interactive Design Editor**: Forteux provides design system intelligence and Google Stitch prompt generation, not an in-browser vector graphics or design canvas editor.
4. **Behavioral Usability Testing**: The consistency score measures visual design uniformity, not conversion rate, user task success, or behavioral telemetry.
