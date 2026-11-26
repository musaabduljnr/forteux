"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useAppState } from "./app-state";
import { Icon } from "./icons";
import { Badge, Button } from "./ui";
import type { AuditMode, ProjectFull, UploadedScreen } from "@/lib/types";
import { formatFileSize } from "@/lib/demo-data";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_SCREENS = 12;

function makeScreen(file: File): UploadedScreen {
  const createObjectUrl = typeof URL.createObjectURL === "function"
    ? URL.createObjectURL(file)
    : undefined;
  return {
    id: `screen-${typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`}`,
    name: file.name.replace(/\.[^.]+$/, ""),
    fileName: file.name,
    mimeType: file.type || "image/png",
    fileSize: file.size,
    previewUrl: createObjectUrl,
    file,
  };
}

export function NewAuditForm() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const { projects: stateProjects, selectedProjectId, setSelectedProjectId, createAudit, notify } = useAppState();
  const [backendProjects, setBackendProjects] = useState<Array<{ id: string; name: string }>>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [mode, setMode] = useState<AuditMode>("single");
  const [screens, setScreens] = useState<UploadedScreen[]>([]);
  const [auditName, setAuditName] = useState("");
  const [product, setProduct] = useState("");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [constraints, setConstraints] = useState("");
  const [analysisFocus, setAnalysisFocus] = useState<"balanced" | "visual" | "usability_accessibility">("balanced");
  const [dragging, setDragging] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const savedMode = window.localStorage.getItem("forteux-default-audit-mode");
    if (savedMode === "single" || savedMode === "multi") setMode(savedMode);
    const projectFromQuery = new URLSearchParams(window.location.search).get("project");
    const supabase = createClient();

    async function loadAuthAndProjects() {
      const { data } = await supabase.auth.getUser();
      const authed = Boolean(data.user);
      setIsAuthenticated(authed);
      if (!authed) {
        setLoadingProjects(false);
        return;
      }
      try {
        const res = await fetch("/api/backend/projects");
        if (res.ok) {
          const raw: unknown = await res.json();
          const items = (Array.isArray(raw) ? raw : ((raw as { items?: ProjectFull[] })?.items ?? [])) as ProjectFull[];
          const mapped = items.map((p) => ({ id: p.id, name: p.name }));
          setBackendProjects(mapped);
          if (projectFromQuery && mapped.some((p) => p.id === projectFromQuery)) {
            setSelectedProjectId(projectFromQuery);
          } else if (mapped.length > 0 && !mapped.some((p) => p.id === selectedProjectId)) {
            setSelectedProjectId(mapped[0].id);
          }
        }
      } catch {
        // Keep empty list; user will see project creation prompt
      } finally {
        setLoadingProjects(false);
      }
    }

    void loadAuthAndProjects();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const projects = isAuthenticated ? backendProjects : stateProjects;

  function receiveFiles(files: FileList | File[]) {
    const incoming = Array.from(files);
    const accepted: UploadedScreen[] = [];
    for (const file of incoming) {
      const validImage = ["image/png", "image/jpeg"].includes(file.type)
        || /\.(png|jpe?g)$/i.test(file.name);
      if (!validImage) {
        notify(`${file.name}: choose a PNG or JPEG screenshot.`, "error");
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        notify(`${file.name}: the maximum screenshot size is 10 MB.`, "error");
        continue;
      }
      accepted.push(makeScreen(file));
    }

    if (mode === "single") {
      if (accepted.length > 1) notify("Single-screen mode keeps one image. Only the first valid file was added.", "info");
      if (accepted.length > 0) {
        screens.forEach((screen) => screen.previewUrl && URL.revokeObjectURL(screen.previewUrl));
        accepted.slice(1).forEach((screen) => screen.previewUrl && URL.revokeObjectURL(screen.previewUrl));
        setScreens(accepted.slice(0, 1));
      }
    } else {
      const remaining = Math.max(0, MAX_SCREENS - screens.length);
      if (accepted.length > remaining) notify(`A multi-screen audit supports up to ${MAX_SCREENS} screenshots.`, "info");
      accepted.slice(remaining).forEach((screen) => screen.previewUrl && URL.revokeObjectURL(screen.previewUrl));
      setScreens([...screens, ...accepted.slice(0, remaining)]);
    }
    if (inputRef.current) inputRef.current.value = "";
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.currentTarget.files) receiveFiles(event.currentTarget.files);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    receiveFiles(event.dataTransfer.files);
  }

  function removeScreen(id: string) {
    const removed = screens.find((screen) => screen.id === id);
    if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl);
    setScreens((current) => current.filter((screen) => screen.id !== id));
  }

  function moveScreen(from: number, to: number) {
    setScreens((current) => {
      if (from < 0 || from >= current.length || to < 0 || to >= current.length) return current;
      const next = [...current];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }

  async function submitAudit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (screens.length === 0) {
      notify("Add a screenshot before continuing.", "error");
      return;
    }
    if (mode === "multi" && screens.length < 2) {
      notify("Add at least two screenshots for a multi-screen audit.", "error");
      return;
    }
    const projectId = selectedProjectId || projects[0]?.id;
    if (!projectId) {
      notify("Create a project before starting an audit.", "error");
      return;
    }
    const name = auditName.trim() || screens[0].name || "Untitled audit";

    setSubmitting(true);
    try {
      if (isAuthenticated) {
        try {
          // 1. Create audit in backend
          const auditRes = await fetch(`/api/backend/projects/${projectId}/audits`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name,
              mode,
              context: { product, goal, audience, constraints },
            }),
          });

          if (auditRes.ok) {
            const auditData = await auditRes.json();
            const backendAuditId = auditData.id;

            // 2. Upload all selected screens
            for (let idx = 0; idx < screens.length; idx += 1) {
              const screen = screens[idx];
              if (!screen?.file) continue;
              const uploadRes = await fetch(`/api/backend/projects/${projectId}/uploads`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "Idempotency-Key": `upload-${Date.now()}-${idx}-${Math.random().toString(16).slice(2)}`,
                },
                body: JSON.stringify({
                  filename: screen.fileName,
                  content_type: screen.mimeType,
                  size: screen.fileSize,
                }),
              });

              if (!uploadRes.ok) {
                throw new Error(`Failed to prepare upload for ${screen.fileName} (HTTP ${uploadRes.status})`);
              }

              const uploadData = await uploadRes.json();
              const { upload_url, asset_id, required_headers } = uploadData;

              const putHeaders: Record<string, string> = {
                "Content-Type": screen.mimeType,
                ...(required_headers || {}),
              };
              const putRes = await fetch(upload_url, {
                method: "PUT",
                headers: putHeaders,
                body: screen.file,
              });
              if (!putRes.ok) {
                throw new Error(`Failed to upload ${screen.fileName} to storage (HTTP ${putRes.status})`);
              }

              const completeRes = await fetch(`/api/backend/projects/${projectId}/assets/${asset_id}/complete`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
              });
              if (!completeRes.ok) {
                throw new Error(`Failed to verify ${screen.fileName} (HTTP ${completeRes.status})`);
              }

              const attachRes = await fetch(`/api/backend/projects/${projectId}/audits/${backendAuditId}/screens`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  screen_asset_id: asset_id,
                  sequence_index: idx,
                  screen_label: screen.name,
                }),
              });
              if (!attachRes.ok) {
                throw new Error(`Failed to attach ${screen.fileName} to audit (HTTP ${attachRes.status})`);
              }

              screen.assetId = asset_id;
            }

            createAudit({
              id: backendAuditId,
              projectId,
              name,
              mode,
              screens,
              context: { product, goal, audience, constraints },
              analysisFocus,
              isDemo: false,
            });

            notify("Screenshot verified and attached. Ready for AI audit.", "success");
            router.push(`/audits/${backendAuditId}`);
            return;
          }
          const errBody = await auditRes.json().catch(() => ({}));
          notify(errBody?.detail?.message || errBody?.error?.message || `Could not create audit (HTTP ${auditRes.status}).`, "error");
          return;
        } catch (err) {
          notify(err instanceof Error ? err.message : "Upload failed. Please try again.", "error");
          return;
        }
      }

      // Fallback demo state
      const id = createAudit({
        projectId,
        name,
        mode,
        screens,
        context: { product, goal, audience, constraints },
        analysisFocus,
        isDemo: true,
      });
      notify("Local audit created.", "info");
      router.push(`/audits/${id}`);
    } finally {
      setSubmitting(false);
    }
  }

  const canStart = !submitting && screens.length > 0 && (mode === "single" || screens.length > 1) && projects.length > 0;

  return (
    <form className="new-audit-layout" onSubmit={submitAudit}>
      <div className="new-audit-main">
        <div className="mode-selector" role="radiogroup" aria-label="Choose audit mode" onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
          event.preventDefault();
          const nextMode = mode === "single" ? "multi" : "single";
          setMode(nextMode);
          event.currentTarget.querySelector<HTMLButtonElement>(`[data-mode="${nextMode}"]`)?.focus();
          if (nextMode === "single") {
            screens.slice(1).forEach((screen) => screen.previewUrl && URL.revokeObjectURL(screen.previewUrl));
            setScreens(screens.slice(0, 1));
          }
        }}>
          <button type="button" data-mode="single" tabIndex={mode === "single" ? 0 : -1} className={`mode-card ${mode === "single" ? "mode-card-selected" : ""}`} onClick={() => { setMode("single"); screens.slice(1).forEach((screen) => screen.previewUrl && URL.revokeObjectURL(screen.previewUrl)); setScreens(screens.slice(0, 1)); }} role="radio" aria-checked={mode === "single"}>
            <span className="mode-icon"><Icon name="image" size={21} /></span>
            <span className="mode-copy"><strong>Single screen</strong><small>Review one interface screenshot for visible design opportunities.</small><span className="mode-meta">1 screenshot</span></span>
            <span className={`radio-indicator ${mode === "single" ? "radio-selected" : ""}`} />
          </button>
          <button type="button" data-mode="multi" tabIndex={mode === "multi" ? 0 : -1} className={`mode-card ${mode === "multi" ? "mode-card-selected" : ""}`} onClick={() => setMode("multi")} role="radio" aria-checked={mode === "multi"}>
            <span className="mode-icon mode-icon-purple"><Icon name="layers" size={21} /></span>
            <span className="mode-copy"><strong>Multi-screen journey</strong><small>Compare an ordered set of screens and explore consistency across a journey.</small><span className="mode-meta">2–12 screenshots</span></span>
            <span className={`radio-indicator ${mode === "multi" ? "radio-selected" : ""}`} />
          </button>
        </div>

        <section className="form-section">
          <div className="section-title">
            <div><h2>{mode === "single" ? "Add a screenshot" : "Add your screens"}</h2><p>{mode === "single" ? "Choose a clear screenshot of the interface you want to review." : "Add screens, then arrange them in the intended user journey order."}</p></div>
            {mode === "multi" && <Badge tone="blue">{screens.length} / {MAX_SCREENS}</Badge>}
          </div>
          {screens.length === 0 && (
            <div className={`upload-dropzone ${dragging ? "upload-dropzone-active" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
              <span className="upload-icon"><Icon name="upload" size={22} /></span>
              <strong>Drop your screenshot{mode === "multi" ? "s" : ""} here</strong>
              <span>or <button type="button" className="text-button" onClick={() => inputRef.current?.click()}>browse files</button></span>
              <small>PNG or JPG · Up to 10 MB per image{mode === "multi" ? " · 12 screens maximum" : ""}</small>
              <input ref={inputRef} className="visually-hidden" type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" multiple={mode === "multi"} onChange={onFileChange} aria-label="Choose screenshot files" />
            </div>
          )}
          {screens.length > 0 && (
            <div className="screen-upload-list">
              {screens.map((screen, index) => (
                <article key={screen.id} className={`screen-upload-card ${dragIndex === index ? "screen-upload-dragging" : ""}`} draggable={mode === "multi"} onDragStart={() => setDragIndex(index)} onDragEnd={() => setDragIndex(null)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (dragIndex !== null) moveScreen(dragIndex, index); setDragIndex(null); }}>
                  <div className="screen-thumb">
                    {screen.previewUrl && <Image src={screen.previewUrl} alt={`Preview of ${screen.name}`} fill sizes="112px" unoptimized />}
                  </div>
                  <div className="screen-upload-details">
                    <label className="screen-name-label" htmlFor={`screen-name-${screen.id}`}>Screen name</label>
                    <input id={`screen-name-${screen.id}`} value={screen.name} onChange={(event) => setScreens((current) => current.map((item) => item.id === screen.id ? { ...item, name: event.target.value } : item))} aria-label={`Rename screen ${index + 1}`} />
                    <small>{mode === "multi" ? `Screen ${index + 1} · ` : ""}{screen.fileName} · {formatFileSize(screen.fileSize)}</small>
                  </div>
                  {mode === "multi" && <span className="icon-button drag-handle" aria-hidden="true" title="Drag to reorder"><Icon name="drag" /></span>}
                  {mode === "multi" && <div className="sequence-buttons"><button type="button" className="icon-button" disabled={index === 0} onClick={() => moveScreen(index, index - 1)} aria-label={`Move ${screen.name} earlier`}><span aria-hidden="true">↑</span></button><button type="button" className="icon-button" disabled={index === screens.length - 1} onClick={() => moveScreen(index, index + 1)} aria-label={`Move ${screen.name} later`}><span aria-hidden="true">↓</span></button></div>}
                  <button type="button" className="icon-button remove-screen" onClick={() => removeScreen(screen.id)} aria-label={`Remove ${screen.name}`}><Icon name="close" size={17} /></button>
                </article>
              ))}
              <div className="upload-list-actions">
                <button type="button" className="button button-secondary button-small" onClick={() => inputRef.current?.click()}><Icon name="plus" size={16} />{mode === "single" ? "Replace screenshot" : "Add screens"}</button>
                <input ref={inputRef} className="visually-hidden" type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" multiple={mode === "multi"} onChange={onFileChange} aria-label={mode === "single" ? "Replace screenshot" : "Add more screenshots"} />
                <span className="helper-text">{isAuthenticated ? "Screenshots are uploaded securely to your workspace storage." : "Sign in to upload screenshots to your workspace."}</span>
              </div>
            </div>
          )}
        </section>

        <section className="form-section">
          <div className="section-title"><div><h2>Audit details</h2><p>Context helps reviewers understand the intended experience.</p></div><span className="optional-label">Optional</span></div>
          <div className="form-grid">
            <label className="form-field"><span>Audit or screen name</span><input value={auditName} onChange={(event) => setAuditName(event.target.value)} placeholder="e.g. New customer checkout" /></label>
            <label className="form-field">
              <span>Project</span>
              <select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)} disabled={loadingProjects}>
                {loadingProjects ? <option value="">Loading projects…</option> : projects.length === 0 ? <option value="">No projects available</option> : null}
                {projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}
              </select>
              {!loadingProjects && projects.length === 0 && (
                <small>
                  <Link className="inline-link" href="/projects">Create a project first <Icon name="arrow" size={14} /></Link>
                </small>
              )}
            </label>
            <label className="form-field"><span>Product context</span><input value={product} onChange={(event) => setProduct(event.target.value)} placeholder="What does this product help people do?" /></label>
            <label className="form-field"><span>Intended user or audience</span><input value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="Who is this experience for?" /></label>
            <label className="form-field form-field-wide"><span>Review focus</span><select value={analysisFocus} onChange={(event) => setAnalysisFocus(event.target.value as typeof analysisFocus)}><option value="balanced">Balanced review</option><option value="visual">Visual design and consistency</option><option value="usability_accessibility">Usability and visible accessibility cues</option></select><small>These settings tailor the audit focus for your uploaded screens.</small></label>
            <label className="form-field form-field-wide"><span>{mode === "single" ? "Screen goal" : "Journey goal"}</span><textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={3} placeholder={mode === "single" ? "What should a person be able to accomplish on this screen?" : "What should a person be able to accomplish across this sequence?"} /></label>
            <label className="form-field form-field-wide"><span>Design constraints</span><textarea value={constraints} onChange={(event) => setConstraints(event.target.value)} rows={2} placeholder="Brand, platform, or content requirements to preserve" /></label>
          </div>
        </section>
      </div>

      <aside className="new-audit-aside">
        <div className="aside-card">
          <span className="aside-card-icon"><Icon name={mode === "single" ? "image" : "layers"} /></span>
          <h3>{mode === "single" ? "Single screen audit" : "Multi-screen UX audit"}</h3>
          <p>{mode === "single" ? "A focused review of one screen’s visual hierarchy, clarity, and visible usability cues." : "Per-screen reviews plus a separate comparison of patterns and transitions across your ordered sequence."}</p>
          <div className="aside-divider" />
          <strong>Before you continue</strong>
          <ul className="check-list">
            <li><Icon name="check" size={15} />Use a clear, full-screen screenshot</li>
            <li><Icon name="check" size={15} />Remove private or sensitive information</li>
            {mode === "multi" && <li><Icon name="check" size={15} />Set the intended order of your screens</li>}
          </ul>
          <div className="privacy-note"><Icon name="info" size={17} /><span>Screenshots are stored privately in your project workspace.</span></div>
        </div>
        <div className="aside-card compact-aside-card">
          <strong>What happens next?</strong>
          <p>Your screenshots are uploaded to your project workspace so you can run analysis, inspect findings, and export reports.</p>
        </div>
        <Button type="submit" className="start-audit-button" icon="arrow" disabled={!canStart}>
          {submitting ? "Uploading screenshot..." : isAuthenticated ? "Upload & create audit" : "Sign in to upload"}
        </Button>
        <span className="start-audit-caption">
          {mode === "multi" && screens.length < 2
            ? "Add at least two screens to continue."
            : screens.length === 0
              ? "Add a screenshot to continue."
              : projects.length === 0
                ? "Create a project to upload and start an audit."
                : "Ready to upload and create your audit."}
        </span>
      </aside>
    </form>
  );
}
