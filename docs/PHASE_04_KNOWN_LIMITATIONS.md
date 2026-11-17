# Phase 04: Known Limitations & System Boundaries

This document outlines intentional design constraints and technical limitations present in Phase 04 of the Forteux UI/UX Auditor.

---

## 1. Single-Screen Static Image Boundaries

### 1.1 Non-Observable Dynamic States
Static screenshots represent a single point-in-time visual rendering of an interface. The AI Vision Engine cannot:
- **Inspect Hover, Focus, or Active States**: Micro-interactions, button hover states, focus rings, and active press feedback cannot be observed from a static PNG/JPEG.
- **Inspect Dropdowns, Overlays, & Modals**: Hidden menus, dialog drawers, tooltips, and toast notifications that are not active at the instant of screenshot capture cannot be evaluated.
- **Inspect Responsive Reflow**: The system evaluates the screenshot at its rendered aspect ratio and dimensions; it cannot deduce how layout elements rearrange across different viewport breakpoints without separate screenshots for each breakpoint.

### 1.2 Contrast & Accessibility Inferences
- **No Direct DOM or CSS Access**: Because the engine operates on raster pixels without rendered CSS or DOM hierarchy, exact font sizes, line heights, and computed hex values are approximations.
- **WCAG Compliance**: The system flags *potential* visual contrast concerns as visual observations, but does not calculate certified mathematical WCAG contrast ratios. Full accessibility audits require live DOM inspection with automated tree traversals (e.g. axe-core).
- **Assistive Technology**: Screen-reader traversal order, semantic HTML elements (`<nav>`, `<header>`, `role="alert"`), aria labels, and keyboard tab stops cannot be determined from pixel data.

---

## 2. Multi-Screen Flow Analysis (Deferred to Phase 05)

- **Sequential Comparison**: Evaluation of user journeys across a sequence of screens (e.g. cart $\rightarrow$ checkout $\rightarrow$ order confirmation) is intentionally omitted from Phase 04.
- **Cross-Screen Consistency**: Detection of mismatched button styles, inconsistent typography, or divergent color schemes between distinct screens is part of Phase 05.

---

## 3. Knowledge Base & Prompt Generation (Deferred to Subsequent Phases)

- **Knowledge Document Retrieval (RAG)**: Ingestion of internal design systems, brand guidelines, and UX heuristics to cite customer-specific rules is part of Phase 06.
- **Google Stitch Integration**: Prompt generation currently uses verified finding templates; live API connectivity to Google Stitch will be introduced in future integration phases.

---

## 4. Local Development vs. Production Infrastructure

- **Object Storage**: Local development operates against MinIO; production deployments require Amazon S3 with IAM role-based authentication and signed URL policies.
- **Authentication**: Local development uses the self-contained JWT development adapter; production requires Amazon Cognito User Pools with OIDC token validation.
