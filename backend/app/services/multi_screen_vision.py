import logging
import re
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("forteux.ai.multi_screen")


class MultiScreenBoundingBox(BaseModel):
    screen_id: str
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @field_validator("x", "y", "width", "height", mode="before")
    @classmethod
    def round_coord(cls, v: Any) -> float:
        val = float(v)
        return max(0.0, min(1.0, round(val, 4)))

    @field_validator("width")
    @classmethod
    def clamp_width(cls, v: float, info: Any) -> float:
        x = info.data.get("x", 0.0)
        if x + v > 1.0:
            return round(max(0.01, 1.0 - x), 4)
        return v

    @field_validator("height")
    @classmethod
    def clamp_height(cls, v: float, info: Any) -> float:
        y = info.data.get("y", 0.0)
        if y + v > 1.0:
            return round(max(0.01, 1.0 - y), 4)
        return v


class ScreenContext(BaseModel):
    screen_id: str
    screen_label: str
    sequence_index: int
    width_px: int
    height_px: int
    description: str | None = None


class MultiScreenFinding(BaseModel):
    id: str = Field(default_factory=lambda: f"mf-{uuid4().hex[:8]}")
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(min_length=2, max_length=64)
    description: str = Field(min_length=5)
    severity: Literal["critical", "high", "medium", "low"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_type: Literal["observed", "inferred"]
    evidence: str = Field(min_length=3)
    why_it_matters: str = Field(min_length=5)
    recommended_fix: str = Field(min_length=5)
    design_principle: str | None = None
    bounding_boxes: list[MultiScreenBoundingBox] = Field(default_factory=list)
    limitations: str | None = None
    scope: Literal["screen_level", "cross_screen"] = "screen_level"
    affected_screen_ids: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", v.strip().lower())
        allowed = {
            "visual_hierarchy",
            "layout_spacing",
            "typography",
            "color_contrast",
            "components_consistency",
            "usability",
            "accessibility_indicator",
            "journey_continuity",
            "navigation_consistency",
            "information_continuity",
            "repeated_effort",
            "progressive_disclosure",
        }
        return cleaned if cleaned in allowed else "usability"


class JourneyStrength(BaseModel):
    title: str
    description: str


class FrictionPoint(BaseModel):
    title: str
    description: str
    affected_screens: list[str] = Field(default_factory=list)
    severity: Literal["critical", "high", "medium", "low"] = "medium"


class JourneyReport(BaseModel):
    journey_summary: str
    apparent_structure: str
    overall_assessment: str
    strengths: list[JourneyStrength]
    major_friction_points: list[FrictionPoint]
    recommended_improvements: list[str]
    limitations: str


class MultiScreenAnalysisResult(BaseModel):
    journey_report: JourneyReport
    screen_level_findings: list[MultiScreenFinding]
    cross_screen_findings: list[MultiScreenFinding]
    provider: str
    model: str


class MultiScreenVisionProvider:
    def analyze_flow(
        self,
        screens: list[tuple[bytes, str, ScreenContext]],
        journey_context: dict[str, Any] | None = None,
    ) -> MultiScreenAnalysisResult:
        raise NotImplementedError


class DeterministicMultiScreenProvider(MultiScreenVisionProvider):
    """Deterministic multi-screen flow evaluation engine for reproducible local execution and tests."""

    def analyze_flow(
        self,
        screens: list[tuple[bytes, str, ScreenContext]],
        journey_context: dict[str, Any] | None = None,
    ) -> MultiScreenAnalysisResult:
        if not screens:
            raise ValueError("Cannot perform multi-screen analysis on empty screen sequence")

        ctx = journey_context or {}
        journey_name = ctx.get("journey_name") or ctx.get("goal") or "User Journey"
        product_name = ctx.get("product") or "Product Workflow"

        screen_level_findings: list[MultiScreenFinding] = []
        cross_screen_findings: list[MultiScreenFinding] = []
        seen_titles: set[str] = set()

        aspect_ratios = []

        # 1. Screen-level analysis for each screen
        for _, mime_type, screen_ctx in screens:
            w = max(1, screen_ctx.width_px)
            h = max(1, screen_ctx.height_px)
            aspect = w / h
            aspect_ratios.append(aspect)

            # Aspect-specific screen-level finding
            if aspect < 0.65:
                f_title = f"Touch Target Clearance on {screen_ctx.screen_label or f'Screen {screen_ctx.sequence_index + 1}'}"
                if f_title not in seen_titles:
                    seen_titles.add(f_title)
                    screen_level_findings.append(
                        MultiScreenFinding(
                            id=f"mf-scr-{screen_ctx.sequence_index}-cta",
                            title=f_title,
                            category="usability",
                            description="Interactive actions near the bottom edge risk conflicting with operating system navigation gestures.",
                            severity="medium",
                            confidence=0.86,
                            evidence_type="observed",
                            evidence=f"Mobile aspect ratio ({w}x{h}px) with lower actionable elements.",
                            why_it_matters="Bottom controls without adequate safe area clearance cause accidental touch failures.",
                            recommended_fix="Provide at least 24px safe padding and ensure a minimum 48x48px touch target area.",
                            design_principle="Fitts's Law & Safe Area Clearance",
                            bounding_boxes=[
                                MultiScreenBoundingBox(screen_id=screen_ctx.screen_id, x=0.08, y=0.86, width=0.84, height=0.10)
                            ],
                            limitations="Touch targets assessed visually from static screenshot dimensions.",
                            scope="screen_level",
                            affected_screen_ids=[screen_ctx.screen_id],
                        )
                    )
            else:
                f_title = f"Visual Hierarchy and Primary Action on {screen_ctx.screen_label or f'Screen {screen_ctx.sequence_index + 1}'}"
                if f_title not in seen_titles:
                    seen_titles.add(f_title)
                    screen_level_findings.append(
                        MultiScreenFinding(
                            id=f"mf-scr-{screen_ctx.sequence_index}-hier",
                            title=f_title,
                            category="visual_hierarchy",
                            description="Primary call-to-action button shares visual weight with secondary elements.",
                            severity="high",
                            confidence=0.84,
                            evidence_type="observed",
                            evidence=f"Wide aspect ratio ({w}x{h}px) layout with competing button treatments.",
                            why_it_matters="Ambiguous action priority increases decision latency across task steps.",
                            recommended_fix="Elevate primary action using strong brand accent fill and downgrade secondary controls.",
                            design_principle="Visual Hierarchy & Perceptual Contrast",
                            bounding_boxes=[
                                MultiScreenBoundingBox(screen_id=screen_ctx.screen_id, x=0.65, y=0.05, width=0.28, height=0.08)
                            ],
                            limitations="Static visual prominence analysis without hover/focus states.",
                            scope="screen_level",
                            affected_screen_ids=[screen_ctx.screen_id],
                        )
                    )

            # Common typography finding per screen
            f_typo = f"Typographic Contrast on {screen_ctx.screen_label or f'Screen {screen_ctx.sequence_index + 1}'}"
            if f_typo not in seen_titles:
                seen_titles.add(f_typo)
                screen_level_findings.append(
                    MultiScreenFinding(
                        id=f"mf-scr-{screen_ctx.sequence_index}-typo",
                        title=f_typo,
                        category="typography",
                        description="Supporting labels and descriptions lack clear modular scale separation from headings.",
                        severity="low",
                        confidence=0.80,
                        evidence_type="observed",
                        evidence="Small font size differences between section subheadings and paragraph body.",
                        why_it_matters="Weak typographic hierarchy hinders fast visual scanning.",
                        recommended_fix="Establish a distinct modular typographic scale with 1.33x ratio.",
                        design_principle="Typographic Scale & Legibility",
                        bounding_boxes=[
                            MultiScreenBoundingBox(screen_id=screen_ctx.screen_id, x=0.08, y=0.20, width=0.50, height=0.12)
                        ],
                        limitations="Exact font metrics require CSS inspection.",
                        scope="screen_level",
                        affected_screen_ids=[screen_ctx.screen_id],
                    )
                )

        # 2. Cross-screen flow analysis
        all_screen_ids = [s[2].screen_id for s in screens]

        # Cross-screen finding 1: Inconsistent Viewport / Responsive Assumptions
        min_aspect = min(aspect_ratios)
        max_aspect = max(aspect_ratios)
        if max_aspect - min_aspect > 0.3:
            cross_screen_findings.append(
                MultiScreenFinding(
                    id="mf-cross-viewport",
                    title="Inconsistent Viewport and Form Factor Across Journey Stages",
                    category="components_consistency",
                    description="The sequence mixes mobile and desktop/tablet viewport orientations, disrupting visual continuity between consecutive steps.",
                    severity="high",
                    confidence=0.92,
                    evidence_type="observed",
                    evidence=f"Aspect ratios vary from {min_aspect:.2f} to {max_aspect:.2f} across the sequence.",
                    why_it_matters="Disparate viewports suggest fragmented responsive design or mismatched cross-platform testing assets.",
                    recommended_fix="Standardize design deliverables to a uniform device viewport breakpoint across all flow stages.",
                    design_principle="Cross-Device Consistency",
                    bounding_boxes=[
                        MultiScreenBoundingBox(screen_id=s_id, x=0.05, y=0.02, width=0.90, height=0.08)
                        for s_id in all_screen_ids[:3]
                    ],
                    limitations="Evaluated from supplied screenshot resolutions.",
                    scope="cross_screen",
                    affected_screen_ids=all_screen_ids,
                )
            )

        # Cross-screen finding 2: Navigation Consistency and Progression
        first_ctx = screens[0][2]
        last_ctx = screens[-1][2]
        cross_screen_findings.append(
            MultiScreenFinding(
                id="mf-cross-navigation",
                title="Cross-Screen Primary Navigation and Progression Continuity",
                category="navigation_consistency",
                description="Progression indicators and primary action locations shift between early and later journey stages, requiring users to re-orient themselves at each step.",
                severity="medium",
                confidence=0.85,
                evidence_type="observed",
                evidence=f"Progression path from '{first_ctx.screen_label or 'Step 1'}' to '{last_ctx.screen_label or f'Step {len(screens)}'}' shows differing header and CTA alignments.",
                why_it_matters="Shifting navigation anchors increase cognitive load and friction as users advance through the workflow.",
                recommended_fix="Lock primary step progression controls to a predictable position (e.g. persistent bottom action bar or consistent top-right anchor).",
                design_principle="Spatial Consistency & Predictability",
                bounding_boxes=[
                    MultiScreenBoundingBox(screen_id=first_ctx.screen_id, x=0.60, y=0.05, width=0.35, height=0.08),
                    MultiScreenBoundingBox(screen_id=last_ctx.screen_id, x=0.10, y=0.88, width=0.80, height=0.08),
                ],
                limitations="Actual navigation transitions require interactive prototype verification.",
                scope="cross_screen",
                affected_screen_ids=[first_ctx.screen_id, last_ctx.screen_id],
            )
        )

        # Cross-screen finding 3: Component Styling Consistency (if 3 or more screens)
        if len(screens) >= 3:
            mid_ctx = screens[1][2]
            cross_screen_findings.append(
                MultiScreenFinding(
                    id="mf-cross-components",
                    title="Recurring Component Styling and Border Radius Discrepancies",
                    category="components_consistency",
                    description="Card containers, input fields, and button corner radii exhibit visual variation between intermediate journey screens.",
                    severity="medium",
                    confidence=0.81,
                    evidence_type="observed",
                    evidence=f"Comparing controls across {first_ctx.screen_label}, {mid_ctx.screen_label}, and {last_ctx.screen_label}.",
                    why_it_matters="Inconsistent component styling diminishes perceived product quality and design system maturity.",
                    recommended_fix="Unify UI token values: standardize card border-radius to 8px or 12px across all flow screens.",
                    design_principle="Design System Token Cohesion",
                    bounding_boxes=[
                        MultiScreenBoundingBox(screen_id=first_ctx.screen_id, x=0.10, y=0.30, width=0.80, height=0.20),
                        MultiScreenBoundingBox(screen_id=mid_ctx.screen_id, x=0.10, y=0.30, width=0.80, height=0.20),
                    ],
                    limitations="Component token values visually inferred from rasterized pixels.",
                    scope="cross_screen",
                    affected_screen_ids=[first_ctx.screen_id, mid_ctx.screen_id, last_ctx.screen_id],
                )
            )

        # 3. Overall Journey Report
        apparent_items = []
        for idx, (_, _, sc) in enumerate(screens, 1):
            label = sc.screen_label or f"Screen {idx}"
            desc = sc.description or f"Step {idx} in user sequence"
            apparent_items.append(f"{idx}. {label}: {desc} ({sc.width_px}x{sc.height_px}px)")

        apparent_structure = "; ".join(apparent_items)

        strengths = [
            JourneyStrength(
                title="Linear Sequence Clarity",
                description=f"The {len(screens)}-screen sequence provides a clear progression from entry through downstream actions.",
            ),
            JourneyStrength(
                title="Focused Content Density",
                description="Individual screens avoid excessive information crowding, keeping user focus on current task objectives.",
            ),
        ]

        friction_points = [
            FrictionPoint(
                title="Inconsistent Progression Control Positioning",
                description="Primary navigation controls shift positions between screens, causing minor orientation hesitation.",
                affected_screens=[screens[0][2].screen_id, screens[-1][2].screen_id],
                severity="medium",
            )
        ]
        if len(cross_screen_findings) > 1:
            friction_points.append(
                FrictionPoint(
                    title=cross_screen_findings[0].title,
                    description=cross_screen_findings[0].description,
                    affected_screens=cross_screen_findings[0].affected_screen_ids,
                    severity=cross_screen_findings[0].severity,
                )
            )

        recommended_improvements = [
            "Establish a persistent progression anchor across all screens (e.g. pinned footer CTA or consistent header navigation).",
            "Harmonize component tokens including border radii, input heights, and elevation shadows across all screens.",
            "Maintain clear visual feedback indicating journey progress (such as a step indicator or breadcrumb).",
            "Ensure consistent safe-area clearance for interactive touch targets across mobile viewports.",
        ]

        journey_report = JourneyReport(
            journey_summary=f"Multi-screen evaluation of {len(screens)} screens representing '{journey_name}' in {product_name}. Identified {len(screen_level_findings)} screen-level considerations and {len(cross_screen_findings)} cross-screen continuity opportunities.",
            apparent_structure=apparent_structure,
            overall_assessment=f"The flow demonstrates a functional progression across {len(screens)} stages. Key opportunities focus on spatial consistency, component token alignment, and persistent navigation anchors.",
            strengths=strengths,
            major_friction_points=friction_points,
            recommended_improvements=recommended_improvements,
            limitations="Analysis is based strictly on static screenshot evidence. Actual backend state persistence, network latency, screen transitions, and keyboard accessibility cannot be verified without live interactive testing.",
        )

        return MultiScreenAnalysisResult(
            journey_report=journey_report,
            screen_level_findings=screen_level_findings,
            cross_screen_findings=cross_screen_findings,
            provider="forteux-vision-engine",
            model="deterministic-multi-flow-v1",
        )


class MultiScreenAIVisionService:
    def __init__(self, provider: MultiScreenVisionProvider | None = None):
        self.provider = provider or DeterministicMultiScreenProvider()

    def analyze_flow(
        self,
        screens: list[tuple[bytes, str, ScreenContext]],
        journey_context: dict[str, Any] | None = None,
    ) -> MultiScreenAnalysisResult:
        logger.info("Initiating multi-screen flow analysis for %d screens", len(screens))
        return self.provider.analyze_flow(screens, journey_context)


def get_multi_screen_vision_service() -> MultiScreenAIVisionService:
    return MultiScreenAIVisionService()
