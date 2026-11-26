export type AuditMode = "single" | "multi";
export type AuditStatus = "demo" | "ready" | "in_progress" | "failed";
export type KnowledgeStatus =
  | "ready"
  | "processing"
  | "extracting"
  | "chunking"
  | "embedding"
  | "indexing"
  | "failed"
  | "demo"
  | "uploaded";
export type Severity = "critical" | "high" | "medium" | "low";
export type EvidenceClass =
  | "visual_observation"
  | "source_supported"
  | "professional_guidance"
  | "demonstration";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface UploadedScreen {
  id: string;
  name: string;
  fileName: string;
  mimeType: string;
  fileSize: number;
  previewUrl?: string;
  file?: File;
  assetId?: string;
  width?: number;
  height?: number;
}

export interface DetectedIssue {
  id: string;
  number: number;
  title: string;
  category: string;
  severity: Severity;
  confidence: number;
  description: string;
  whyItMatters: string;
  recommendation: string;
  evidenceClass: EvidenceClass;
  certainty: "observed" | "suspected";
  evidence?: string;
  designPrinciple?: string;
  limitations?: string;
  screenIds: string[];
  boundingBoxes: Array<{ screenId: string; box: BoundingBox }>;
  knowledgeReferences?: Array<{ documentName: string; page?: number }>;
  selected: boolean;
  isAiGenerated?: boolean;
}

export type SelectedFinding = Pick<DetectedIssue, "id" | "number" | "title" | "selected">;

export interface User {
  id: string;
  displayName: string;
  email: string;
  role: string;
  avatarInitials: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  updatedAt: string;
  status: "Active" | "Archived";
}

export interface Audit {
  id: string;
  projectId: string;
  name: string;
  mode: AuditMode;
  status: AuditStatus;
  createdAt: string;
  screens: UploadedScreen[];
  issues: DetectedIssue[];
  context?: {
    product?: string;
    goal?: string;
    audience?: string;
    constraints?: string;
  };
  analysisFocus?: "balanced" | "visual" | "usability_accessibility";
  isDemo?: boolean;
}

export interface GeneratedPrompt {
  auditId: string;
  content: string;
  updatedAt: string;
}

export interface DocumentVersionInfo {
  id: string;
  versionNumber: number;
  originalFilename: string;
  mimeType: string;
  byteSize: number;
  pageCount?: number | null;
  chunkCount?: number | null;
  status: string;
  errorMessage?: string | null;
  createdAt: string;
  processedAt?: string | null;
}

export interface KnowledgeDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  updatedAt: string;
  status: KnowledgeStatus;
  scope: "Global" | "Project";
  projectId?: string;
  category: string;
  pages?: number;
  description?: string;
  chunkCount?: number;
  versionNumber?: number;
  processingError?: string;
  downloadUrl?: string;
  versions?: DocumentVersionInfo[];
  isDemo?: boolean;
}

export interface KnowledgeSearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  category: string;
  scope: string;
  text: string;
  page_start?: number | null;
  page_end?: number | null;
  section_heading?: string | null;
  score: number;
  retrieval_rank: number;
}

export interface DesignSystem {
  id: string;
  projectId: string;
  status: "empty" | "available";
}

// ---------------------------------------------------------------------------
// Phase 07 — Multi-Screen Flow Types
// ---------------------------------------------------------------------------

export interface MultiScreenBoundingBox {
  screen_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AuditScreen {
  id: string;
  audit_id: string;
  screen_asset_id: string;
  sequence_index: number;
  screen_label?: string | null;
  screen_description?: string | null;
  width_px?: number | null;
  height_px?: number | null;
  download_url?: string | null;
  created_at: string;
}

export interface JourneyStrength {
  title: string;
  description: string;
}

export interface FrictionPoint {
  title: string;
  description: string;
  affected_screens: string[];
  severity: "critical" | "high" | "medium" | "low";
}

export interface JourneyReport {
  journey_summary: string;
  apparent_structure: string;
  overall_assessment: string;
  strengths: JourneyStrength[];
  major_friction_points: FrictionPoint[];
  recommended_improvements: string[];
  limitations: string;
}

export interface MultiScreenFinding {
  id: string;
  audit_id: string;
  scope: "screen_level" | "cross_screen";
  affected_screen_ids: string[];
  category: string;
  title: string;
  description: string;
  why_it_matters: string;
  recommended_fix: string;
  design_principle?: string | null;
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;
  evidence_type: "observed" | "inferred";
  evidence: string;
  bounding_boxes: MultiScreenBoundingBox[];
  limitations?: string | null;
  created_at: string;
}

export interface FlowReport {
  job_id: string;
  status: string;
  journey_report?: JourneyReport | null;
  screen_level_findings: MultiScreenFinding[];
  cross_screen_findings: MultiScreenFinding[];
  created_at: string;
  completed_at?: string | null;
}

// Phase 08: Design System Intelligence Types

export interface ExtractedColor {
  hex: string;
  semantic_name: string;
  category: string;
  screens: number[];
  frequency: string;
  confidence: number;
  evidence: "observed" | "approximate" | "inferred";
}

export interface ExtractedTypography {
  style_name: string;
  font_size_approx: string;
  font_weight_category: string;
  text_hierarchy: string;
  alignment: string;
  line_height_estimate?: string | null;
  screens: number[];
  confidence: number;
  evidence: "observed" | "approximate" | "inferred";
}

export interface SpacingLayoutPattern {
  page_margins?: string | null;
  content_padding?: string | null;
  section_spacing?: string | null;
  component_gaps?: string | null;
  card_padding?: string | null;
  grid_arrangements?: string | null;
  alignment_patterns?: string | null;
  content_width_patterns?: string | null;
  confidence: number;
}

export interface ShapeSurfacePattern {
  border_radii: string[];
  card_shapes?: string | null;
  input_shapes?: string | null;
  button_shapes?: string | null;
  borders?: string | null;
  shadows: string[];
  elevation_patterns?: string | null;
  surface_treatments?: string | null;
  confidence: number;
}

export interface ComponentPattern {
  component_category: string;
  visual_description: string;
  screens: number[];
  observed_occurrences: number;
  common_characteristics: string;
  variations: string[];
  confidence: number;
  evidence_references: string;
  recommended_component_spec: string;
}

export interface ProposedDesignToken {
  name: string;
  value: string;
  category: string;
  confidence: number;
  evidence: string;
  screens: number[];
  classification: "observed" | "approximate" | "inferred";
}

export interface DesignConsistencyIssue {
  id?: string | null;
  category: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;
  affected_screens: number[];
  evidence: string;
  recommended_fix: string;
}

export interface DesignSystemReport {
  id: string;
  project_id: string;
  audit_id: string;
  status: "pending" | "analyzing" | "completed" | "failed";
  consistency_score?: number | null;
  score_breakdown: Record<string, number>;
  extraction_coverage?: number | null;
  confidence?: number | null;
  summary?: string | null;
  screens_analyzed: number;
  color_palette: ExtractedColor[];
  typography: ExtractedTypography[];
  spacing_layout: SpacingLayoutPattern;
  shapes_surfaces: ShapeSurfacePattern;
  components: ComponentPattern[];
  tokens: ProposedDesignToken[];
  consistency_issues: DesignConsistencyIssue[];
  recommendations: string[];
  limitations: string[];
  stitch_prompt?: string | null;
  provider: string;
  model: string;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface DesignSystemExportJson {
  design_system_id: string;
  audit_id: string;
  project_id: string;
  consistency_score: number | null;
  generated_at: string;
  tokens: Record<string, Record<string, string>>;
  colors: ExtractedColor[];
  typography: ExtractedTypography[];
  components: ComponentPattern[];
}

export interface DesignSystemExportCss {
  css_content: string;
  token_count: number;
}

// Phase 09 — Project Management & Export Types

export interface ProjectFull {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  platform_type: string | null;
  context_text: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  audit_count: number;
  screen_count: number;
  design_system_count: number;
}

export interface ActivityEvent {
  id: string;
  project_id: string;
  event_type: string;
  resource_id: string | null;
  resource_type: string | null;
  description: string;
  created_at: string;
}

export interface ExportJob {
  id: string;
  project_id: string;
  audit_id: string | null;
  export_type: string;
  format: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  file_size: number | null;
  error_message: string | null;
  expires_at: string | null;
  created_at: string;
  completed_at: string | null;
  download_available: boolean;
}

export interface AnalysisVersion {
  job_id: string;
  audit_id: string;
  version_number: number;
  status: string;
  provider: string;
  model: string;
  finding_count: number;
  summary: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisComparison {
  earlier_job_id: string;
  later_job_id: string;
  audit_id: string;
  comparison_type: string;
  new_findings: unknown[];
  resolved_findings: unknown[];
  persistent_findings: unknown[];
  changed_severity_findings: unknown[];
  earlier_finding_count: number;
  later_finding_count: number;
  limitations: string[];
}

export interface PaginatedAudits {
  items: AuditRead[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditRead {
  id: string;
  project_id: string;
  name: string;
  mode: 'single' | 'multi';
  status: string;
  created_at: string;
  /** Optional summary counts — may be returned by the API for dashboard views */
  screen_count?: number | null;
  finding_count?: number | null;
}

export interface DashboardAuditItem {
  id: string;
  project_id: string;
  project_name: string;
  name: string;
  mode: 'single' | 'multi';
  status: string;
  created_at: string;
  screen_count: number;
  finding_count: number;
}

export interface DashboardProjectItem {
  id: string;
  name: string;
  description: string | null;
  archived_at: string | null;
  updated_at: string;
  audit_count: number;
  screen_count: number;
}

export interface DashboardSummaryResponse {
  total_audits: number;
  screens_analysed: number;
  issues_identified: number;
  total_projects: number;
  recent_audits: DashboardAuditItem[];
  recent_projects: DashboardProjectItem[];
}
