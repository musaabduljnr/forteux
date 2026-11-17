import type {
  Audit,
  GeneratedPrompt,
  KnowledgeDocument,
  Project,
  UploadedScreen,
} from "@/lib/types";

export interface CreateAuditRequest {
  projectId: string;
  name: string;
  mode: Audit["mode"];
  screens: UploadedScreen[];
  context?: Audit["context"];
  analysisFocus?: Audit["analysisFocus"];
}

export interface ProjectService {
  list(): Promise<Project[]>;
  create(input: Pick<Project, "name" | "description">): Promise<Project>;
  update(id: string, input: Partial<Pick<Project, "name" | "description" | "status">>): Promise<Project>;
  delete(id: string): Promise<void>;
}

export interface AuditService {
  list(projectId?: string): Promise<Audit[]>;
  get(id: string): Promise<Audit | null>;
  create(input: CreateAuditRequest): Promise<Audit>;
  updateFindingSelection(auditId: string, findingIds: string[]): Promise<void>;
  savePrompt(auditId: string, prompt: GeneratedPrompt): Promise<GeneratedPrompt>;
}

export interface KnowledgeLibraryService {
  list(projectId?: string): Promise<KnowledgeDocument[]>;
  requestUpload(projectId: string, file: File): Promise<{ documentId: string; uploadUrl: string }>;
  replace(documentId: string, file: File): Promise<KnowledgeDocument>;
  delete(documentId: string): Promise<void>;
}
