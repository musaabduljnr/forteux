"use client";

import Link from "next/link";
import { useMemo, useRef, useState, useEffect, useCallback, type ChangeEvent, type DragEvent } from "react";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, Modal, MetricCard, PageHeader, SectionTitle } from "@/components/ui";
import { formatDate, formatFileSize } from "@/lib/demo-data";
import type { KnowledgeDocument, KnowledgeSearchResult, DocumentVersionInfo, KnowledgeStatus } from "@/lib/types";

const ACCEPTED_TYPES = [".pdf", ".docx", ".txt", ".md"];

interface ApiKnowledgeDocument {
  id: string;
  display_name: string;
  byte_size?: number;
  updated_at?: string;
  created_at?: string;
  status: KnowledgeStatus;
  category?: string;
  page_count?: number | null;
  description?: string | null;
  chunk_count?: number | null;
  version_number?: number;
  error_message?: string | null;
  download_url?: string | null;
  versions?: DocumentVersionInfo[];
}

function documentType(fileName: string): string {
  const extension = fileName.split(".").pop()?.toLowerCase();
  if (extension === "pdf") return "PDF";
  if (extension === "docx") return "DOCX";
  if (extension === "md") return "Markdown";
  if (extension === "txt") return "TXT";
  return "Unknown";
}

function documentMime(fileName: string): string {
  const extension = fileName.split(".").pop()?.toLowerCase();
  if (extension === "pdf") return "application/pdf";
  if (extension === "docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (extension === "md") return "text/markdown";
  return "text/plain";
}

async function computeSha256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default function KnowledgePage() {
  const { documents: stateDocuments, projects, selectedProjectId, notify } = useAppState();
  const [scope, setScope] = useState<"all" | "Global" | "Project">("all");
  const [projectFilter, setProjectFilter] = useState(selectedProjectId);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [detailDoc, setDetailDoc] = useState<KnowledgeDocument | null>(null);
  const [deleteDoc, setDeleteDoc] = useState<KnowledgeDocument | null>(null);
  const [documentToReplace, setDocumentToReplace] = useState<KnowledgeDocument | null>(null);
  const [remoteDocuments, setRemoteDocuments] = useState<KnowledgeDocument[]>([]);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const replaceRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const projectId = new URLSearchParams(window.location.search).get("project");
    if (projectId) setProjectFilter(projectId);
  }, []);

  // Fetch documents from backend API
  const loadDocuments = useCallback(async () => {
    try {
      const globalRes = await fetch("/api/backend/knowledge");
      if (!globalRes.ok) {
        setBackendAvailable(false);
        return;
      }
      setBackendAvailable(true);
      const globalData: ApiKnowledgeDocument[] = await globalRes.json();
      const mappedGlobal: KnowledgeDocument[] = (globalData || []).map((d) => ({
        id: d.id,
        name: d.display_name,
        type: documentType(d.display_name),
        size: d.byte_size || 0,
        updatedAt: d.updated_at || d.created_at || new Date().toISOString(),
        status: d.status,
        scope: "Global" as const,
        category: d.category || "Uncategorised",
        pages: d.page_count ?? undefined,
        description: d.description || undefined,
        chunkCount: d.chunk_count ?? undefined,
        versionNumber: d.version_number ?? 1,
        processingError: d.error_message || undefined,
        downloadUrl: d.download_url || undefined,
        versions: d.versions || [],
        isDemo: false,
      }));

      let mappedProject: KnowledgeDocument[] = [];
      const pid = projectFilter || selectedProjectId;
      if (pid) {
        const projRes = await fetch(`/api/backend/projects/${pid}/knowledge`);
        if (projRes.ok) {
          const projData: ApiKnowledgeDocument[] = await projRes.json();
          mappedProject = (projData || []).map((d) => ({
            id: d.id,
            name: d.display_name,
            type: documentType(d.display_name),
            size: d.byte_size || 0,
            updatedAt: d.updated_at || d.created_at || new Date().toISOString(),
            status: d.status,
            scope: "Project" as const,
            projectId: pid,
            category: d.category || "Uncategorised",
            pages: d.page_count ?? undefined,
            description: d.description || undefined,
            chunkCount: d.chunk_count ?? undefined,
            versionNumber: d.version_number ?? 1,
            processingError: d.error_message || undefined,
            downloadUrl: d.download_url || undefined,
            versions: d.versions || [],
            isDemo: false,
          }));
        }
      }

      setRemoteDocuments([...mappedGlobal, ...mappedProject]);
    } catch {
      setBackendAvailable(false);
    }
  }, [projectFilter, selectedProjectId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Combined documents: remote if available, else local demo state
  const allDocuments = useMemo(() => {
    if (backendAvailable && remoteDocuments.length > 0) {
      return remoteDocuments;
    }
    return stateDocuments;
  }, [backendAvailable, remoteDocuments, stateDocuments]);

  const scopedDocuments = useMemo(() => {
    return allDocuments.filter((document) => {
      if (scope !== "all" && document.scope !== scope) return false;
      if (document.scope === "Project" && projectFilter && document.projectId !== projectFilter) return false;
      if (typeFilter !== "all" && document.type !== typeFilter) return false;
      if (statusFilter !== "all" && document.status !== statusFilter) return false;
      return `${document.name} ${document.category} ${document.description ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase());
    });
  }, [allDocuments, projectFilter, query, scope, statusFilter, typeFilter]);

  const totalReady = allDocuments.filter((d) => d.status === "ready").length;
  const processingCount = allDocuments.filter((d) =>
    ["processing", "extracting", "chunking", "embedding", "indexing", "uploaded"].includes(d.status)
  ).length;
  const failedCount = allDocuments.filter((d) => d.status === "failed").length;

  // Real upload handler
  async function uploadFile(file: File, isReplacement: boolean = false, targetDoc?: KnowledgeDocument) {
    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!ACCEPTED_TYPES.includes(ext)) {
      notify(`${file.name}: supported formats are PDF, DOCX, TXT, and Markdown.`, "error");
      return;
    }

    setUploading(true);
    notify(`Processing "${file.name}"...`, "info");

    try {
      const sha256 = await computeSha256(file);
      const isGlobal = (targetDoc ? targetDoc.scope === "Global" : scope === "Global");
      const pid = targetDoc?.projectId || projectFilter || selectedProjectId;

      let uploadEndpoint: string;
      if (isReplacement && targetDoc) {
        uploadEndpoint = isGlobal
          ? `/api/backend/knowledge/${targetDoc.id}/replace`
          : `/api/backend/projects/${pid}/knowledge/${targetDoc.id}/replace`;
      } else {
        uploadEndpoint = isGlobal
          ? "/api/backend/knowledge/upload"
          : `/api/backend/projects/${pid}/knowledge/upload`;
      }

      // Step 1: Request upload intent
      const intentRes = await fetch(uploadEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: documentMime(file.name),
          size: file.size,
          scope: isGlobal ? "global" : "project",
          category: "Design Guidelines",
          description: `Uploaded reference document: ${file.name}`,
        }),
      });

      if (!intentRes.ok) {
        const err = await intentRes.json().catch(() => ({}));
        const msg = err.detail?.message || err.detail || `Upload failed with status ${intentRes.status}`;
        notify(msg, "error");
        return;
      }

      const intent = await intentRes.json();

      // Step 2: Upload bytes to storage (presigned S3 URL)
      const putRes = await fetch(intent.upload_url, {
        method: "PUT",
        headers: { "Content-Type": documentMime(file.name) },
        body: file,
      });

      if (!putRes.ok && putRes.status !== 200 && putRes.status !== 204) {
        notify("Failed to write document to storage.", "error");
        return;
      }

      // Step 3: Complete upload and trigger processing pipeline
      const completeEndpoint = isGlobal
        ? `/api/backend/knowledge/${intent.document_id}/complete`
        : `/api/backend/projects/${pid}/knowledge/${intent.document_id}/complete`;

      const completeRes = await fetch(completeEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version_id: intent.version_id,
          sha256,
        }),
      });

      if (!completeRes.ok) {
        const err = await completeRes.json().catch(() => ({}));
        const msg = err.detail?.message || err.detail || "Processing pipeline failed";
        notify(msg, "error");
        await loadDocuments();
        return;
      }

      const completedDoc = await completeRes.json();
      notify(`"${file.name}" processed successfully: ${completedDoc.chunk_count || 0} chunks indexed.`, "success");
      await loadDocuments();
    } catch (err) {
      notify(`Upload failed: ${err instanceof Error ? err.message : String(err)}`, "error");
    } finally {
      setUploading(false);
      setDocumentToReplace(null);
    }
  }

  function addFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      if (documentToReplace) {
        uploadFile(file, true, documentToReplace);
      } else {
        uploadFile(file, false);
      }
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.currentTarget.files) addFiles(event.currentTarget.files);
    event.currentTarget.value = "";
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  }

  async function handleDelete(doc: KnowledgeDocument) {
    try {
      const isGlobal = doc.scope === "Global";
      const pid = doc.projectId || projectFilter || selectedProjectId;
      const endpoint = isGlobal
        ? `/api/backend/knowledge/${doc.id}`
        : `/api/backend/projects/${pid}/knowledge/${doc.id}`;

      const res = await fetch(endpoint, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        notify(`Document "${doc.name}" deleted and excluded from retrieval.`, "success");
        await loadDocuments();
      } else {
        notify("Failed to delete document from backend.", "error");
      }
    } catch {
      notify("Network error during document deletion.", "error");
    } finally {
      setDeleteDoc(null);
    }
  }

  async function handleRetry(doc: KnowledgeDocument) {
    try {
      const isGlobal = doc.scope === "Global";
      const pid = doc.projectId || projectFilter || selectedProjectId;
      const endpoint = isGlobal
        ? `/api/backend/knowledge/${doc.id}/retry`
        : `/api/backend/projects/${pid}/knowledge/${doc.id}/retry`;

      notify(`Retrying processing for "${doc.name}"...`, "info");
      const res = await fetch(endpoint, { method: "POST" });
      if (res.ok) {
        notify(`Processing completed for "${doc.name}".`, "success");
        await loadDocuments();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail?.message || "Retry failed.", "error");
      }
    } catch {
      notify("Failed to trigger reprocessing.", "error");
    }
  }

  async function handleSemanticSearch() {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const isGlobal = scope === "Global";
      const pid = projectFilter || selectedProjectId;
      const endpoint = (isGlobal || !pid)
        ? "/api/backend/knowledge/search"
        : `/api/backend/projects/${pid}/knowledge/search`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          include_global: true,
          include_project: true,
          top_k: 6,
        }),
      });

      if (res.ok) {
        const results = await res.json();
        setSearchResults(results);
      } else {
        setSearchResults([]);
      }
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  function statusBadge(document: KnowledgeDocument) {
    if (document.isDemo || document.status === "demo") return <Badge tone="demo">Demo metadata</Badge>;
    if (document.status === "ready") return <Badge tone="success"><Icon name="check" size={13} />Ready</Badge>;
    if (["processing", "extracting", "chunking", "embedding", "indexing", "uploaded"].includes(document.status)) {
      return <Badge tone="warning"><Icon name="clock" size={13} />{document.status}</Badge>;
    }
    return <Badge tone="danger"><Icon name="warning" size={13} />Failed</Badge>;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Manage"
        title="Knowledge library"
        description="Organise design systems, brand guidelines, and reference documents for AI-grounded auditing."
        action={
          <Button onClick={() => inputRef.current?.click()} icon="upload" disabled={uploading}>
            {uploading ? "Uploading..." : "Add documents"}
          </Button>
        }
      />

      <div className="metrics-grid knowledge-metrics">
        <MetricCard label="Total documents" value={allDocuments.length} detail="In accessible libraries" icon="file" tint="blue" />
        <MetricCard label="Indexed & ready" value={totalReady} detail="Available for RAG retrieval" icon="check" tint="green" />
        <MetricCard label="Processing" value={processingCount} detail="Pipeline running" icon="clock" tint="amber" />
        <MetricCard label="Action required" value={failedCount} detail="Extraction or format errors" icon="warning" tint="violet" />
      </div>

      <section className="knowledge-upload-section panel">
        <SectionTitle
          title="Add knowledge sources"
          description="Supported formats: PDF, DOCX, TXT, and Markdown (up to 20MB)."
        />
        <div
          className={`knowledge-dropzone ${dragging ? "upload-dropzone-active" : ""}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <span className="upload-icon"><Icon name="upload" size={21} /></span>
          <div>
            <strong>Drag files here, or <button className="text-button" type="button" onClick={() => inputRef.current?.click()}>browse</button></strong>
            <p>PDF · DOCX · TXT · Markdown</p>
          </div>
          <label className="form-field upload-scope-select">
            <span>Save as</span>
            <select value={scope === "Global" ? "Global" : "Project"} onChange={(event) => setScope(event.target.value as "Global" | "Project")}>
              <option value="Project">Project-specific</option>
              <option value="Global">Global library</option>
            </select>
          </label>
          {scope !== "Global" && (
            <label className="form-field upload-project-select">
              <span>Project</span>
              <select value={projectFilter || selectedProjectId} onChange={(event) => setProjectFilter(event.target.value)}>
                {projects.map((project) => (
                  <option value={project.id} key={project.id}>{project.name}</option>
                ))}
              </select>
            </label>
          )}
          <input
            ref={inputRef}
            className="visually-hidden"
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
            onChange={onFileChange}
            aria-label="Choose knowledge documents"
          />
        </div>
      </section>

      {/* Semantic Search Box */}
      <section className="panel" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px" }} className="search-field">
            <Icon name="search" size={17} />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (!e.target.value) setSearchResults(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSemanticSearch();
              }}
              placeholder="Search documents by keywords or semantic design concept (e.g. 'button hierarchy', 'spacing scale')..."
              style={{ border: "none", outline: "none", width: "100%", background: "transparent" }}
            />
          </div>
          <Button variant="secondary" onClick={handleSemanticSearch} disabled={searching || !query.trim()}>
            {searching ? "Searching..." : "Semantic search"}
          </Button>
          {searchResults && (
            <Button variant="secondary" onClick={() => setSearchResults(null)}>
              Clear
            </Button>
          )}
        </div>

        {/* Semantic search results view */}
        {searchResults && (
          <div style={{ marginTop: "16px", borderTop: "1px solid var(--border-subtle, #e2e8f0)", paddingTop: "12px" }}>
            <h4 style={{ margin: "0 0 10px 0", fontSize: "14px" }}>
              Retrieved passages ({searchResults.length})
            </h4>
            {searchResults.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: "13px" }}>No semantic matches found above the similarity threshold.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {searchResults.map((result) => (
                  <div
                    key={result.chunk_id}
                    style={{
                      padding: "10px 14px",
                      borderRadius: "6px",
                      background: "var(--surface-muted, #f8fafc)",
                      fontSize: "13px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <strong>{result.document_name} {result.section_heading ? `— ${result.section_heading}` : ""}</strong>
                      <span style={{ color: "#64748b" }}>
                        Score: {(result.score * 100).toFixed(1)}% {result.page_start ? `· Page ${result.page_start}` : ""}
                      </span>
                    </div>
                    <p style={{ margin: 0, color: "#334155", fontStyle: "italic" }}>
                      &ldquo;{result.text.length > 220 ? result.text.slice(0, 220) + "..." : result.text}&rdquo;
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="panel knowledge-documents-panel">
        <SectionTitle title="Documents" description="Reference sources active for AI audit analysis and Stitch prompt generation." />
        <div className="knowledge-tabs" role="group" aria-label="Filter by knowledge scope">
          {(["all", "Global", "Project"] as const).map((item) => (
            <button
              key={item}
              aria-pressed={scope === item}
              className={scope === item ? "knowledge-tab-active" : ""}
              onClick={() => setScope(item)}
            >
              {item === "all" ? "All knowledge" : `${item} library`}
              <span>
                {item === "all"
                  ? allDocuments.length
                  : allDocuments.filter(
                    (doc) => doc.scope === item && (item !== "Project" || !projectFilter || doc.projectId === projectFilter)
                  ).length}
              </span>
            </button>
          ))}
          <Link className="knowledge-project-link" href="/projects">
            Manage projects <Icon name="arrow" size={14} />
          </Link>
        </div>

        <div className="knowledge-toolbar">
          <label className="toolbar-select">
            <span className="visually-hidden">Filter by file type</span>
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="all">All file types</option>
              <option value="PDF">PDF</option>
              <option value="DOCX">DOCX</option>
              <option value="TXT">TXT</option>
              <option value="Markdown">Markdown</option>
            </select>
          </label>
          <label className="toolbar-select">
            <span className="visually-hidden">Filter by processing status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              <option value="ready">Ready</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          {scope !== "Global" && (
            <label className="toolbar-select">
              <span className="visually-hidden">Filter by project</span>
              <select value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
                <option value="">All projects</option>
                {projects.map((project) => (
                  <option value={project.id} key={project.id}>{project.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>

        <div className="table-scroll">
          {scopedDocuments.length ? (
            <table className="data-table knowledge-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Scope</th>
                  <th>Category</th>
                  <th>Size</th>
                  <th>Version</th>
                  <th>Chunks</th>
                  <th>Status</th>
                  <th><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {scopedDocuments.map((document) => (
                  <tr key={document.id}>
                    <td>
                      <button className="document-name-cell" onClick={() => setDetailDoc(document)}>
                        <span className="document-type-icon"><Icon name="file" size={17} /></span>
                        <span>
                          {document.name}
                          <small>{document.pages ? `${document.pages} page${document.pages > 1 ? "s" : ""}` : formatFileSize(document.size)}</small>
                        </span>
                      </button>
                    </td>
                    <td>
                      <span className="scope-label">
                        {document.scope === "Global"
                          ? "Global"
                          : projects.find((p) => p.id === document.projectId)?.name ?? "Project"}
                      </span>
                    </td>
                    <td>{document.category}</td>
                    <td>{formatFileSize(document.size)}</td>
                    <td>v{document.versionNumber || 1}</td>
                    <td>{document.chunkCount ?? (document.status === "ready" ? "Indexed" : "—")}</td>
                    <td>{statusBadge(document)}</td>
                    <td>
                      <div className="table-actions">
                        <button className="icon-button" aria-label={`View ${document.name}`} onClick={() => setDetailDoc(document)}>
                          <Icon name="eye" size={16} />
                        </button>
                        {document.status === "failed" && (
                          <button
                            className="icon-button"
                            aria-label={`Retry ${document.name}`}
                            onClick={() => handleRetry(document)}
                            title="Retry extraction and embedding"
                          >
                            <Icon name="spark" size={16} />
                          </button>
                        )}
                        <button
                          className="icon-button"
                          aria-label={`Replace ${document.name}`}
                          onClick={() => {
                            setDocumentToReplace(document);
                            replaceRef.current?.click();
                          }}
                          title="Upload new version"
                        >
                          <Icon name="upload" size={16} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label={`Delete ${document.name}`}
                          onClick={() => setDeleteDoc(document)}
                          title="Delete document and remove from RAG"
                        >
                          <Icon name="trash" size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState
              icon="book"
              title={allDocuments.length ? "No documents match these filters" : "Your knowledge library is ready"}
              description={
                allDocuments.length
                  ? "Try adjusting the search, scope, or filters."
                  : "Upload brand standards, design guidelines, or component documentation to ground your UI audits."
              }
              action={
                !allDocuments.length ? (
                  <Button variant="secondary" icon="upload" onClick={() => inputRef.current?.click()}>
                    Choose a document
                  </Button>
                ) : undefined
              }
            />
          )}
        </div>
      </section>

      <input
        ref={replaceRef}
        className="visually-hidden"
        type="file"
        accept=".pdf,.docx,.txt,.md"
        onChange={onFileChange}
        aria-label="Choose replacement knowledge document"
      />

      {detailDoc && (
        <Modal
          title={detailDoc.name}
          description="Document provenance and indexing metadata."
          onClose={() => setDetailDoc(null)}
          footer={
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", width: "100%" }}>
              {detailDoc.downloadUrl && (
                <a href={detailDoc.downloadUrl} download={detailDoc.name} target="_blank" rel="noreferrer">
                  <Button variant="secondary" icon="arrow">Download file</Button>
                </a>
              )}
              <Button variant="secondary" onClick={() => setDetailDoc(null)}>Close</Button>
            </div>
          }
        >
          <dl className="document-detail-list">
            <div>
              <dt>Scope</dt>
              <dd>{detailDoc.scope === "Global" ? "Global library" : projects.find((p) => p.id === detailDoc.projectId)?.name ?? "Project-specific"}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{detailDoc.category}</dd>
            </div>
            <div>
              <dt>File type & size</dt>
              <dd>{detailDoc.type} · {formatFileSize(detailDoc.size)}</dd>
            </div>
            <div>
              <dt>Pages</dt>
              <dd>{detailDoc.pages ? `${detailDoc.pages} extracted` : "N/A (text stream)"}</dd>
            </div>
            <div>
              <dt>Indexed chunks</dt>
              <dd>{detailDoc.chunkCount ? `${detailDoc.chunkCount} semantic passages` : "Not chunked"}</dd>
            </div>
            <div>
              <dt>Active version</dt>
              <dd>v{detailDoc.versionNumber || 1}</dd>
            </div>
            <div>
              <dt>Processing status</dt>
              <dd>{detailDoc.status}</dd>
            </div>
            <div>
              <dt>Last updated</dt>
              <dd>{formatDate(detailDoc.updatedAt)}</dd>
            </div>
          </dl>
          {detailDoc.processingError && (
            <div className="confirmation-callout" style={{ borderColor: "#ef4444" }}>
              <Icon name="warning" size={18} />
              <p><strong>Processing error:</strong> {detailDoc.processingError}</p>
            </div>
          )}
          {detailDoc.description && (
            <div className="confirmation-callout">
              <Icon name="info" size={18} />
              <p>{detailDoc.description}</p>
            </div>
          )}
        </Modal>
      )}

      {deleteDoc && (
        <Modal
          title="Remove document from library?"
          description={`Permanently delete “${deleteDoc.name}” and all derived vector embeddings?`}
          onClose={() => setDeleteDoc(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setDeleteDoc(null)}>Cancel</Button>
              <Button variant="danger" icon="trash" onClick={() => handleDelete(deleteDoc)}>
                Delete permanently
              </Button>
            </>
          }
        >
          <p className="modal-body-copy">
            This permanently deletes the document record, raw object storage files, and all extracted
            semantic passages. Any future UI audits will no longer retrieve design guidance from this document.
          </p>
        </Modal>
      )}
    </div>
  );
}
