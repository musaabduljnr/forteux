"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { useAppState } from "./app-state";
import { Icon } from "./icons";
import { Badge, Button, EmptyState, SeverityBadge } from "./ui";
import type { DetectedIssue } from "@/lib/types";

interface PromptVersionItem {
  id: string;
  version_number: number;
  created_at: string;
  content: string;
  selected_finding_ids: string[];
}

function PromptDialog({
  content,
  originalContent,
  versionNumber,
  versions,
  dialogRef,
  userInstructions,
  selectionChangedSincePrompt,
  generating,
  copied,
  onChangeContent,
  onChangeInstructions,
  onClose,
  onCopy,
  onRegenerate,
  onRestoreOriginal,
  onSelectVersion,
}: {
  content: string;
  originalContent: string | null;
  versionNumber: number;
  versions: PromptVersionItem[];
  dialogRef: RefObject<HTMLElement | null>;
  userInstructions: string;
  selectionChangedSincePrompt: boolean;
  generating: boolean;
  copied: boolean;
  onChangeContent: (value: string) => void;
  onChangeInstructions: (value: string) => void;
  onClose: () => void;
  onCopy: () => void;
  onRegenerate: () => void;
  onRestoreOriginal: () => void;
  onSelectVersion: (version: PromptVersionItem) => void;
}) {
  const isEdited = originalContent !== null && content !== originalContent;

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="dialog prompt-dialog" ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="prompt-dialog-title" tabIndex={-1} onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
        if (event.key === "Tab") {
          const focusable = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("button, textarea, input")).filter((element) => !element.hasAttribute("disabled"));
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
      }}>
        <div className="dialog-heading">
          <div>
            <div className="breadcrumb" style={{ gap: "6px" }}>
              <Badge tone="blue">Google Stitch Redesign Brief</Badge>
              <Badge tone="neutral">v{versionNumber}</Badge>
            </div>
            <h2 id="prompt-dialog-title">Google Stitch Redesign Brief</h2>
            <p>Review and refine the generated design brief before copying into Google Stitch.</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close prompt editor"><Icon name="close" /></button>
        </div>

        {selectionChangedSincePrompt && (
          <div className="demo-notice demo-notice-strong" style={{ margin: "10px 19px 0" }}>
            <Icon name="info" size={15} />
            <span>Finding selections changed in workspace. Click <strong>Regenerate</strong> to update the brief with your latest selections.</span>
          </div>
        )}

        <div className="stitch-handoff-banner">
          <div>
            <strong>Google Stitch Handoff:</strong> Provide your original screenshot to Stitch, then paste this brief into the prompt box.
          </div>
          <a href="https://stitch.withgoogle.com" target="_blank" rel="noopener noreferrer">
            Open Google Stitch <Icon name="arrow" size={13} />
          </a>
        </div>

        {versions.length > 1 && (
          <div className="prompt-versions-bar">
            <span>Version History:</span>
            {versions.map((v) => (
              <button
                key={v.id}
                type="button"
                className={`version-chip ${v.version_number === versionNumber ? "version-chip-active" : ""}`}
                onClick={() => onSelectVersion(v)}
                title={`Created ${new Date(v.created_at).toLocaleTimeString()}`}
              >
                v{v.version_number} ({v.selected_finding_ids.length} issues)
              </button>
            ))}
          </div>
        )}

        <label className="visually-hidden" htmlFor="prompt-content">Editable Google Stitch prompt</label>
        <textarea id="prompt-content" className="prompt-textarea" value={content} onChange={(event) => onChangeContent(event.target.value)} />

        <div className="prompt-options-wrap">
          <label htmlFor="dialog-user-instructions">Additional design preferences (optional):</label>
          <input
            id="dialog-user-instructions"
            type="text"
            className="prompt-instructions-input"
            placeholder="e.g. Preserve dark brand colors, use 12px rounded pill buttons, make layout more compact..."
            value={userInstructions}
            onChange={(event) => onChangeInstructions(event.target.value)}
          />
        </div>

        <div className="dialog-footer">
          <div>
            {isEdited ? (
              <div className="button-row" style={{ alignItems: "center" }}>
                <Badge tone="warning">Edited manually</Badge>
                <Button variant="secondary" onClick={onRestoreOriginal}>Restore original</Button>
              </div>
            ) : (
              <span className="helper-text">Structured brief ready for Google Stitch.</span>
            )}
          </div>
          <div className="button-row">
            <Button variant="secondary" icon="spark" onClick={onRegenerate} disabled={generating}>
              {generating ? "Regenerating..." : "Regenerate"}
            </Button>
            <Button icon={copied ? "check" : "copy"} onClick={onCopy}>
              {copied ? "Copied to clipboard" : "Copy complete prompt"}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

function IssueCard({
  issue,
  active,
  selected,
  onSelect,
  onToggle,
}: {
  issue: DetectedIssue;
  active: boolean;
  selected: boolean;
  onSelect: () => void;
  onToggle: () => void;
}) {
  return (
    <article className={`finding-card ${active ? "finding-card-active" : ""} ${!selected ? "finding-card-deselected" : ""}`}>
      <button className="finding-main" onClick={onSelect} aria-label={`View finding ${issue.number}: ${issue.title}`}>
        <span className={`issue-number issue-number-${issue.severity}`}>{issue.number}</span>
        <span className="finding-title-wrap"><strong>{issue.title}</strong><small>{issue.category.replace(/_/g, " ")}</small></span>
        <Icon name="chevron" size={16} />
      </button>
      <div className="finding-meta">
        <SeverityBadge severity={issue.severity} />
        <Badge tone={issue.isAiGenerated ? "blue" : "demo"}>{issue.isAiGenerated ? "AI Vision finding" : "Demo fixture"}</Badge>
        <Badge tone={issue.certainty === "observed" ? "neutral" : "demo"}>{issue.certainty === "observed" ? "Observed" : "Inferred"}</Badge>
        <Badge>{Math.round(issue.confidence * 100)}% confidence</Badge>
      </div>
      <p className="finding-description">{issue.description}</p>
      {issue.evidence && <div className="finding-detail"><strong>Visual evidence</strong><p>{issue.evidence}</p></div>}
      <div className="finding-detail"><strong>Why it matters</strong><p>{issue.whyItMatters}</p></div>
      <div className="finding-detail"><strong>Suggested direction</strong><p>{issue.recommendation}</p></div>
      {issue.designPrinciple && <div className="finding-detail"><strong>Design principle</strong><p>{issue.designPrinciple}</p></div>}
      {issue.limitations && <div className="finding-detail"><strong>Audit limitations</strong><p>{issue.limitations}</p></div>}
      {issue.knowledgeReferences?.length ? <div className="finding-detail"><strong>Knowledge references</strong><p>{issue.knowledgeReferences.map((reference) => `${reference.documentName}${reference.page ? `, p. ${reference.page}` : ""}`).join("; ")}</p></div> : null}
      <div className="finding-footer">
        {issue.isAiGenerated ? (
          <span className="evidence-label"><Icon name="spark" size={14} />AI Vision Observation · {issue.certainty}</span>
        ) : (
          <span className="evidence-label"><Icon name="info" size={14} />Illustrative only · not an AI finding</span>
        )}
        <label className="selection-control">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            aria-label={`Include finding ${issue.number}: ${issue.title} in Stitch redesign brief`}
          />
          <span>{selected ? "Included in brief" : "Excluded"}</span>
        </label>
      </div>
    </article>
  );
}

function ScreenshotViewer({
  auditId,
  screenId,
  screenName,
  previewUrl,
  issues,
  selectedIssueIds,
  activeIssueId,
  onSelectIssue,
}: {
  auditId: string;
  screenId: string;
  screenName: string;
  previewUrl?: string;
  issues: DetectedIssue[];
  selectedIssueIds: string[];
  activeIssueId: string | null;
  onSelectIssue: (id: string) => void;
}) {
  const [zoom, setZoom] = useState(100);
  return (
    <div className="screenshot-stage">
      {previewUrl ? (
        <div className="screenshot-scroll">
          <div className="screenshot-image-wrap" style={{ width: `${zoom}%` }}>
            <Image src={previewUrl} alt={`${screenName} screenshot`} fill sizes="(max-width: 1200px) 100vw, 65vw" unoptimized priority />
            {issues.flatMap((issue) => issue.boundingBoxes.filter((annotation) => annotation.screenId === screenId).map(({ box }, bIdx) => {
              const isSelected = selectedIssueIds.includes(issue.id);
              return (
                <button
                  type="button"
                  key={`${issue.id}-${screenId}-${bIdx}`}
                  className={`annotation-box ${activeIssueId === issue.id ? "annotation-box-active" : ""} ${!isSelected ? "annotation-box-deselected" : ""}`}
                  style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }}
                  aria-label={`Finding ${issue.number}: ${issue.title}${!isSelected ? " (Excluded from brief)" : ""}`}
                  title={`[${issue.category.replace(/_/g, " ")}] ${issue.title} (${Math.round(issue.confidence * 100)}% confidence)${!isSelected ? " — Excluded" : ""}`}
                  onClick={() => onSelectIssue(issue.id)}
                >
                  <span className={`annotation-marker annotation-marker-${issue.severity} ${activeIssueId === issue.id ? "annotation-marker-active" : ""}`}>{issue.number}</span>
                </button>
              );
            }))}
            {auditId === "demo-audit" && <div className="fixture-image-label">Illustrative screenshot · demo fixture</div>}
          </div>
        </div>
      ) : (
        <div className="viewer-placeholder">
          <div className="placeholder-icon"><Icon name="image" size={25} /></div>
          <strong>{screenName}</strong>
          <p>{auditId === "demo-flow" ? "Illustrative flow workspace; no real screenshots or analysis are included." : "Image preview is available only in the upload session. Re-add the screenshot to view it again."}</p>
          <Badge tone="demo">No server upload</Badge>
        </div>
      )}
      <div className="viewer-toolbar">
        <span className="viewer-screen-name"><Icon name="image" size={15} />{screenName}</span>
        <div className="zoom-controls"><button className="icon-button" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(50, value - 10))}>−</button><span>{zoom}%</span><button className="icon-button" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(150, value + 10))}>+</button><button className="fit-button" onClick={() => setZoom(100)}>Fit</button></div>
      </div>
    </div>
  );
}

function FlowOverview({ screens, selectedId, onSelect }: { screens: AuditScreen[]; selectedId: string; onSelect: (id: string) => void }) {
  return (
    <div className="flow-overview">
      <div className="flow-overview-heading"><div><strong>Screen sequence</strong><span>User-provided order · no live product traversal</span></div><Badge tone="demo">Illustrative flow</Badge></div>
      <div className="flow-canvas">
        {screens.map((screen, index) => (
          <div className="flow-node-wrap" key={screen.id}>
            <button type="button" className={`flow-node ${selectedId === screen.id ? "flow-node-selected" : ""}`} onClick={() => onSelect(screen.id)}>
              <span className="flow-node-number">{index + 1}</span><span className="flow-node-title">{screen.name}</span><small>{screen.fileName}</small>
            </button>
            {index < screens.length - 1 && <span className="flow-connector" aria-hidden="true"><Icon name="arrow" size={17} /></span>}
          </div>
        ))}
      </div>
      <p className="flow-caption">Connections show the order provided by the user; they do not prove that the real interface navigates between these screens.</p>
    </div>
  );
}

type AuditScreen = { id: string; name: string; fileName: string; mimeType: string; fileSize: number; previewUrl?: string };

interface ApiFinding {
  id: string;
  title: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;
  description: string;
  why_it_matters: string;
  recommended_fix: string;
  evidence_type: "observed" | "inferred";
  evidence?: string;
  design_principle?: string;
  limitations?: string;
  bounding_boxes?: Array<{ x: number; y: number; width: number; height: number }>;
}

export function AuditWorkspace({ auditId }: { auditId: string }) {
  const { audits, projects, reorderAuditScreens, updateAudit, notify } = useAppState();
  const audit = audits.find((item) => item.id === auditId);
  const [selectedScreenId, setSelectedScreenId] = useState("");
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);
  const [prompt, setPrompt] = useState("");
  const [originalPromptContent, setOriginalPromptContent] = useState<string | null>(null);
  const [promptId, setPromptId] = useState<string | null>(null);
  const [promptVersionNumber, setPromptVersionNumber] = useState(1);
  const [promptVersions, setPromptVersions] = useState<PromptVersionItem[]>([]);
  const [promptSelectedFindingIds, setPromptSelectedFindingIds] = useState<string[]>([]);
  const [userInstructions, setUserInstructions] = useState("");
  const [generatingPrompt, setGeneratingPrompt] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [draggedScreen, setDraggedScreen] = useState<number | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const promptDialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!promptOpen) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = promptDialogRef.current;
    const firstFocusable = dialog?.querySelector<HTMLElement>("textarea, button");
    firstFocusable?.focus();
    return () => previousFocus?.focus();
  }, [promptOpen]);

  useEffect(() => {
    if (!audit) return;
    setSelectedScreenId((current) => audit.screens.some((screen) => screen.id === current) ? current : audit.screens[0]?.id ?? "");
    // Default selection: select all findings
    setSelectedIssues(audit.issues.map((issue) => issue.id));

    // Retrieve active prompt if already generated on backend
    fetch(`/api/backend/projects/${audit.projectId}/audits/${audit.id}/prompt`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.content) {
          setPrompt(data.content);
          setOriginalPromptContent(data.original_content || data.content);
          setPromptId(data.id);
          setPromptVersionNumber(data.version_number);
          setPromptVersions(data.versions || []);
          setPromptSelectedFindingIds(data.selected_finding_ids || []);
          if (data.user_instructions) {
            setUserInstructions(data.user_instructions);
          }
        }
      })
      .catch(() => {});
  }, [audit]);

  const currentScreen = audit?.screens.find((screen) => screen.id === selectedScreenId);
  const visibleIssues = useMemo(() => audit?.issues.filter((issue) => issue.screenIds.includes(selectedScreenId) || issue.boundingBoxes.some((item) => item.screenId === selectedScreenId)) ?? [], [audit?.issues, selectedScreenId]);
  
  const totalFindingsCount = audit?.issues.length ?? 0;
  const selectedCount = selectedIssues.length;
  const criticalCount = useMemo(() => audit?.issues.filter((i) => selectedIssues.includes(i.id) && i.severity === "critical").length ?? 0, [audit?.issues, selectedIssues]);
  const highCount = useMemo(() => audit?.issues.filter((i) => selectedIssues.includes(i.id) && i.severity === "high").length ?? 0, [audit?.issues, selectedIssues]);
  const excludedCount = totalFindingsCount - selectedCount;

  const selectionChangedSincePrompt = useMemo(() => {
    if (promptSelectedFindingIds.length === 0) return false;
    if (promptSelectedFindingIds.length !== selectedIssues.length) return true;
    return selectedIssues.some((id) => !promptSelectedFindingIds.includes(id));
  }, [promptSelectedFindingIds, selectedIssues]);

  function selectAll() {
    if (!audit) return;
    setSelectedIssues(audit.issues.map((i) => i.id));
  }

  function deselectAll() {
    setSelectedIssues([]);
  }

  async function runAiAnalysis() {
    if (!audit || analyzing) return;
    setAnalyzing(true);
    notify("Starting AI vision analysis...", "info");
    try {
      const res = await fetch(`/api/backend/projects/${audit.projectId}/audits/${audit.id}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const msg = errorData.detail || errorData.error?.message || `Analysis request failed with status ${res.status}`;
        notify(msg, "error");
        return;
      }

      const data = (await res.json()) as { findings?: ApiFinding[] };
      const findingsList = data.findings || [];
      const currentScr = audit.screens.find((s) => s.id === selectedScreenId) || audit.screens[0];

      const mappedIssues: DetectedIssue[] = findingsList.map((f, index) => {
        const boxes = (f.bounding_boxes || []).map((b) => ({
          screenId: currentScr?.id ?? "",
          box: {
            x: b.x,
            y: b.y,
            width: b.width,
            height: b.height,
          },
        }));

        return {
          id: f.id || `f-${index + 1}`,
          number: index + 1,
          title: f.title,
          category: f.category,
          severity: f.severity,
          confidence: f.confidence,
          description: f.description,
          whyItMatters: f.why_it_matters,
          recommendation: f.recommended_fix,
          evidenceClass: "visual_observation",
          certainty: f.evidence_type === "observed" ? "observed" : "suspected",
          evidence: f.evidence,
          designPrinciple: f.design_principle,
          limitations: f.limitations,
          screenIds: currentScr ? [currentScr.id] : [],
          boundingBoxes: boxes,
          selected: true,
          isAiGenerated: true,
        };
      });

      updateAudit(audit.id, {
        issues: mappedIssues,
        status: "ready",
        isDemo: false,
      });

      setSelectedIssues(mappedIssues.map((i) => i.id));
      if (mappedIssues.length > 0) {
        setActiveIssueId(mappedIssues[0].id);
      }
      notify(`AI vision analysis completed: ${mappedIssues.length} findings detected.`, "success");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to reach analysis service";
      notify(`Analysis error: ${message}`, "error");
    } finally {
      setAnalyzing(false);
    }
  }

  function toggleIssue(issueId: string) {
    setSelectedIssues((current) => current.includes(issueId) ? current.filter((id) => id !== issueId) : [...current, issueId]);
  }

  function makeStructuredPromptFallback(instructionsText?: string) {
    if (!audit) return "";
    const priority = { critical: 0, high: 1, medium: 2, low: 3 } as const;
    const selected = audit.issues
      .filter((issue) => selectedIssues.includes(issue.id))
      .sort((left, right) => priority[left.severity] - priority[right.severity]);
    if (selected.length === 0) return "";

    const productName = audit.context?.product?.trim() || audit.name || "User Interface";
    const goal = audit.context?.goal?.trim() || "Primary user workflow";
    const audience = audit.context?.audience?.trim() || "Target application users";
    const constraints = audit.context?.constraints?.trim() || "Preserve existing brand assets and layout foundation";

    const issuesBlocks = selected.map((issue, idx) => {
      const locations = issue.boundingBoxes.map((annotation) => {
        const { x, y, width, height } = annotation.box;
        const vert = y < 0.2 ? "Top" : y < 0.65 ? "Mid" : "Bottom";
        const horiz = x < 0.3 ? "Left" : x < 0.65 ? "Center" : "Right";
        return `${vert}-${horiz} section (approx. x: ${Math.round(x * 100)}%, y: ${Math.round(y * 100)}%, width: ${Math.round(width * 100)}%, height: ${Math.round(height * 100)}%)`;
      }).join("; ") || "Screen-level interface component";

      return [
        `### Issue ${idx + 1}: ${issue.title} [${issue.severity.toUpperCase()}]`,
        `- **Category**: ${issue.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}`,
        `- **Location**: ${locations}`,
        `- **Existing Problem**: ${issue.description}`,
        `- **Visual Evidence**: ${issue.evidence || "Observed in visual layout"}`,
        `- **Why It Matters**: ${issue.whyItMatters}`,
        `- **Required Improvement**: ${issue.recommendation}`,
        `- **Design Principle**: ${issue.designPrinciple || "Usability & Visual Standards"}`,
      ].join("\n");
    }).join("\n\n");

    const instructions = instructionsText !== undefined ? instructionsText : userInstructions;

    const sections = [
      `# Google Stitch Redesign Brief: ${productName}`,
      `## 1. Role & Objective\nYou are an experienced Principal UI/UX Designer, Design Systems Specialist, and Google Stitch prompt engineer. Your objective is to generate an improved, production-ready interface design that directly addresses the ${selected.length} selected usability and visual design findings identified from the uploaded screenshot. Reference the uploaded interface screenshot as the baseline visual canvas.`,
      `## 2. Existing Interface Context\n- **Product / Surface**: ${productName}\n- **User Goal**: ${goal}\n- **Target Audience**: ${audience}\n- **Baseline Visual Characteristics**: Use the provided screenshot as the authoritative source for the existing layout structure, recognizable color accents, navigation scheme, and content taxonomy. Do not invent arbitrary rebranding; preserve the identifiable product character while solving the specific defects below.`,
      `## 3. Core Design Objectives\nFocus the redesign on these required improvements:\n- Establish a clear visual hierarchy with distinct visual weight for primary versus secondary actions.\n- Harmonize spacing and padding using a consistent layout grid to resolve visual crowding.\n- Strengthen typographic contrast and modular scale differentiation between headings, labels, and body text.\n- Ensure sufficient visual contrast and legibility across all text labels and microcopy.`,
      `## 4. Prioritized Issues & Required Design Solutions\n\n${issuesBlocks}`,
      `## 5. Visual Design Requirements\n- **Layout & Spacing**: Use an 8pt/4pt harmonic grid. Ensure comfortable breathing room around interactive elements.\n- **Typography Scale**: Maintain clear visual differentiation between section headings and body text (minimum 1.33x scale ratio). Ensure microcopy remains crisp and legible.\n- **Components & Buttons**: Primary calls-to-action must have distinct visual weight (solid filled background with high luminance contrast). Secondary actions should use outline or ghost styles. Align corner radii consistently across buttons and cards.\n- **Perceptual Contrast**: Ensure all text, icons, and status indicators are easily distinguishable from their backing surfaces.\n- **Visual Economy**: Remove visual clutter, heavy borders, and unnecessary decorative elements that compete with primary user tasks.`,
      instructions.trim() ? `## 6. User-Specified Design Instructions\nIn addition to resolving the audit findings above, incorporate these explicit user preferences:\n${instructions.trim()}` : "",
      `## ${instructions.trim() ? "7" : "6"}. Strict Design Constraints\n- **Preserve Product Purpose**: Do not alter the fundamental purpose or core business logic of the interface.\n- **Retain Essential Content**: Do not remove functional labels, navigation links, or data columns unless explicitly required.\n- **No Speculative Features**: Do not invent new features, tabs, or workflows not visible in the screenshot.\n- **Avoid Unrelated Churn**: Do not redesign unrelated interface components that have no audit findings unless necessary to maintain visual consistency.\n- **Preserve Constraints**: ${constraints}.`,
      `## ${instructions.trim() ? "8" : "7"}. Expected Output for Google Stitch\nGenerate a polished, production-ready interface that completely resolves the listed design issues while respecting all constraints.\n\n> **Handoff Note for Google Stitch**:\n> 1. Provide the original screenshot to Google Stitch as visual input.\n> 2. Paste this complete brief into Stitch's prompt window to guide the generative redesign.\n> 3. Export the resulting UI to Figma for final design system token alignment.`,
    ].filter(Boolean);

    return sections.join("\n\n");
  }

  async function generateStitchPrompt(instructionsOverride?: string) {
    if (!audit || selectedIssues.length === 0) {
      notify("Select at least one finding before generating a prompt.", "info");
      return;
    }
    setGeneratingPrompt(true);
    const instructions = instructionsOverride !== undefined ? instructionsOverride : userInstructions;
    try {
      const res = await fetch(`/api/backend/projects/${audit.projectId}/audits/${audit.id}/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_finding_ids: selectedIssues,
          user_instructions: instructions || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPrompt(data.content);
        setOriginalPromptContent(data.original_content || data.content);
        setPromptId(data.id);
        setPromptVersionNumber(data.version_number);
        setPromptVersions(data.versions || []);
        setPromptSelectedFindingIds([...selectedIssues]);
        setPromptOpen(true);
        setCopied(false);
        notify(`Generated Google Stitch brief (v${data.version_number}) with ${selectedIssues.length} findings.`, "success");
      } else {
        const fallback = makeStructuredPromptFallback(instructions);
        setPrompt(fallback);
        setOriginalPromptContent(fallback);
        setPromptVersionNumber(1);
        setPromptVersions([{
          id: "local-v1",
          version_number: 1,
          created_at: new Date().toISOString(),
          content: fallback,
          selected_finding_ids: [...selectedIssues],
        }]);
        setPromptSelectedFindingIds([...selectedIssues]);
        setPromptOpen(true);
        setCopied(false);
        notify("Generated client-side prompt brief.", "info");
      }
    } catch {
      const fallback = makeStructuredPromptFallback(instructions);
      setPrompt(fallback);
      setOriginalPromptContent(fallback);
      setPromptVersionNumber(1);
      setPromptVersions([{
        id: "local-v1",
        version_number: 1,
        created_at: new Date().toISOString(),
        content: fallback,
        selected_finding_ids: [...selectedIssues],
      }]);
      setPromptSelectedFindingIds([...selectedIssues]);
      setPromptOpen(true);
      setCopied(false);
      notify("Generated prompt brief.", "info");
    } finally {
      setGeneratingPrompt(false);
    }
  }

  async function handleManualEdit(newContent: string) {
    setPrompt(newContent);
    if (promptId && audit) {
      try {
        await fetch(`/api/backend/projects/${audit.projectId}/audits/${audit.id}/prompt/${promptId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: newContent }),
        });
      } catch {
        // silent fail for local edits
      }
    }
  }

  async function handleRestoreOriginal() {
    if (promptId && audit) {
      try {
        const res = await fetch(`/api/backend/projects/${audit.projectId}/audits/${audit.id}/prompt/${promptId}/restore-original`, {
          method: "POST",
        });
        if (res.ok) {
          const data = await res.json();
          setPrompt(data.content);
          notify("Restored original generated prompt.", "success");
          return;
        }
      } catch {
        // fallback to local state
      }
    }
    if (originalPromptContent) {
      setPrompt(originalPromptContent);
      notify("Restored original generated prompt.", "success");
    }
  }

  function handleSelectVersion(versionItem: PromptVersionItem) {
    setPrompt(versionItem.content);
    setPromptVersionNumber(versionItem.version_number);
    notify(`Loaded prompt version ${versionItem.version_number}.`, "info");
  }

  async function copyPrompt() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      notify("Prompt copied to clipboard.", "success");
    } catch {
      notify("Clipboard access was blocked. Select and copy the prompt text manually.", "error");
    }
  }

  if (!audit) {
    return <div className="page-stack"><EmptyState icon="warning" title="Audit not found" description="This audit is not available in the local demo workspace." action={<Button href="/history" variant="secondary">Go to audit history</Button>} /></div>;
  }

  const project = projects.find((item) => item.id === audit.projectId);
  const hasAiFindings = audit.issues.some((issue) => issue.isAiGenerated);

  return (
    <div className="page-stack audit-page">
      <div className="audit-heading">
        <div>
          <div className="breadcrumb"><Link href="/history">Audit history</Link><Icon name="chevron" size={14} /><span>{project?.name ?? "Project"}</span></div>
          <div className="audit-title-row">
            <h1>{audit.name}</h1>
            <Badge tone={hasAiFindings ? "blue" : audit.isDemo ? "demo" : "neutral"}>
              {hasAiFindings ? "AI Vision Audited" : audit.isDemo ? "Illustrative demo" : "Ready"}
            </Badge>
          </div>
          <p className="page-description">{audit.mode === "multi" ? "Multi-screen UX audit" : "Single-screen audit"} · {audit.screens.length} {audit.screens.length === 1 ? "screen" : "screens"} · {new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(audit.createdAt))}</p>
        </div>
        <div className="button-row">
          {audit.mode === "single" && (
            <Button
              variant="secondary"
              icon="spark"
              onClick={runAiAnalysis}
              disabled={analyzing || audit.screens.length === 0}
            >
              {analyzing ? "Analyzing visual design..." : hasAiFindings ? "Re-analyze with AI" : "Analyze with AI"}
            </Button>
          )}
          <Button onClick={() => generateStitchPrompt()} icon="spark" disabled={selectedCount === 0 || generatingPrompt}>
            {generatingPrompt ? "Generating brief..." : `Generate prompt for Google Stitch${selectedCount > 0 ? ` · ${selectedCount}` : ""}`}
          </Button>
        </div>
      </div>

      {analyzing && (
        <div className="audit-state-banner" role="status">
          <Icon name="clock" size={17} />
          <span><strong>Running AI vision analysis...</strong> Evaluating visual hierarchy, layout & spacing, typography, contrast indicators, and usability affordances.</span>
        </div>
      )}

      {!analyzing && hasAiFindings && (
        <div className="audit-state-banner audit-state-ready" role="status">
          <Icon name="check" size={17} />
          <span><strong>AI Vision Analysis Complete</strong> {audit.issues.length} design and usability findings identified across the screenshot. Bounding boxes are overlaid on the visual canvas.</span>
        </div>
      )}

      {!analyzing && !hasAiFindings && audit.isDemo && (
        <div className="demo-notice demo-notice-strong">
          <Icon name="info" size={17} />
          <span><strong>No AI analysis has run yet.</strong> {audit.screens.length > 0 ? "Click \"Analyze with AI\" above to inspect visual hierarchy, typography, and contrast." : "Visible findings are demonstration fixtures."}</span>
        </div>
      )}

      <div className={`audit-workspace ${audit.mode === "multi" ? "audit-workspace-multi" : ""}`}>
        <aside className="audit-screen-panel">
          <div className="panel-heading"><div><h2>Screens</h2><span>{audit.screens.length} {audit.screens.length === 1 ? "screen" : "screens"}</span></div><Badge>{audit.mode === "multi" ? "Multi" : "Single"}</Badge></div>
          <div className="screen-nav-list">
            {audit.screens.map((screen, index) => (
              <button type="button" className={`screen-nav-item ${screen.id === selectedScreenId ? "screen-nav-active" : ""}`} key={screen.id} onClick={() => setSelectedScreenId(screen.id)} draggable={audit.mode === "multi"} onDragStart={() => setDraggedScreen(index)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (draggedScreen !== null) reorderAuditScreens(audit.id, draggedScreen, index); setDraggedScreen(null); }}>
                <span className="screen-nav-thumb">{screen.previewUrl ? <Image src={screen.previewUrl} alt="" fill sizes="70px" unoptimized /> : <Icon name="image" size={17} />}</span>
                <span className="screen-nav-copy"><span><strong>{index + 1}.</strong> {screen.name}</span><small>{screen.fileName}</small></span>
                {audit.mode === "multi" && <Icon name="drag" size={17} />}
              </button>
            ))}
          </div>
          {audit.mode === "multi" && <div className="panel-footnote"><Icon name="info" size={14} />Sequence is user-provided; no transition was verified.</div>}
        </aside>

        <section className="audit-viewer-panel" aria-label="Screenshot viewer">
          <div className="panel-heading viewer-heading"><div><h2>{audit.mode === "multi" ? "Flow workspace" : "Screenshot"}</h2><span>{currentScreen?.name ?? "Select a screen"}</span></div><Badge tone={hasAiFindings ? "blue" : "demo"}>{hasAiFindings ? "Visual canvas" : "Demo state"}</Badge></div>
          {audit.mode === "multi" && <FlowOverview screens={audit.screens} selectedId={selectedScreenId} onSelect={setSelectedScreenId} />}
          {currentScreen ? (
            <ScreenshotViewer
              auditId={audit.id}
              screenId={currentScreen.id}
              screenName={currentScreen.name}
              previewUrl={currentScreen.previewUrl}
              issues={visibleIssues}
              selectedIssueIds={selectedIssues}
              activeIssueId={activeIssueId}
              onSelectIssue={setActiveIssueId}
            />
          ) : (
            <EmptyState icon="image" title="No screens available" description="Add screenshots through the new audit flow." action={<Button href="/audits/new" variant="secondary">Create an audit</Button>} />
          )}
          {audit.context?.goal && <div className="audit-goal"><strong>Stated journey goal</strong><p>{audit.context.goal}</p><small>Provided by the user · not independently verified</small></div>}
        </section>

        <aside className="audit-findings-panel">
          <div className="panel-heading findings-heading">
            <div>
              <h2>Findings</h2>
              <span>{audit.issues.length ? `${audit.issues.length} items` : "No results yet"}</span>
            </div>
          </div>

          {totalFindingsCount > 0 && (
            <div className="selection-summary-bar">
              <span>
                <strong>{selectedCount}</strong> of {totalFindingsCount} selected
                {selectedCount > 0 && (
                  <> · <span style={{ color: "var(--red)" }}>{criticalCount} Critical</span> · <span style={{ color: "var(--amber)" }}>{highCount} High</span></>
                )}
                {excludedCount > 0 && <> · {excludedCount} Excluded</>}
              </span>
              <div className="button-row">
                <button
                  type="button"
                  className="text-button"
                  onClick={selectAll}
                  disabled={selectedCount === totalFindingsCount}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={deselectAll}
                  disabled={selectedCount === 0}
                >
                  Deselect all
                </button>
              </div>
            </div>
          )}

          {totalFindingsCount > 0 && selectedCount === 0 && (
            <div className="demo-notice demo-notice-strong" style={{ margin: "8px 8px 0" }}>
              <Icon name="warning" size={15} />
              <span>No findings selected. Select at least one finding to generate a Google Stitch redesign brief.</span>
            </div>
          )}

          {audit.issues.length > 0 ? (
            <div className="findings-list">{audit.issues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} active={activeIssueId === issue.id} selected={selectedIssues.includes(issue.id)} onSelect={() => { setActiveIssueId(issue.id); const box = issue.boundingBoxes[0]; if (box) setSelectedScreenId(box.screenId); }} onToggle={() => toggleIssue(issue.id)} />
            ))}</div>
          ) : (
            <EmptyState
              icon="spark"
              title="No findings yet"
              description="Run single-screen AI vision analysis to detect visual hierarchy, typography, contrast indicators, and layout problems."
              action={
                audit.mode === "single" && audit.screens.length > 0 ? (
                  <Button icon="spark" onClick={runAiAnalysis} disabled={analyzing}>
                    {analyzing ? "Analyzing..." : "Analyze with AI"}
                  </Button>
                ) : audit.isDemo && auditId !== "demo-audit" ? (
                  <Button href="/audits/demo" variant="secondary">Explore labelled fixtures</Button>
                ) : undefined
              }
            />
          )}
          {audit.issues.length > 0 && (
            <div className="findings-bottom-note">
              <Icon name="info" size={15} />
              {hasAiFindings
                ? "AI findings are visual observations. Always verify potential contrast and accessibility findings in your code or design system."
                : "All items in this workspace are demonstration fixtures, not product analysis."}
            </div>
          )}
        </aside>
      </div>

      {promptOpen && (
        <PromptDialog
          content={prompt}
          originalContent={originalPromptContent}
          versionNumber={promptVersionNumber}
          versions={promptVersions}
          dialogRef={promptDialogRef}
          userInstructions={userInstructions}
          selectionChangedSincePrompt={selectionChangedSincePrompt}
          generating={generatingPrompt}
          copied={copied}
          onChangeContent={handleManualEdit}
          onChangeInstructions={setUserInstructions}
          onClose={() => setPromptOpen(false)}
          onCopy={copyPrompt}
          onRegenerate={() => generateStitchPrompt()}
          onRestoreOriginal={handleRestoreOriginal}
          onSelectVersion={handleSelectVersion}
        />
      )}
    </div>
  );
}
