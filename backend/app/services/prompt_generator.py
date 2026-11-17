import json
from typing import TYPE_CHECKING, Any
from app.db.models import Audit, AuditScreen, Finding, ScreenAsset

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

    def generate_multi_screen_prompt(
        self,
        audit: Audit,
        screens: list[tuple[AuditScreen, ScreenAsset | None]],
        selected_findings: list[Finding],
        journey_report: dict[str, Any] | None = None,
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
        audit_context: dict[str, Any] = {}
        if getattr(audit, "context_json", None):
            try:
                audit_context = json.loads(audit.context_json)
            except Exception:
                pass

        product_name = audit_context.get("product") or audit.name or "User Journey"
        journey_name = audit_context.get("journey_name") or audit.name or "Primary Workflow"
        goal = audit_context.get("objective") or audit_context.get("goal") or "End-to-end task completion"
        audience = audit_context.get("intended_user") or audit_context.get("audience") or "Application users"
        start_point = audit_context.get("start_point") or "Initial entry screen"
        end_state = audit_context.get("end_state") or "Final confirmation state"

        # Separate findings by scope
        screen_findings = [f for f in sorted_findings if getattr(f, "scope", "screen_level") == "screen_level"]
        cross_findings = [f for f in sorted_findings if getattr(f, "scope", "screen_level") == "cross_screen"]

        # Map screen IDs to labels
        screen_map: dict[str, str] = {}
        screen_sequence_lines: list[str] = []
        for idx, (audit_scr, asset) in enumerate(screens, 1):
            s_id = str(audit_scr.id)
            label = audit_scr.screen_label or f"Screen {idx}"
            screen_map[s_id] = label
            dim_str = f" ({asset.width_px}x{asset.height_px}px)" if asset and asset.width_px and asset.height_px else ""
            desc = f" — {audit_scr.screen_description}" if audit_scr.screen_description else ""
            screen_sequence_lines.append(f"{idx}. **{label}**{dim_str}{desc}")

        sections = []

        # 1. Role & Multi-Screen Objective
        sections.append(
            f"# Google Stitch Multi-Screen Redesign Brief: {journey_name} ({product_name})\n\n"
            f"## 1. Role & Objective\n"
            f"You are a Principal Product Designer, Flow Architect, and Google Stitch prompt engineer. "
            f"Your task is to redesign the complete {len(screens)}-screen user journey to eliminate the "
            f"{len(sorted_findings)} selected usability, cross-screen consistency, and visual hierarchy issues. "
            f"Treat all {len(screens)} uploaded screenshots as connected steps of ONE cohesive product experience."
        )

        # 2. Product & Journey Context
        sections.append(
            f"## 2. Product & User Journey Context\n"
            f"- **Product / Ecosystem**: {product_name}\n"
            f"- **Workflow Name**: {journey_name}\n"
            f"- **Target User**: {audience}\n"
            f"- **Journey Objective**: {goal}\n"
            f"- **Entry Point**: {start_point}\n"
            f"- **Intended Completion**: {end_state}"
        )

        # 3. Screen Sequence Overview
        sections.append(
            f"## 3. Screen Sequence Overview\n"
            f"The journey consists of the following {len(screens)} screens in explicit chronological order:\n"
            + "\n".join(screen_sequence_lines)
        )

        # 4. Cross-Screen Continuity & Navigation Issues
        if cross_findings:
            cross_blocks = []
            for idx, finding in enumerate(cross_findings, 1):
                affected_ids = []
                try:
                    affected_ids = json.loads(finding.affected_screen_ids_json) if isinstance(finding.affected_screen_ids_json, str) else (finding.affected_screen_ids_json or [])
                except Exception:
                    pass
                affected_labels = [screen_map.get(s_id, f"Screen ({s_id[:8]})") for s_id in affected_ids]
                affected_str = ", ".join(affected_labels) if affected_labels else "Entire sequence"

                cross_blocks.append(
                    f"### Cross-Screen Issue {idx}: {finding.title} [{finding.severity.upper()}]\n"
                    f"- **Category**: {finding.category.replace('_', ' ').title()}\n"
                    f"- **Affected Screens**: {affected_str}\n"
                    f"- **Cross-Screen Inconsistency**: {finding.description}\n"
                    f"- **Visual Comparison**: {finding.evidence}\n"
                    f"- **Why It Matters**: {finding.why_it_matters}\n"
                    f"- **Required Cohesive Fix**: {finding.recommended_fix}\n"
                    f"- **Design Principle**: {finding.design_principle or 'Cross-Screen Cohesion'}"
                )
            sections.append(
                f"## 4. Cross-Screen Continuity & Consistency Fixes\n"
                f"Address these flow-level discrepancies across the relevant screens:\n\n"
                + "\n\n".join(cross_blocks)
            )

        # 5. Screen-Level Usability & Visual Fixes
        if screen_findings:
            scr_blocks = []
            for idx, finding in enumerate(screen_findings, 1):
                # Map location
                locations = []
                try:
                    boxes = json.loads(finding.bounding_boxes_json) if isinstance(finding.bounding_boxes_json, str) else finding.bounding_boxes_json
                    if isinstance(boxes, list) and boxes:
                        for b in boxes:
                            scr_label = screen_map.get(b.get("screen_id", ""), "")
                            loc = describe_region(b)
                            locations.append(f"{scr_label}: {loc}" if scr_label else loc)
                except Exception:
                    pass
                loc_str = "; ".join(locations) if locations else "Specific screen interface region"

                scr_blocks.append(
                    f"### Screen Issue {idx}: {finding.title} [{finding.severity.upper()}]\n"
                    f"- **Target Area**: {loc_str}\n"
                    f"- **Existing Problem**: {finding.description}\n"
                    f"- **Visual Evidence**: {finding.evidence}\n"
                    f"- **Why It Matters**: {finding.why_it_matters}\n"
                    f"- **Required Improvement**: {finding.recommended_fix}"
                )
            sections.append(
                f"## 5. Screen-Specific Usability & Visual Polish\n\n"
                + "\n\n".join(scr_blocks)
            )

        # 6. Overall Journey Assessment & High-Level Directives
        if journey_report and isinstance(journey_report, dict):
            summary = journey_report.get("journey_summary", "")
            assessment = journey_report.get("overall_assessment", "")
            improvements = journey_report.get("recommended_improvements", [])
            imp_lines = "\n".join(f"- {imp}" for imp in improvements) if improvements else "- Unify visual patterns across all screens."
            sections.append(
                f"## 6. Flow Cohesion & Journey Guidelines\n"
                f"- **Flow Assessment**: {assessment or summary}\n"
                f"- **Global Flow Recommendations**:\n{imp_lines}"
            )

        # 7. Navigation & Progression Architecture
        sections.append(
            f"## 7. Navigation & Progression Architecture\n"
            f"- **Predictable Action Anchoring**: Primary progression actions ('Continue', 'Submit', 'Next') must occupy a consistent location across every screen.\n"
            f"- **Clear Backward Navigation**: Provide unambiguous back affordances allowing users to review earlier selections without state disruption.\n"
            f"- **Progress Visibility**: Include clear step indicators or contextual breadcrumbs to reassure users of their position in the flow.\n"
            f"- **No Dead Ends**: Every screen must provide an obvious forward path or clear escape/cancel action."
        )

        # 8. User-Specified Design Instructions (if provided)
        if user_instructions and user_instructions.strip():
            sections.append(
                f"## 8. User-Specified Design Instructions\n"
                f"Incorporate these explicit design preferences across all redesigned screens:\n"
                f"{user_instructions.strip()}"
            )

        # 9. Applied Design References (Knowledge Library grounding)
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
                "## 9. Applied Design References (Knowledge Base)\n"
                "Align all redesigned screens with these authoritative design guidelines:\n"
                + "\n".join(ref_items)
            )

        # 10. Strict Multi-Screen Constraints
        sections.append(
            f"## 10. Strict Multi-Screen Design Constraints\n"
            f"- **Cohesive Multi-Screen Redesign**: Do not fix one screen in isolation if the solution produces visual or navigation discrepancies with adjacent screens.\n"
            f"- **Preserve Flow Logic**: Maintain the established step sequence and business logic ({start_point} to {end_state}).\n"
            f"- **No Arbitrary Feature Injection**: Do not introduce unrequested intermediate modals, marketing banners, or features not in the flow.\n"
            f"- **Consistent UI Tokens**: Maintain uniform button heights, corner radii, typography scales, and color values across every screen in the journey."
        )

        # 11. Expected Multi-Screen Output & Google Stitch Handoff
        sections.append(
            f"## 11. Expected Multi-Screen Output for Google Stitch\n"
            f"Generate an aligned, multi-screen redesign spanning all {len(screens)} screens with complete cross-screen consistency.\n\n"
            f"> **Critical Handoff Instructions for Google Stitch**:\n"
            f"> 1. Provide ALL {len(screens)} original screenshots to Google Stitch in the defined sequence order.\n"
            f"> 2. Instruct Stitch to evaluate and redesign the screenshots as a linked multi-screen flow.\n"
            f"> 3. Paste this complete brief into Stitch's prompt window to guide the generative redesign.\n"
            f"> 4. Verify that component styles, colors, and button placements remain uniform across all generated screens."
        )

        return "\n\n".join(sections)

    def generate_design_system_refinement_prompt(
        self,
        audit_name: str,
        screen_count: int,
        consistency_score: float | None,
        colors: list[dict[str, Any]],
        typography: list[dict[str, Any]],
        spacing_layout: dict[str, Any],
        shapes_surfaces: dict[str, Any],
        components: list[dict[str, Any]],
        tokens: list[dict[str, Any]],
        consistency_issues: list[dict[str, Any]],
        recommendations: list[str],
        user_instructions: str | None = None,
        retrieved_knowledge: list["RetrievedChunk"] | None = None,
    ) -> str:
        """
        Generate a comprehensive Google Stitch Design System Refinement Prompt.
        Standardizes typography, spacing, colors, and reusable components across screens
        while strictly preserving product identity and information architecture.
        """
        score_display = f"{consistency_score}/100" if consistency_score is not None else "Pending"
        sections: list[str] = []

        # 1. Executive Directive
        sections.append(
            f"# Google Stitch Design System Refinement Brief: {audit_name}\n\n"
            f"**Audit Context**: Design system extraction & cross-screen harmonization across {screen_count} screens.\n"
            f"**Current Consistency Score**: {score_display}\n\n"
            f"You are a Principal Product Designer refining and standardizing the UI design system of this application. "
            f"Your objective is to establish a rigorous, uniform visual language across all screens while strictly "
            f"preserving the brand identity, product layout, and user mental model."
        )

        # 2. Design System Core Principles
        sections.append(
            "## 1. Core Directives for Google Stitch\n"
            "- **Preserve Product Identity**: Do not re-brand or introduce arbitrary aesthetic pivots. Elevate and align the existing visual language.\n"
            "- **Standardize Reusable Components**: Apply identical button heights, text input styles, card borders, and tab bars across all screens.\n"
            "- **Strict Token Uniformity**: Replace rogue, one-off colors and font sizes with the exact design tokens specified below.\n"
            "- **Maintain Information Architecture**: Do not rearrange page layouts, user navigation, or core content hierarchy.\n"
            "- **Evidence-Based Fidelity**: Verified tokens must be strictly implemented; approximate tokens provide baseline targets."
        )

        # 3. Color Tokens & Foundations
        color_lines = []
        for c in colors[:10]:
            name = c.get("semantic_name", c.get("category", "Color"))
            hex_val = c.get("hex", "#000000")
            cat = c.get("category", "general")
            ev = c.get("evidence", "observed")
            conf = int(c.get("confidence", 0.9) * 100)
            color_lines.append(f"- **{name}** (`{hex_val}`) — *{cat.capitalize()}* [{ev}, {conf}% conf]")
        if color_lines:
            sections.append(
                "## 2. Color Palette & Token System\n"
                "Unify all UI elements to the following measured color tokens:\n"
                + "\n".join(color_lines)
            )

        # 4. Typography Scale
        type_lines = []
        for t in typography[:8]:
            style = t.get("style_name", "typography.style")
            size = t.get("font_size_approx", "14px")
            weight = t.get("font_weight_category", "regular")
            hier = t.get("text_hierarchy", "body")
            type_lines.append(f"- **{style}**: `{size}`, weight: `{weight}` (hierarchy: *{hier}*)")
        if type_lines:
            sections.append(
                "## 3. Typography Hierarchy\n"
                "Standardize all headings, body text, and labels across all screens to this scale:\n"
                + "\n".join(type_lines)
            )

        # 5. Spacing, Shapes & Surfaces
        surface_items = []
        radii = shapes_surfaces.get("border_radii", [])
        if radii:
            surface_items.append(f"- **Border Radii**: Standardize to {', '.join(radii)} across cards, buttons, and inputs.")
        if shapes_surfaces.get("borders"):
            surface_items.append(f"- **Borders & Dividers**: {shapes_surfaces['borders']}")
        if spacing_layout.get("card_padding"):
            surface_items.append(f"- **Card Padding**: {spacing_layout['card_padding']}")
        if spacing_layout.get("component_gaps"):
            surface_items.append(f"- **Component Gaps**: {spacing_layout['component_gaps']}")
        if surface_items:
            sections.append(
                "## 4. Spacing, Shapes & Surface Treatments\n"
                + "\n".join(surface_items)
            )

        # 6. Reusable Component Specifications
        comp_lines = []
        for comp in components[:8]:
            cat = comp.get("component_category", "Component")
            spec = comp.get("recommended_component_spec", comp.get("visual_description", ""))
            vars_list = comp.get("variations", [])
            var_note = f" (Resolve variations: {'; '.join(vars_list)})" if vars_list else ""
            comp_lines.append(f"- **{cat}**: {spec}{var_note}")
        if comp_lines:
            sections.append(
                "## 5. Reusable Component Standards\n"
                "Consolidate all button, input, and card instances into these canonical component patterns:\n"
                + "\n".join(comp_lines)
            )

        # 7. Cross-Screen Visual Inconsistencies to Resolve
        if consistency_issues:
            issue_lines = []
            for idx, issue in enumerate(consistency_issues[:10], start=1):
                sev = issue.get("severity", "medium").upper()
                title = issue.get("title", "")
                desc = issue.get("description", "")
                fix = issue.get("recommended_fix", "")
                screens = issue.get("affected_screens", [])
                scr_str = f" [Screens: {', '.join(str(s) for s in screens)}]" if screens else ""
                issue_lines.append(f"{idx}. **[{sev}] {title}**{scr_str}\n   - *Problem*: {desc}\n   - *Required Fix*: {fix}")
            sections.append(
                "## 6. Targeted Cross-Screen Inconsistencies to Resolve\n"
                "Specifically correct the following visual drift between screens:\n\n"
                + "\n\n".join(issue_lines)
            )

        # 8. User Custom Instructions
        if user_instructions and user_instructions.strip():
            sections.append(
                "## 7. Additional User Design Directives\n"
                f"{user_instructions.strip()}"
            )

        # 9. Knowledge Library Reference Citations (if present)
        if retrieved_knowledge:
            ref_items = []
            for chunk in retrieved_knowledge[:4]:
                heading_info = f" ({chunk.section_heading})" if chunk.section_heading else ""
                clean_text = chunk.text.replace("\n", " ").strip()
                if len(clean_text) > 180:
                    clean_text = clean_text[:177] + "..."
                ref_items.append(f"- **{chunk.document_name}**{heading_info}: \"{clean_text}\"")
            sections.append(
                "## 8. Applied Brand & Design Standards (Knowledge Base)\n"
                + "\n".join(ref_items)
            )

        # 10. Recommended Action Plan
        if recommendations:
            rec_items = [f"{i}. {r}" for i, r in enumerate(recommendations[:6], start=1)]
            sections.append(
                "## 9. Design System Harmonization Action Plan\n"
                + "\n".join(rec_items)
            )

        # 11. Handoff Instructions for Google Stitch
        sections.append(
            f"## 10. Google Stitch Handoff & Generation Protocol\n"
            f"> **Handoff Procedure**:\n"
            f"> 1. Upload all {screen_count} original screenshots to Google Stitch in sequence.\n"
            f"> 2. Paste this complete Design System Refinement Brief into the Stitch generation window.\n"
            f"> 3. Instruct Stitch to generate the redesigned screens as a unified, token-harmonized set.\n"
            f"> 4. Verify that primary buttons, typography hierarchy, card radiuses, and spacing are 100% consistent across all outputs."
        )

        return "\n\n".join(sections)


