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

