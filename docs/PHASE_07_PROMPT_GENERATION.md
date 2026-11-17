# Phase 07 Multi-Screen Stitch Prompt Generation

## Overview

The Phase 07 Stitch prompt generator produces a comprehensive, 11-section design brief that covers the complete user journey. It extends the Phase 05 single-screen prompt format to address multiple screens simultaneously and instructs Google Stitch on how to upload and reference all original screenshots.

---

## Trigger

The existing `POST /projects/{project_id}/audits/{audit_id}/prompt` endpoint checks `audit.mode`:
- `mode == "single"` → delegates to `generate_stitch_prompt()` (Phase 05)
- `mode == "multi"` → delegates to `generate_multi_screen_prompt()` (Phase 07)

The Phase 05 prompt versioning system (create, restore original, version history) applies to both.

---

## 11-Section Brief Structure

### Section 1: Context
```
PROJECT: {audit_name}
SCREENS: {n} screens representing the user journey
USER INSTRUCTIONS: {custom instructions if provided}
```

### Section 2: Journey Overview
High-level description of the apparent flow structure and the screens included. References the AI-generated `journey_summary` from the `JourneyReport`.

### Section 3: Selected Issues to Address
Numbered list of all selected findings (from `selected_finding_ids`), each including:
- Severity badge
- Title
- Description
- Recommended fix
- Scope (screen-level or cross-screen)
- Affected screen references

### Section 4: Cross-Screen Patterns
Dedicated section summarising cross-screen findings — navigation consistency, component consistency, information continuity, repeated effort, missing steps.

### Section 5: Per-Screen Improvement Directives
One sub-section per screen, listing only the findings that affect that screen. Cross-screen findings that touch the screen are included with a note linking back to the full cross-screen pattern.

### Section 6: Design System Requirements
If findings indicate design system inconsistencies (colour, typography, component variants), this section describes the target unified system.

### Section 7: Flow-Level Recommendations
The `recommended_improvements` list from `JourneyReport` — ordered actions to improve the journey as a whole.

### Section 8: Knowledge Library Citations
If RAG citations were used during the analysis, this section includes the referenced sources and the relevant guidance they provided.

### Section 9: Preservation Directives
Explicit instructions on what NOT to change — elements identified as strengths in the `JourneyReport`.

### Section 10: Stitch Generation Instructions
Specific instructions for how to use the brief in Google Stitch:
- Generate each screen separately.
- Maintain consistent design tokens across all generations.
- Use the same component library and spacing system for all screens.
- Apply cross-screen fixes globally (e.g. if nav changes, change it on all screens).

### Section 11: Screenshot Handoff
```
HANDOFF: Provide all {n} original screenshots to Google Stitch in sequence order
before pasting this prompt. Upload them in the following order:
  Screen 1: {label} — {description}
  Screen 2: {label} — {description}
  ...
```

---

## Prompt Length and Editability

The generated prompt is returned as a plain text string in the `PromptVersion.content` field. The UI renders it in an editable `<textarea>` for user modification before copying.

The `userInstructions` parameter (optional free text from the UI) is injected into Section 1 and influences finding prioritisation in Section 3.

---

## Prompt Version Persistence

Multi-screen prompts use the same `PromptVersion` model as single-screen prompts. The Phase 05 restore-original and version history features work identically for multi-screen audits.
