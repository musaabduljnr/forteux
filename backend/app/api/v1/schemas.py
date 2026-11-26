from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRead(BaseModel):
    id: UUID
    email: str | None
    display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=100)
    platform_type: str | None = Field(default=None, max_length=100)
    thumbnail_url: str | None = Field(default=None, max_length=900)
    context_text: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Project name cannot be blank")
        return trimmed


class ProjectRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: str | None = None
    platform_type: str | None = None
    thumbnail_url: str | None = None
    context_text: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["single", "multi"]
    context: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Audit name cannot be blank")
        return trimmed


class AuditRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    mode: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=1024)
    content_type: Literal["image/png", "image/jpeg"]
    size: int = Field(gt=0)


class UploadIntentRead(BaseModel):
    asset_id: UUID
    upload_url: str
    required_headers: dict[str, str]
    expires_in_seconds: int


class AssetRead(BaseModel):
    id: UUID
    project_id: UUID
    original_filename: str
    declared_content_type: str
    declared_size: int
    status: str
    width_px: int | None = None
    height_px: int | None = None
    orientation: int | None = None
    verified_mime_type: str | None = None
    sha256: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetDownloadRead(BaseModel):
    asset_id: UUID
    download_url: str
    expires_in_seconds: int


class AuditScreenCreate(BaseModel):
    screen_asset_id: UUID
    sequence_index: int = 0
    screen_label: str | None = None


class AuditScreenRead(BaseModel):
    id: UUID
    audit_id: UUID
    screen_asset_id: UUID
    sequence_index: int
    screen_label: str | None = None
    screen_description: str | None = None
    width_px: int | None = None
    height_px: int | None = None
    download_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoundingBoxRead(BaseModel):
    x: float
    y: float
    width: float
    height: float


class FindingEvidenceRead(BaseModel):
    id: UUID
    finding_id: UUID
    chunk_id: UUID
    document_id: UUID
    document_display_name: str
    quote_or_paraphrase: str | None = None
    page_number_snapshot: int | None = None
    section_heading_snapshot: str | None = None
    retrieval_score: float | None = None
    retrieval_rank: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingRead(BaseModel):
    id: UUID
    audit_id: UUID
    scope: str = "screen_level"
    affected_screen_ids: list[str] = Field(default_factory=list)
    category: str
    title: str
    description: str
    why_it_matters: str
    recommended_fix: str
    design_principle: str | None = None
    severity: str
    confidence: float
    evidence_type: str
    evidence: str
    bounding_boxes: list[BoundingBoxRead] = Field(default_factory=list)
    evidence_sources: list[FindingEvidenceRead] = Field(default_factory=list)
    limitations: str | None = None
    created_at: datetime


class AnalysisJobRead(BaseModel):
    id: UUID
    audit_id: UUID
    status: str
    provider: str
    model: str
    summary: str | None = None
    flow_report_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    job: AnalysisJobRead
    findings: list[FindingRead]


class PromptGenerateRequest(BaseModel):
    selected_finding_ids: list[UUID] = Field(min_length=1)
    user_instructions: str | None = None


class PromptUpdateRequest(BaseModel):
    content: str = Field(min_length=10)


class PromptVersionRead(BaseModel):
    id: UUID
    version_number: int
    content: str
    selected_finding_ids: list[UUID] = Field(default_factory=list)
    user_instructions: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptRead(BaseModel):
    id: UUID
    audit_id: UUID
    screen_asset_id: UUID | None = None
    content: str
    original_generated_content: str
    selected_finding_ids: list[UUID] = Field(default_factory=list)
    user_instructions: str | None = None
    provider: str
    model: str
    template_version: str
    version_number: int
    created_at: datetime
    updated_at: datetime
    versions: list[PromptVersionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DevTokenRequest(BaseModel):
    email: str = Field(default="dev@forteux.local", min_length=3, max_length=320)
    name: str = Field(default="Local Developer", min_length=1, max_length=200)


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    email: str
    name: str


# ---------------------------------------------------------------------------
# Knowledge Library Schemas (Phase 06)
# ---------------------------------------------------------------------------


class KnowledgeUploadIntentRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=100)
    size: int = Field(gt=0)
    scope: Literal["global", "project"] = "project"
    category: str = Field(default="Uncategorised", max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class KnowledgeUploadIntentRead(BaseModel):
    document_id: UUID
    version_id: UUID
    version_number: int
    object_key: str
    upload_url: str
    expires_in_seconds: int


class KnowledgeCompleteRequest(BaseModel):
    version_id: UUID
    sha256: str = Field(min_length=64, max_length=64)


class DocumentVersionRead(BaseModel):
    id: UUID
    version_number: int
    original_filename: str
    mime_type: str
    byte_size: int
    page_count: int | None = None
    chunk_count: int | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentRead(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID | None = None
    scope: str
    display_name: str
    category: str
    description: str | None = None
    status: str
    error_message: str | None = None
    active_version_id: UUID | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    byte_size: int = 0
    mime_type: str = "application/octet-stream"
    version_number: int = 1
    embedding_model: str | None = None
    created_at: datetime
    updated_at: datetime
    download_url: str | None = None
    versions: list[DocumentVersionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    include_global: bool = True
    include_project: bool = True
    top_k: int = Field(default=8, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    category: str
    scope: str
    text: str
    page_start: int | None = None
    page_end: int | None = None
    section_heading: str | None = None
    score: float
    retrieval_rank: int


# ---------------------------------------------------------------------------
# Phase 07 — Multi-Screen Flow Schemas
# ---------------------------------------------------------------------------


class AuditScreenUpdate(BaseModel):
    screen_label: str | None = Field(default=None, max_length=200)
    screen_description: str | None = Field(default=None, max_length=2000)
    sequence_index: int | None = Field(default=None, ge=0)


class ScreenReorderItem(BaseModel):
    screen_id: UUID
    sequence_index: int = Field(ge=0)


class AuditScreenReorderRequest(BaseModel):
    screens: list[ScreenReorderItem] = Field(min_length=1)


class AuditContextUpdate(BaseModel):
    context: dict[str, str] = Field(default_factory=dict)


class MultiScreenBoundingBoxRead(BaseModel):
    screen_id: str
    x: float
    y: float
    width: float
    height: float


class JourneyStrengthRead(BaseModel):
    title: str
    description: str


class FrictionPointRead(BaseModel):
    title: str
    description: str
    affected_screens: list[str] = Field(default_factory=list)
    severity: str


class JourneyReportRead(BaseModel):
    journey_summary: str
    apparent_structure: str
    overall_assessment: str
    strengths: list[JourneyStrengthRead]
    major_friction_points: list[FrictionPointRead]
    recommended_improvements: list[str]
    limitations: str


class MultiScreenFindingRead(BaseModel):
    id: UUID
    audit_id: UUID
    scope: str
    affected_screen_ids: list[str] = Field(default_factory=list)
    category: str
    title: str
    description: str
    why_it_matters: str
    recommended_fix: str
    design_principle: str | None = None
    severity: str
    confidence: float
    evidence_type: str
    evidence: str
    bounding_boxes: list[MultiScreenBoundingBoxRead] = Field(default_factory=list)
    limitations: str | None = None
    evidence_sources: list[FindingEvidenceRead] = Field(default_factory=list)
    created_at: datetime


class MultiScreenAnalysisResponse(BaseModel):
    job: AnalysisJobRead
    journey_report: JourneyReportRead
    screen_level_findings: list[MultiScreenFindingRead]
    cross_screen_findings: list[MultiScreenFindingRead]


class FlowReportRead(BaseModel):
    job_id: UUID
    status: str
    journey_report: JourneyReportRead | None = None
    screen_level_findings: list[MultiScreenFindingRead] = Field(default_factory=list)
    cross_screen_findings: list[MultiScreenFindingRead] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


# Phase 08: Design System Extraction Schemas

class ExtractedColor(BaseModel):
    hex: str
    semantic_name: str
    category: str  # primary, secondary, accent, background, surface, text, border, status
    screens: list[int] = Field(default_factory=list)
    frequency: str = "recurring"  # primary, recurring, rare
    confidence: float = 0.9
    evidence: str = "observed"  # observed, approximate, inferred


class ExtractedTypography(BaseModel):
    style_name: str  # heading.large, heading.medium, body.large, label, etc.
    font_size_approx: str  # e.g. "24px / 1.5rem"
    font_weight_category: str  # bold, semibold, regular, medium
    text_hierarchy: str  # display, h1, h2, h3, body, caption, button
    alignment: str = "left"
    line_height_estimate: str | None = None
    screens: list[int] = Field(default_factory=list)
    confidence: float = 0.85
    evidence: str = "approximate"


class SpacingLayoutPattern(BaseModel):
    page_margins: str | None = None
    content_padding: str | None = None
    section_spacing: str | None = None
    component_gaps: str | None = None
    card_padding: str | None = None
    grid_arrangements: str | None = None
    alignment_patterns: str | None = None
    content_width_patterns: str | None = None
    confidence: float = 0.8


class ShapeSurfacePattern(BaseModel):
    border_radii: list[str] = Field(default_factory=list)
    card_shapes: str | None = None
    input_shapes: str | None = None
    button_shapes: str | None = None
    borders: str | None = None
    shadows: list[str] = Field(default_factory=list)
    elevation_patterns: str | None = None
    surface_treatments: str | None = None
    confidence: float = 0.85


class ComponentPattern(BaseModel):
    component_category: str  # button.primary, input.text, card.standard, navbar, tab.bar, badge, etc.
    visual_description: str
    screens: list[int] = Field(default_factory=list)
    observed_occurrences: int = 1
    common_characteristics: str
    variations: list[str] = Field(default_factory=list)
    confidence: float = 0.9
    evidence_references: str = "observed"
    recommended_component_spec: str


class ProposedDesignToken(BaseModel):
    name: str  # color.primary, typography.heading.large, spacing.4, radius.medium, shadow.small
    value: str
    category: str  # color, typography, spacing, radius, shadow
    confidence: float = 0.9
    evidence: str = "observed"  # observed, approximate, inferred
    screens: list[int] = Field(default_factory=list)
    classification: str = "observed"


class DesignConsistencyIssue(BaseModel):
    id: str | None = None
    category: str  # color, typography, components, spacing, surfaces, navigation
    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    confidence: float = 0.85
    affected_screens: list[int] = Field(default_factory=list)
    evidence: str
    recommended_fix: str


class DesignSystemReportRead(BaseModel):
    id: UUID
    project_id: UUID
    audit_id: UUID
    status: str
    consistency_score: float | None = None
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    extraction_coverage: float | None = None
    confidence: float | None = None
    summary: str | None = None
    screens_analyzed: int = 0
    color_palette: list[ExtractedColor] = Field(default_factory=list)
    typography: list[ExtractedTypography] = Field(default_factory=list)
    spacing_layout: SpacingLayoutPattern = Field(default_factory=SpacingLayoutPattern)
    shapes_surfaces: ShapeSurfacePattern = Field(default_factory=ShapeSurfacePattern)
    components: list[ComponentPattern] = Field(default_factory=list)
    tokens: list[ProposedDesignToken] = Field(default_factory=list)
    consistency_issues: list[DesignConsistencyIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    stitch_prompt: str | None = None
    provider: str
    model: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DesignSystemExportJson(BaseModel):
    design_system_id: str
    audit_id: str
    project_id: str
    consistency_score: float | None
    generated_at: str
    tokens: dict[str, dict[str, str]]
    colors: list[ExtractedColor]
    typography: list[ExtractedTypography]
    components: list[ComponentPattern]


class DesignSystemExportCss(BaseModel):
    css_content: str
    token_count: int


class DesignSystemPromptRequest(BaseModel):
    custom_instructions: str | None = None
    include_inconsistencies: bool = True
    include_tokens: bool = True


class DesignSystemPromptResponse(BaseModel):
    prompt: str
    tokens_included: int
    issues_addressed: int
    screens_referenced: int


# ---------------------------------------------------------------------------
# Phase 09: Project Management, Versioning & Export Schemas
# ---------------------------------------------------------------------------


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=100)
    platform_type: str | None = Field(default=None, max_length=100)
    thumbnail_url: str | None = Field(default=None, max_length=900)
    context_text: str | None = Field(default=None, max_length=4000)


class ProjectReadFull(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: str | None = None
    platform_type: str | None = None
    thumbnail_url: str | None = None
    context_text: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    audit_count: int = 0
    screen_count: int = 0
    design_system_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectActivityEventRead(BaseModel):
    id: UUID
    project_id: UUID
    event_type: str
    resource_id: UUID | None = None
    resource_type: str | None = None
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportJobCreate(BaseModel):
    export_type: Literal["single_audit", "multi_audit", "design_system", "stitch_prompt", "project_package"]
    format: Literal["json", "markdown", "csv", "zip"]
    audit_id: UUID | None = None


class ExportJobRead(BaseModel):
    id: UUID
    project_id: UUID
    audit_id: UUID | None = None
    export_type: str
    format: str
    status: str
    file_size: int | None = None
    error_message: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    completed_at: datetime | None = None
    download_available: bool = False

    model_config = ConfigDict(from_attributes=True)


class AnalysisVersionRead(BaseModel):
    job_id: UUID
    audit_id: UUID
    version_number: int
    status: str
    provider: str
    model: str
    finding_count: int
    summary: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisComparisonRead(BaseModel):
    earlier_job_id: UUID
    later_job_id: UUID
    audit_id: UUID
    comparison_type: str  # single_screen | multi_screen
    new_findings: list[FindingRead] = Field(default_factory=list)
    resolved_findings: list[FindingRead] = Field(default_factory=list)
    persistent_findings: list[FindingRead] = Field(default_factory=list)
    changed_severity_findings: list[FindingRead] = Field(default_factory=list)
    earlier_finding_count: int = 0
    later_finding_count: int = 0
    limitations: list[str] = Field(default_factory=list)


class PaginatedAuditsResponse(BaseModel):
    items: list[AuditRead]
    total: int
    page: int
    page_size: int


class DashboardAuditItem(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str
    name: str
    mode: str
    status: str
    created_at: datetime
    screen_count: int = 0
    finding_count: int = 0


class DashboardProjectItem(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    archived_at: datetime | None = None
    updated_at: datetime
    audit_count: int = 0
    screen_count: int = 0


class DashboardSummaryResponse(BaseModel):
    total_audits: int = 0
    screens_analysed: int = 0
    issues_identified: int = 0
    total_projects: int = 0
    recent_audits: list[DashboardAuditItem] = Field(default_factory=list)
    recent_projects: list[DashboardProjectItem] = Field(default_factory=list)



