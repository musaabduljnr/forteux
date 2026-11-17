# Phase 07 User-Flow Analysis

## Overview

Multi-screen user-flow analysis applies eight structured reasoning dimensions to evaluate how screens work together as a cohesive experience. This goes beyond identifying per-screen defects to find problems that only emerge across the full journey.

---

## Eight Cross-Screen Reasoning Dimensions

### 1. Navigation Consistency
Does the navigation structure remain stable across screens? The model evaluates whether primary navigation items, their positions, and their visual treatment stay consistent. Changes without user intent (e.g. a hamburger menu on screen 2 that expands into a full sidebar on screen 4) are flagged.

### 2. Visual Continuity
Do screens feel like they belong to the same product? This includes typography, colour palette, component style, spacing rhythm, and iconography. Screens that look visually disconnected break trust and imply inconsistent development.

### 3. Component Consistency
Are the same UI patterns used for the same interactions across screens? A primary button that changes shape, size, or colour across screens — without intent — indicates a design system gap.

### 4. Information Continuity
Does information entered or selected on one screen correctly carry through to later screens? Missing confirmations, lost form data, or unacknowledged user choices are flagged as information continuity failures.

### 5. Repeated Effort
Does the user have to re-enter or re-confirm the same information at multiple points in the journey? Repeated effort is a usability failure that should be identified and reduced.

### 6. Missing Steps
Are there abrupt transitions between screens with no visible state to explain the jump? Missing loading states, confirmation pages, or intermediate feedback screens leave users disoriented.

### 7. Progressive Disclosure
Is complexity introduced gradually and appropriately across the journey? Screens that present too much too early, or too little at critical decision points, violate progressive disclosure principles.

### 8. Overall Experience
Does the journey feel coherent, well-paced, and purposeful? This meta-dimension synthesises the above seven into a holistic assessment.

---

## Finding Scopes

```
scope = "screen_level"   → Issue found on a single screen
scope = "cross_screen"   → Issue that spans two or more screens
```

Cross-screen findings include an `affected_screen_ids` list identifying which screens are involved. The UI uses this list to render screen-jump chips that navigate directly to the referenced screen.

---

## Evidence Calibration

The AI model is instructed to:
1. Base findings on **visual evidence only** — what is observable in the screenshots.
2. Distinguish clearly between screen-level and cross-screen evidence.
3. Cite the specific screen number(s) supporting each finding.
4. Not assume interactions, hover states, or animations that cannot be observed statically.

---

## Deduplication

When a screen-level issue on Screen 2 and a cross-screen issue both concern the same visual element, they are reported as separate findings with different scopes. The frontend's finding tabs (Screen Issues / Cross-Screen Issues) prevent visual confusion.

---

## Journey Report Structure

```
JourneyReport {
  journey_summary: str         # 2–3 sentence overview
  apparent_flow_structure: str # What journey structure was observed
  overall_assessment: str      # Holistic evaluation
  strengths: list[JourneyStrength]      # What works well
  major_friction_points: list[FrictionPoint]  # Key failures
  recommended_improvements: list[str]   # Ordered action items
  limitations: str             # Static screenshot analysis boundaries
}
```

This report is stored as `flow_report_json` on `AnalysisJob` and surfaced via `GET /flow-report`.
