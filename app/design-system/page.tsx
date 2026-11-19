"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, PageHeader, SectionTitle, SeverityBadge } from "@/components/ui";
import type {
  DesignSystemReport,
  ProposedDesignToken,
} from "@/lib/types";

export default function DesignSystemPage() {
  const { projects, audits, selectedProjectId, setSelectedProjectId } = useAppState();

  // Selected audit for design system analysis
  const projectAudits = useMemo(() => {
    return audits.filter((a) => a.projectId === selectedProjectId);
  }, [audits, selectedProjectId]);

  const [selectedAuditId, setSelectedAuditId] = useState<string>("");

  useEffect(() => {
    if (projectAudits.length > 0 && (!selectedAuditId || !projectAudits.some((a) => a.id === selectedAuditId))) {
      setSelectedAuditId(projectAudits[0].id);
    }
  }, [projectAudits, selectedAuditId]);

  // Design system report state
  const [report, setReport] = useState<DesignSystemReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active view tab
  const [activeTab, setActiveTab] = useState<
    "overview" | "colors" | "typography" | "surfaces" | "components" | "inconsistencies" | "tokens"
  >("overview");

  // Filter & Search states
  const [tokenSearch, setTokenSearch] = useState("");
  const [tokenCategoryFilter, setTokenCategoryFilter] = useState("all");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // Modal states
  const [stitchModalOpen, setStitchModalOpen] = useState(false);
  const [exportModalType, setExportModalType] = useState<"json" | "css" | null>(null);
  const [exportContent, setExportContent] = useState<string>("");
  const [stitchCustomInstructions, setStitchCustomInstructions] = useState("");
  const [generatingStitch, setGeneratingStitch] = useState(false);
  const [stitchPromptText, setStitchPromptText] = useState<string>("");
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  // Fetch existing design system for selected audit
  const fetchDesignSystem = useCallback(async () => {
    if (!selectedProjectId || !selectedAuditId) {
      setReport(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/backend/projects/${selectedProjectId}/audits/${selectedAuditId}/design-system`);
      if (res.ok) {
        const data: DesignSystemReport = await res.json();
        setReport(data);
        setStitchPromptText(data.stitch_prompt || "");
      } else if (res.status === 404) {
        setReport(null);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData?.error?.message || "Failed to load design system");
      }
    } catch {
      setError("Network error connecting to design system service");
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId, selectedAuditId]);

  useEffect(() => {
    fetchDesignSystem();
  }, [fetchDesignSystem]);

  // Trigger design system extraction
  const handleExtract = async () => {
    if (!selectedProjectId || !selectedAuditId) return;
    setExtracting(true);
    setError(null);
    try {
      const res = await fetch(`/api/backend/projects/${selectedProjectId}/audits/${selectedAuditId}/design-system/extract`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.error?.message || "Extraction failed");
      }
      const data: DesignSystemReport = await res.json();
      setReport(data);
      setStitchPromptText(data.stitch_prompt || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Design system extraction failed");
    } finally {
      setExtracting(false);
    }
  };

  // Open Export Modal (JSON or CSS)
  const handleOpenExport = async (type: "json" | "css") => {
    if (!selectedProjectId || !selectedAuditId) return;
    try {
      const res = await fetch(`/api/backend/projects/${selectedProjectId}/audits/${selectedAuditId}/design-system/export/${type}`);
      if (res.ok) {
        const data = await res.json();
        const content = type === "css" ? data.css_content : JSON.stringify(data, null, 2);
        setExportContent(content);
        setExportModalType(type);
      }
    } catch (err) {
      console.error("Export fetch error:", err);
    }
  };

  // Re-generate custom Google Stitch prompt
  const handleRegenerateStitchPrompt = async () => {
    if (!selectedProjectId || !selectedAuditId) return;
    setGeneratingStitch(true);
    try {
      const res = await fetch(`/api/backend/projects/${selectedProjectId}/audits/${selectedAuditId}/design-system/stitch-prompt`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          custom_instructions: stitchCustomInstructions,
          include_inconsistencies: true,
          include_tokens: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStitchPromptText(data.prompt);
      }
    } catch (err) {
      console.error("Stitch prompt regeneration failed:", err);
    } finally {
      setGeneratingStitch(false);
    }
  };

  const copyToClipboard = (text: string, identifier: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(identifier);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  // Filtered tokens
  const filteredTokens = useMemo(() => {
    if (!report?.tokens) return [];
    return report.tokens.filter((t) => {
      const matchesSearch = t.name.toLowerCase().includes(tokenSearch.toLowerCase()) || t.value.toLowerCase().includes(tokenSearch.toLowerCase());
      const matchesCat = tokenCategoryFilter === "all" || t.category.toLowerCase() === tokenCategoryFilter.toLowerCase();
      return matchesSearch && matchesCat;
    });
  }, [report?.tokens, tokenSearch, tokenCategoryFilter]);

  // Score Qualitative Rating Tier
  const scoreTier = useMemo(() => {
    const score = report?.consistency_score;
    if (score === null || score === undefined) return { label: "Pending", tone: "neutral" as const };
    if (score >= 90) return { label: "Exemplary", tone: "success" as const };
    if (score >= 75) return { label: "Strong", tone: "blue" as const };
    if (score >= 60) return { label: "Moderate", tone: "warning" as const };
    return { label: "Fragmented", tone: "danger" as const };
  }, [report?.consistency_score]);

  return (
    <div className="page-stack">
      {/* Page Header with Pickers & Action Controls */}
      <PageHeader
        eyebrow="Intelligence"
        title="Design System & Consistency"
        description="Extract recurring visual tokens, repeated component patterns, and cross-screen consistency metrics."
        action={
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <label className="project-picker">
              <span>Project</span>
              <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
                {projects.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="project-picker">
              <span>Audit</span>
              <select value={selectedAuditId} onChange={(e) => setSelectedAuditId(e.target.value)} disabled={projectAudits.length === 0}>
                {projectAudits.length === 0 ? (
                  <option value="">No audits</option>
                ) : (
                  projectAudits.map((a) => (
                    <option value={a.id} key={a.id}>
                      {a.name} ({a.mode})
                    </option>
                  ))
                )}
              </select>
            </label>

            <Button variant="primary" onClick={handleExtract} disabled={extracting || !selectedAuditId}>
              <Icon name="spark" size={15} />
              {extracting ? "Extracting..." : report ? "Re-Extract" : "Extract Design System"}
            </Button>

            {report && (
              <>
                <Button variant="secondary" onClick={() => handleOpenExport("css")}>
                  <Icon name="code" size={14} /> CSS
                </Button>
                <Button variant="secondary" onClick={() => handleOpenExport("json")}>
                  <Icon name="download" size={14} /> JSON
                </Button>
                <Button variant="primary" onClick={() => setStitchModalOpen(true)}>
                  <Icon name="file" size={14} /> Stitch Brief
                </Button>
              </>
            )}
          </div>
        }
      />

      {error && (
        <div className="demo-notice" style={{ background: "#fef2f2", color: "#991b1b", borderColor: "#fecaca" }}>
          <Icon name="warning" size={16} />
          <span>{error}</span>
        </div>
      )}

      {loading && !report ? (
        <div className="empty-state" style={{ padding: "60px 0" }}>
          <p>Loading design system intelligence...</p>
        </div>
      ) : !report ? (
        <EmptyState
          icon="layers"
          title="No Design System Extracted Yet"
          description="Select an audit containing uploaded screenshots and run 'Extract Design System' to discover colors, typography, spacing, component patterns, and consistency issues."
          action={
            <Button variant="primary" onClick={handleExtract} disabled={extracting || !selectedAuditId}>
              <Icon name="spark" size={15} />
              {extracting ? "Analyzing Screenshots..." : "Extract Design System"}
            </Button>
          }
        />
      ) : (
        <>
          {/* Executive Overview Banner */}
          <div className="panel" style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "24px", alignItems: "center" }}>
            <div style={{ textAlign: "center", borderRight: "1px solid #e2e8f0", paddingRight: "16px" }}>
              <div style={{ fontSize: "11px", textTransform: "uppercase", fontWeight: 700, color: "#64748b", marginBottom: "4px" }}>
                Consistency Score
              </div>
              <div style={{ fontSize: "40px", fontWeight: 800, color: "#0f172a", lineHeight: 1 }}>
                {report.consistency_score ?? 100}
                <span style={{ fontSize: "16px", color: "#94a3b8" }}>/100</span>
              </div>
              <div style={{ marginTop: "8px" }}>
                <Badge tone={scoreTier.tone}>{scoreTier.label}</Badge>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                <Badge tone="neutral">{report.screens_analyzed} screens analyzed</Badge>
                <Badge tone="blue">{Math.round((report.extraction_coverage ?? 0) * 100)}% coverage</Badge>
                <Badge tone="neutral">{Math.round((report.confidence ?? 0.9) * 100)}% confidence</Badge>
                <Badge tone="success">{report.tokens.length} tokens generated</Badge>
                {report.consistency_issues.length > 0 && (
                  <Badge tone="warning">{report.consistency_issues.length} inconsistencies</Badge>
                )}
              </div>
              <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#475569", lineHeight: 1.5 }}>
                {report.summary}
              </p>
            </div>
          </div>

          {/* Category Score Breakdown Badges */}
          {report.score_breakdown && Object.keys(report.score_breakdown).length > 0 && (
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              {Object.entries(report.score_breakdown).map(([cat, catScore]) => (
                <div
                  key={cat}
                  style={{
                    padding: "6px 12px",
                    background: "#ffffff",
                    border: "1px solid #e2e8f0",
                    borderRadius: "6px",
                    fontSize: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span style={{ textTransform: "capitalize", fontWeight: 600, color: "#475569" }}>{cat}:</span>
                  <span style={{ fontWeight: 700, color: catScore >= 90 ? "#16a34a" : catScore >= 75 ? "#2563eb" : "#d97706" }}>
                    {catScore}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Section Navigation Tabs */}
          <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #e2e8f0", paddingBottom: "8px", marginTop: "8px" }}>
            {[
              { id: "overview", label: "Overview", icon: "dashboard" as const },
              { id: "colors", label: `Colors (${report.color_palette.length})`, icon: "layers" as const },
              { id: "typography", label: `Typography (${report.typography.length})`, icon: "file" as const },
              { id: "surfaces", label: "Spacing & Shapes", icon: "grid" as const },
              { id: "components", label: `Components (${report.components.length})`, icon: "folder" as const },
              { id: "inconsistencies", label: `Inconsistencies (${report.consistency_issues.length})`, icon: "warning" as const },
              { id: "tokens", label: `Design Tokens (${report.tokens.length})`, icon: "code" as const },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: "none",
                  background: activeTab === tab.id ? "#0f172a" : "transparent",
                  color: activeTab === tab.id ? "#ffffff" : "#64748b",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Icon name={tab.icon} size={14} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="card" style={{ padding: "16px" }}>
                <SectionTitle title="Key Recommendations" description="Actionable directives to harmonize the design system." />
                <ol style={{ paddingLeft: "18px", fontSize: "13px", color: "#334155", lineHeight: 1.6, marginTop: "8px" }}>
                  {report.recommendations.map((rec, i) => (
                    <li key={i} style={{ marginBottom: "6px" }}>
                      {rec}
                    </li>
                  ))}
                </ol>
              </div>

              <div className="card" style={{ padding: "16px" }}>
                <SectionTitle title="Evidence Limitations" description="Boundaries of static screenshot computer vision." />
                <ul style={{ paddingLeft: "18px", fontSize: "13px", color: "#64748b", lineHeight: 1.6, marginTop: "8px" }}>
                  {report.limitations.map((lim, i) => (
                    <li key={i} style={{ marginBottom: "6px" }}>
                      {lim}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* TAB 2: COLOUR PALETTE */}
          {activeTab === "colors" && (
            <div>
              <SectionTitle title="Extracted Colour Palette" description="Measured HEX values, semantic roles, and recurrence across screens." />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "12px", marginTop: "12px" }}>
                {report.color_palette.map((c, idx) => (
                  <div
                    key={idx}
                    className="card"
                    style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px" }}
                  >
                    <div
                      style={{
                        height: "56px",
                        borderRadius: "6px",
                        background: c.hex,
                        border: "1px solid rgba(0,0,0,0.1)",
                        boxShadow: "inset 0 1px 2px rgba(0,0,0,0.06)",
                      }}
                    />
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "#1e293b" }}>{c.semantic_name}</span>
                      <Badge tone={c.evidence === "observed" ? "success" : "neutral"}>{c.evidence}</Badge>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <code style={{ fontSize: "12px", background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px" }}>
                        {c.hex}
                      </code>
                      <button
                        onClick={() => copyToClipboard(c.hex, `hex-${idx}`)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#2563eb",
                          fontSize: "11px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {copiedToken === `hex-${idx}` ? "Copied!" : "Copy"}
                      </button>
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b" }}>
                      Category: <span style={{ textTransform: "capitalize", fontWeight: 600 }}>{c.category}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: TYPOGRAPHY */}
          {activeTab === "typography" && (
            <div>
              <SectionTitle title="Typography Scale & Hierarchy" description="Identified heading, body, and label styles with size estimates." />
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
                {report.typography.map((t, idx) => (
                  <div key={idx} className="card" style={{ padding: "16px", display: "grid", gridTemplateColumns: "220px 1fr 140px", gap: "16px", alignItems: "center" }}>
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 700, color: "#1e293b" }}>{t.style_name}</div>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        Hierarchy: <strong style={{ textTransform: "uppercase" }}>{t.text_hierarchy}</strong>
                      </div>
                    </div>
                    <div style={{ fontSize: "14px", color: "#334155" }}>
                      Approx: <strong>{t.font_size_approx}</strong> • Weight: <strong>{t.font_weight_category}</strong>
                      {t.line_height_estimate && ` • Line-height: ${t.line_height_estimate}`}
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <Badge tone={t.evidence === "observed" ? "success" : "neutral"}>{t.evidence}</Badge>
                      <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "4px" }}>
                        {Math.round(t.confidence * 100)}% confidence
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: SPACING & SURFACES */}
          {activeTab === "surfaces" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="card" style={{ padding: "16px" }}>
                <SectionTitle title="Shapes & Surface Treatments" description="Border radii, card curves, elevation, and shadows." />
                <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Border Radii:</span>
                    <div style={{ display: "flex", gap: "8px", marginTop: "4px", flexWrap: "wrap" }}>
                      {report.shapes_surfaces.border_radii.map((r, i) => (
                        <span key={i} style={{ padding: "4px 8px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "4px", fontSize: "12px" }}>
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                  {report.shapes_surfaces.borders && (
                    <div>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Borders:</span>
                      <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#334155" }}>{report.shapes_surfaces.borders}</p>
                    </div>
                  )}
                  {report.shapes_surfaces.card_shapes && (
                    <div>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Card Treatment:</span>
                      <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#334155" }}>{report.shapes_surfaces.card_shapes}</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="card" style={{ padding: "16px" }}>
                <SectionTitle title="Spacing & Layout Patterns" description="Content padding, section gaps, and component rhythm." />
                <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  {report.spacing_layout.card_padding && (
                    <div>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Card Internal Padding:</span>
                      <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#334155" }}>{report.spacing_layout.card_padding}</p>
                    </div>
                  )}
                  {report.spacing_layout.component_gaps && (
                    <div>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Component Gaps:</span>
                      <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#334155" }}>{report.spacing_layout.component_gaps}</p>
                    </div>
                  )}
                  {report.spacing_layout.page_margins && (
                    <div>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Page Margins:</span>
                      <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#334155" }}>{report.spacing_layout.page_margins}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: COMPONENTS */}
          {activeTab === "components" && (
            <div>
              <SectionTitle title="Reusable Component Patterns" description="Identified buttons, inputs, cards, and repeated interface structures." />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "14px", marginTop: "12px" }}>
                {report.components.map((comp, idx) => (
                  <div key={idx} className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>{comp.component_category}</span>
                      <Badge tone="blue">{comp.observed_occurrences} observed</Badge>
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "#475569" }}>{comp.visual_description}</p>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                      <strong>Characteristics:</strong> {comp.common_characteristics}
                    </div>
                    {comp.variations.length > 0 && (
                      <div style={{ fontSize: "11px", color: "#b45309", background: "#fffbeb", padding: "6px", borderRadius: "4px" }}>
                        <strong>Variations:</strong> {comp.variations.join("; ")}
                      </div>
                    )}
                    <div style={{ fontSize: "11px", color: "#1e3a8a", background: "#eff6ff", padding: "6px", borderRadius: "4px", marginTop: "4px" }}>
                      <strong>Target Spec:</strong> {comp.recommended_component_spec}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: INCONSISTENCIES */}
          {activeTab === "inconsistencies" && (
            <div>
              <SectionTitle title="Cross-Screen Visual Inconsistencies" description="Detected styling conflicts that diverge across screens." />
              {report.consistency_issues.length === 0 ? (
                <div className="empty-state" style={{ padding: "40px 0" }}>
                  <Icon name="check" size={24} style={{ color: "#16a34a", marginBottom: "8px" }} />
                  <p>No cross-screen design inconsistencies detected! High visual uniformity observed.</p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
                  {report.consistency_issues.map((iss, idx) => (
                    <div key={idx} className="card" style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                          <SeverityBadge severity={iss.severity} />
                          <span style={{ fontSize: "14px", fontWeight: 700, color: "#1e293b" }}>{iss.title}</span>
                          <span style={{ fontSize: "11px", color: "#64748b", textTransform: "capitalize" }}>({iss.category})</span>
                        </div>
                        {iss.affected_screens.length > 0 && (
                          <span style={{ fontSize: "11px", color: "#64748b" }}>
                            Screens: {iss.affected_screens.join(", ")}
                          </span>
                        )}
                      </div>
                      <p style={{ margin: "2px 0", fontSize: "12px", color: "#475569" }}>{iss.description}</p>
                      <div style={{ fontSize: "11px", color: "#15803d", background: "#f0fdf4", padding: "6px 8px", borderRadius: "4px", marginTop: "4px" }}>
                        <strong>Recommended Correction:</strong> {iss.recommended_fix}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 7: DESIGN TOKENS TABLE */}
          {activeTab === "tokens" && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
                <SectionTitle title="Proposed Design Tokens" description="Unified token architecture based on extracted visual foundations." />
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Search tokens..."
                    value={tokenSearch}
                    onChange={(e) => setTokenSearch(e.target.value)}
                    style={{ fontSize: "12px", padding: "6px 10px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                  />
                  <select
                    value={tokenCategoryFilter}
                    onChange={(e) => setTokenCategoryFilter(e.target.value)}
                    style={{ fontSize: "12px", padding: "6px 10px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                  >
                    <option value="all">All Categories</option>
                    <option value="color">Colors</option>
                    <option value="typography">Typography</option>
                    <option value="spacing">Spacing</option>
                    <option value="radius">Radius</option>
                    <option value="shadow">Shadows</option>
                  </select>
                  <Button variant="secondary" onClick={() => copyToClipboard(export_tokens_to_css_client(report.tokens), "all-tokens")}>
                    {copiedToken === "all-tokens" ? "Copied All!" : "Copy All CSS"}
                  </Button>
                </div>
              </div>

              <div className="card" style={{ overflow: "hidden", padding: 0 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                  <thead>
                    <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0", color: "#64748b" }}>
                      <th style={{ padding: "10px 14px" }}>Token Name</th>
                      <th style={{ padding: "10px 14px" }}>Value</th>
                      <th style={{ padding: "10px 14px" }}>Category</th>
                      <th style={{ padding: "10px 14px" }}>Evidence</th>
                      <th style={{ padding: "10px 14px", textAlign: "right" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTokens.map((tok, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "8px 14px", fontFamily: "var(--font-mono)", fontSize: "12px", fontWeight: 600, color: "#1e293b" }}>
                          {tok.name}
                        </td>
                        <td style={{ padding: "8px 14px" }}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                            {tok.category === "color" && (
                              <span
                                style={{
                                  width: "14px",
                                  height: "14px",
                                  borderRadius: "3px",
                                  background: tok.value,
                                  border: "1px solid rgba(0,0,0,0.15)",
                                  display: "inline-block",
                                }}
                              />
                            )}
                            <code style={{ fontSize: "11px", background: "#f1f5f9", padding: "1px 4px", borderRadius: "3px" }}>
                              {tok.value}
                            </code>
                          </span>
                        </td>
                        <td style={{ padding: "8px 14px", textTransform: "capitalize", color: "#64748b" }}>{tok.category}</td>
                        <td style={{ padding: "8px 14px" }}>
                          <Badge tone={tok.classification === "observed" ? "success" : "neutral"}>
                            {tok.classification}
                          </Badge>
                        </td>
                        <td style={{ padding: "8px 14px", textAlign: "right" }}>
                          <button
                            onClick={() => copyToClipboard(tok.value, `tok-${idx}`)}
                            style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: "11px", fontWeight: 600 }}
                          >
                            {copiedToken === `tok-${idx}` ? "Copied!" : "Copy"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Export Modal (JSON / CSS) */}
      {exportModalType && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setExportModalType(null); }}>
          <section className="dialog" role="dialog" aria-modal="true" style={{ maxWidth: "700px", width: "90%" }}>
            <div className="dialog-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Export Design System ({exportModalType.toUpperCase()})</h2>
              <button className="icon-button" onClick={() => setExportModalType(null)}>
                <Icon name="close" />
              </button>
            </div>
            <textarea
              readOnly
              value={exportContent}
              style={{
                width: "100%",
                height: "360px",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                resize: "vertical",
                marginTop: "12px",
              }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "12px" }}>
              <Button variant="secondary" onClick={() => setExportModalType(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  navigator.clipboard.writeText(exportContent);
                  setCopiedToken("modal-export");
                  setTimeout(() => setCopiedToken(null), 2000);
                }}
              >
                <Icon name="copy" size={15} />
                {copiedToken === "modal-export" ? "Copied!" : "Copy Code"}
              </Button>
            </div>
          </section>
        </div>
      )}

      {/* Google Stitch Brief Dialog */}
      {stitchModalOpen && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setStitchModalOpen(false); }}>
          <section className="dialog prompt-dialog" role="dialog" aria-modal="true" style={{ maxWidth: "800px", width: "90%" }}>
            <div className="dialog-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <Badge tone="blue">Google Stitch Design System Brief</Badge>
                <h2 style={{ margin: "4px 0 0" }}>Design System Refinement Brief</h2>
                <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                  Harmonize visual tokens, components, and layout across all screens in Google Stitch.
                </p>
              </div>
              <button className="icon-button" onClick={() => setStitchModalOpen(false)}>
                <Icon name="close" />
              </button>
            </div>

            <div
              className="stitch-handoff-banner"
              style={{
                margin: "12px 0",
                padding: "10px",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "6px",
                fontSize: "12px",
                color: "#166534",
              }}
            >
              <strong>Handoff Procedure:</strong> Upload all original screenshots to Google Stitch in order, then paste this prompt into Stitch to produce harmonized screens.
            </div>

            <textarea
              readOnly
              value={stitchPromptText}
              style={{
                width: "100%",
                height: "350px",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                resize: "vertical",
              }}
            />

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Optional custom instruction..."
                  value={stitchCustomInstructions}
                  onChange={(e) => setStitchCustomInstructions(e.target.value)}
                  style={{ fontSize: "12px", padding: "6px 10px", borderRadius: "4px", border: "1px solid #cbd5e1", width: "260px" }}
                />
                <Button variant="secondary" onClick={handleRegenerateStitchPrompt} disabled={generatingStitch}>
                  Regenerate
                </Button>
              </div>
              <Button
                variant="primary"
                onClick={() => {
                  navigator.clipboard.writeText(stitchPromptText);
                  setCopiedPrompt(true);
                  setTimeout(() => setCopiedPrompt(false), 2000);
                }}
              >
                <Icon name="copy" size={15} />
                {copiedPrompt ? "Copied Brief!" : "Copy Full Brief"}
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function export_tokens_to_css_client(tokens: ProposedDesignToken[]): string {
  const lines = [":root {"];
  for (const t of tokens) {
    const varName = "--" + t.name.replace(/\./g, "-").replace(/_/g, "-");
    let val = t.value;
    if ((t.category === "spacing" || t.category === "radius") && /^\d+$/.test(val)) {
      val = `${val}px`;
    }
    lines.push(`  ${varName}: ${val};`);
  }
  lines.push("}");
  return lines.join("\n");
}
