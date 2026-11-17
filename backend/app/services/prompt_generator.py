import json
from typing import TYPE_CHECKING, Any
from app.db.models import Audit, Finding, ScreenAsset

if TYPE_CHECKING:
    from app.services.knowledge_retrieval import RetrievedChunk


def describe_region(box: dict[str, Any]) -> str:
    """Translate normalized coordinates into an intuitive layout region description."""
    x = box.get("x", 0.0)
    y = box.get("y", 0.0)
    w = box.get("width", 0.0)
    h = box.get("height", 0.0)

    # Vertical descriptor
    if y < 0.20:
        vert = "Top"
    elif y < 0.65:
        vert = "Mid"
    else:
        vert = "Bottom"

    # Horizontal descriptor
    if x < 0.30:
        horiz = "Left"
    elif x < 0.65:
        horiz = "Center"
    else:
        horiz = "Right"

    pct_x = int(round(x * 100))
    pct_y = int(round(y * 100))
    pct_w = int(round(w * 100))
    pct_h = int(round(h * 100))

    return f"{vert}-{horiz} section (approx. x: {pct_x}%, y: {pct_y}%, width: {pct_w}%, height: {pct_h}%)"


class StitchPromptGenerator:
    """
    Generates structured, professional Google Stitch redesign briefs
    grounded in verified audit findings, screenshot geometry, and user instructions.
    """

    def generate_prompt(
        self,
        audit: Audit,
        screen: ScreenAsset | None,
        selected_findings: list[Finding],
        user_instructions: str | None = None,
        retrieved_knowledge: list["RetrievedChunk"] | None = None,
    ) -> str:
        if not selected_findings:
            raise ValueError("Cannot generate Google Stitch prompt with zero selected findings.")

        # Severity ranking for prioritization
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            selected_findings,
            key=lambda f: severity_order.get(f.severity.lower(), 4),
        )

        # Context extraction
        audit_context = {}
        if getattr(audit, "context_json", None):
            try:
                audit_context = json.loads(audit.context_json)
            except Exception:
                pass
        product_name = audit_context.get("product") or audit.name or "User Interface"
        goal = audit_context.get("goal") or "Primary user workflow"
        audience = audit_context.get("audience") or "Target application users"
        constraints = audit_context.get("constraints") or "Preserve existing brand assets and layout foundation"

        # Screen dimensions and orientation
        screen_desc = "Standard interface layout"
        if screen and screen.width_px and screen.height_px:
            aspect = screen.width_px / max(1, screen.height_px)
            device_type = "mobile viewport" if aspect < 0.65 else "desktop viewport" if aspect > 1.3 else "tablet/standard viewport"
            screen_desc = f"{device_type} ({screen.width_px}x{screen.height_px}px, aspect ratio {aspect:.2f})"

        # Collect unique design objectives based on selected finding categories
        category_objectives = {
            "visual_hierarchy": "Establish a clear visual hierarchy with distinct visual weight for primary versus secondary actions.",
            "layout_spacing": "Harmonize spacing and padding using a consistent layout grid to resolve visual crowding.",
            "typography": "Strengthen typographic contrast and modular scale differentiation between headings, labels, and body text.",
            "color_contrast": "Ensure sufficient visual contrast and legibility across all text labels and microcopy.",
            "components_consistency": "Standardize component styling, border radii, and interaction states for buttons and form elements.",
            "usability": "Clarify action affordances and reduce decision friction across interactive controls.",
            "accessibility_indicator": "Improve perceptual clarity, text size readability, and non-color-dependent status indicators.",
        }

        included_categories = {f.category for f in sorted_findings}
        objectives_list = [category_objectives[cat] for cat in included_categories if cat in category_objectives]
        if not objectives_list:
            objectives_list.append("Refine visual hierarchy and component consistency across the interface.")

        # Build prompt sections
        sections = []

        # 1. Role and Objective
        sections.append(
            f"# Google Stitch Redesign Brief: {product_name}\n\n"
            f"## 1. Role & Objective\n"
            f"You are an experienced Principal UI/UX Designer, Design Systems Specialist, and Google Stitch prompt engineer. "
            f"Your objective is to generate an improved, production-ready interface design that directly addresses "
            f"the {len(sorted_findings)} selected usability and visual design findings identified from the uploaded screenshot. "
            f"Reference the uploaded interface screenshot as the baseline visual canvas."
        )

        # 2. Existing Interface Context
        sections.append(
            f"## 2. Existing Interface Context\n"
            f"- **Product / Surface**: {product_name}\n"
            f"- **User Goal**: {goal}\n"
            f"- **Target Audience**: {audience}\n"
            f"- **Captured Screen Geometry**: {screen_desc}\n"
            f"- **Baseline Visual Characteristics**: Use the provided screenshot as the authoritative source for the existing "
            f"layout structure, recognizable color accents, navigation scheme, and content taxonomy. Do not invent arbitrary "
            f"rebranding; preserve the identifiable product character while solving the specific defects below."
        )

        # 3. Design Objectives
        obj_text = "\n".join(f"- {obj}" for obj in objectives_list)
        sections.append(
            f"## 3. Core Design Objectives\n"
            f"Focus the redesign on these required improvements:\n"
            f"{obj_text}"
        )

        # 4. Selected Issues and Required Improvements
        issues_blocks = []
        for idx, finding in enumerate(sorted_findings, 1):
            # Parse bounding boxes
            locations = []
            try:
                boxes = json.loads(finding.bounding_boxes_json) if isinstance(finding.bounding_boxes_json, str) else finding.bounding_boxes_json
                if isinstance(boxes, list) and boxes:
                    for b in boxes:
                        locations.append(describe_region(b))
            except Exception:
                pass

            location_str = "; ".join(locations) if locations else "Screen-level interface component"

            issue_item = (
                f"### Issue {idx}: {finding.title} [{finding.severity.upper()}]\n"
                f"- **Category**: {finding.category.replace('_', ' ').title()}\n"
                f"- **Location**: {location_str}\n"
                f"- **Existing Problem**: {finding.description}\n"
                f"- **Visual Evidence**: {finding.evidence}\n"
                f"- **Why It Matters**: {finding.why_it_matters}\n"
                f"- **Required Improvement**: {finding.recommended_fix}\n"
                f"- **Design Principle**: {finding.design_principle or 'Usability & Visual Standards'}"
            )
            issues_blocks.append(issue_item)

        sections.append(
            f"## 4. Prioritized Issues & Required Design Solutions\n\n"
            + "\n\n".join(issues_blocks)
        )

        # 5. Visual Design Requirements
        sections.append(
            f"## 5. Visual Design Requirements\n"
            f"- **Layout & Spacing**: Use an 8pt/4pt harmonic grid. Ensure comfortable breathing room around interactive elements.\n"
            f"- **Typography Scale**: Maintain clear visual differentiation between section headings and body text (minimum 1.33x scale ratio). "
            f"Ensure microcopy remains crisp and legible.\n"
            f"- **Components & Buttons**: Primary calls-to-action must have distinct visual weight (solid filled background with high luminance contrast). "
            f"Secondary actions should use outline or ghost styles. Align corner radii consistently across buttons and cards.\n"
            f"- **Perceptual Contrast**: Ensure all text, icons, and status indicators are easily distinguishable from their backing surfaces.\n"
            f"- **Visual Economy**: Remove visual clutter, heavy borders, and unnecessary decorative elements that compete with primary user tasks."
        )

        # 6. User-Provided Design Preferences (if supplied)
        if user_instructions and user_instructions.strip():
            sections.append(
                f"## 6. User-Specified Design Instructions\n"
                f"In addition to resolving the audit findings above, incorporate these explicit user preferences:\n"
                f"{user_instructions.strip()}"
            )

        # 7. Applied Design References (Knowledge Library grounding)
        if retrieved_knowledge:
            ref_items = []
            for chunk in retrieved_knowledge[:5]:
                page_info = f", Page {chunk.page_start}" if chunk.page_start else ""
                heading_info = f" ({chunk.section_heading})" if chunk.section_heading else ""
                clean_text = chunk.text.replace("\n", " ").strip()
                if len(clean_text) > 200:
                    clean_text = clean_text[:197] + "..."
                ref_items.append(
                    f"- **{chunk.document_name}**{heading_info}{page_info}:\n"
                    f'  > "{clean_text}"'
                )
            sections.append(
                "## Applied Design References (Knowledge Base)\n"
                "Align the redesign with these authoritative organizational design standards:\n"
                + "\n".join(ref_items)
            )

        # Constraints & Boundary Rules
        sections.append(
            f"## Strict Design Constraints\n"
            f"- **Preserve Product Purpose**: Do not alter the fundamental purpose or core business logic of the interface.\n"
            f"- **Retain Essential Content**: Do not remove functional labels, navigation links, or data columns unless explicitly required.\n"
            f"- **No Speculative Features**: Do not invent new features, tabs, or workflows not visible in the screenshot.\n"
            f"- **Avoid Unrelated Churn**: Do not redesign unrelated interface components that have no audit findings unless necessary to maintain visual consistency.\n"
            f"- **Preserve Constraints**: {constraints}."
        )

        # Expected Output & Google Stitch Handoff
        sections.append(
            f"## Expected Output for Google Stitch\n"
            f"Generate a polished, production-ready interface that completely resolves the listed design issues while respecting all constraints.\n\n"
            f"> **Handoff Note for Google Stitch**:\n"
            f"> 1. Provide the original screenshot to Google Stitch as visual input.\n"
            f"> 2. Paste this complete brief into Stitch's prompt window to guide the generative redesign.\n"
            f"> 3. Export the resulting UI to Figma for final design system token alignment."
        )

        return "\n\n".join(sections)
