"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "./icons";
import { Badge, Button, EmptyState, SeverityBadge } from "./ui";
import type { AuditScreen, FlowReport, MultiScreenBoundingBox, MultiScreenFinding } from "@/lib/types";

interface MultiScreenWorkspaceProps {
  auditId: string;
  projectId: string;
  auditName: string;
}

export function MultiScreenWorkspace({ auditId, projectId, auditName }: MultiScreenWorkspaceProps) {
  const [screens, setScreens] = useState<AuditScreen[]>([]);
  const [activeScreenId, setActiveScreenId] = useState<string | null>(null);
  const [flowReport, setFlowReport] = useState<FlowReport | null>(null);
  const [screenFindings, setScreenFindings] = useState<MultiScreenFinding[]>([]);
  const [crossFindings, setCrossFindings] = useState<MultiScreenFinding[]>([]);
  const [selectedFindingIds, setSelectedFindingIds] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<"screen_issues" | "cross_screen_issues" | "journey_overview">("screen_issues");
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null);
  const [hoveredFindingId, setHoveredFindingId] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [generatingPrompt, setGeneratingPrompt] = useState(false);
  const [promptContent, setPromptContent] = useState<string | null>(null);
  const [promptCopied, setPromptCopied] = useState(false);
  const [userInstructions, setUserInstructions] = useState("");
  const [promptModalOpen, setPromptModalOpen] = useState(false);

  // Load screens
  const loadScreens = useCallback(async () => {
    try {
      const res = await fetch(`/api/backend/projects/${projectId}/audits/${auditId}/screens`);
      if (res.ok) {
        const data: AuditScreen[] = await res.json();
        setScreens(data);
        if (data.length > 0 && !activeScreenId) {
          setActiveScreenId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load screens:", err);
    }
  }, [projectId, auditId, activeScreenId]);

  // Load flow report and findings
  const loadFlowReport = useCallback(async () => {
    try {
      const res = await fetch(`/api/backend/projects/${projectId}/audits/${auditId}/flow-report`);
      if (res.ok) {
        const data: FlowReport = await res.json();
        setFlowReport(data);
        setScreenFindings(data.screen_level_findings || []);
        setCrossFindings(data.cross_screen_findings || []);
        // Select all by default
        const allIds = new Set<string>();
        (data.screen_level_findings || []).forEach((f) => allIds.add(f.id));
        (data.cross_screen_findings || []).forEach((f) => allIds.add(f.id));
        setSelectedFindingIds(allIds);
      }
    } catch {
      // Flow report may not exist yet
    }
  }, [projectId, auditId]);

  useEffect(() => {
    async function init() {
      setLoading(true);
      await loadScreens();
      await loadFlowReport();
      setLoading(false);
    }
    init();
  }, [loadScreens, loadFlowReport]);

  const activeScreen = useMemo(() => {
    return screens.find((s) => s.id === activeScreenId) || screens[0] || null;
  }, [screens, activeScreenId]);

  // Screen-level findings for currently active screen
  const currentScreenFindings = useMemo(() => {
    if (!activeScreen) return [];
    return screenFindings.filter(
      (f) => f.affected_screen_ids && f.affected_screen_ids.includes(activeScreen.id)
    );
  }, [screenFindings, activeScreen]);

  // All findings relevant to active screen (including cross-screen that affect it)
  const activeScreenBoxes = useMemo(() => {
    if (!activeScreen) return [];
    const boxes: Array<{ findingId: string; box: MultiScreenBoundingBox; isCross: boolean; selected: boolean }> = [];
    const allFindings = [...screenFindings, ...crossFindings];
    allFindings.forEach((f) => {
      const isSelected = selectedFindingIds.has(f.id);
      (f.bounding_boxes || []).forEach((b) => {
        if (b.screen_id === activeScreen.id) {
          boxes.push({
            findingId: f.id,
            box: b,
            isCross: f.scope === "cross_screen",
            selected: isSelected,
          });
        }
      });
    });
    return boxes;
  }, [activeScreen, screenFindings, crossFindings, selectedFindingIds]);

  // Finding counts per screen ID
  const findingCountsPerScreen = useMemo(() => {
    const map: Record<string, number> = {};
    screenFindings.forEach((f) => {
      f.affected_screen_ids.forEach((sid) => {
        map[sid] = (map[sid] || 0) + 1;
      });
    });
    return map;
  }, [screenFindings]);

  // Trigger Multi-Screen Analysis
  const handleAnalyzeFlow = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await fetch(`/api/backend/projects/${projectId}/audits/${auditId}/analyze-flow`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.error?.message || errData?.detail?.message || "Multi-screen flow analysis failed");
      }
      await loadFlowReport();
    } catch (err: unknown) {
      setAnalysisError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  // Toggle selection
  const toggleFindingSelection = (id: string) => {
    setSelectedFindingIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    const all = new Set<string>();
    screenFindings.forEach((f) => all.add(f.id));
    crossFindings.forEach((f) => all.add(f.id));
    setSelectedFindingIds(all);
  };

  const deselectAll = () => {
    setSelectedFindingIds(new Set());
  };

  // Generate Stitch prompt
  const handleGeneratePrompt = async () => {
    if (selectedFindingIds.size === 0) return;
    setGeneratingPrompt(true);
    try {
      const res = await fetch(`/api/backend/projects/${projectId}/audits/${auditId}/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({
          selected_finding_ids: Array.from(selectedFindingIds),
          user_instructions: userInstructions || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPromptContent(data.content);
        setPromptModalOpen(true);
      }
    } catch (err) {
      console.error("Prompt generation failed:", err);
    } finally {
      setGeneratingPrompt(false);
    }
  };

  const handleCopyPrompt = async () => {
    if (!promptContent) return;
    await navigator.clipboard.writeText(promptContent);
    setPromptCopied(true);
    setTimeout(() => setPromptCopied(false), 2500);
  };

  if (loading) {
    return (
      <div className="empty-state" style={{ padding: "60px 0" }}>
        <p>Loading multi-screen workspace...</p>
      </div>
    );
  }

  const totalFindings = screenFindings.length + crossFindings.length;
  const isAnalyzed = flowReport !== null && flowReport.status === "completed";

  return (
    <div className="workspace-shell">
      {/* Top Header / Mode Banner */}
      <div className="workspace-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <div className="breadcrumb" style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
            <Link href={`/projects/${projectId}`} style={{ color: "#64748b", textDecoration: "none" }}>Projects</Link>
            <span>/</span>
            <Badge tone="blue">Multi-Screen User Flow</Badge>
          </div>
          <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700 }}>{auditName}</h1>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {!isAnalyzed ? (
            <Button variant="primary" onClick={handleAnalyzeFlow} disabled={analyzing || screens.length < 2}>
              <Icon name="spark" size={15} />
              {analyzing ? "Analyzing Flow..." : "Analyze User Flow"}
            </Button>
          ) : (
            <Button variant="secondary" onClick={handleAnalyzeFlow} disabled={analyzing}>
              <Icon name="spark" size={14} />
              {analyzing ? "Re-analyzing..." : "Re-run Analysis"}
            </Button>
          )}

          <Button
            variant="primary"
            onClick={handleGeneratePrompt}
            disabled={selectedFindingIds.size === 0 || generatingPrompt || !isAnalyzed}
          >
            <Icon name="file" size={15} />
            {generatingPrompt ? "Generating..." : "Generate Stitch Brief"}
          </Button>
        </div>
      </div>

      {analysisError && (
        <div className="demo-notice" style={{ background: "#fef2f2", color: "#991b1b", borderColor: "#fecaca", marginBottom: "16px" }}>
          <Icon name="warning" size={16} />
          <span>{analysisError}</span>
        </div>
      )}

      {/* 3-Column Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr 380px", gap: "16px", minHeight: "75vh" }}>
        {/* LEFT COLUMN: Screen Sequence Panel */}
        <div className="card" style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "12px", height: "fit-content" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" }}>
              Journey Sequence
            </span>
            <Badge tone="neutral">{screens.length} screens</Badge>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {screens.map((scr, idx) => {
              const isActive = scr.id === activeScreen?.id;
              const issueCount = findingCountsPerScreen[scr.id] || 0;
              return (
                <div
                  key={scr.id}
                  onClick={() => setActiveScreenId(scr.id)}
                  style={{
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: isActive ? "2px solid #3b82f6" : "1px solid #e2e8f0",
                    background: isActive ? "#eff6ff" : "#ffffff",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: isActive ? "#1d4ed8" : "#64748b" }}>
                      #{idx + 1}
                    </span>
                    {issueCount > 0 && (
                      <Badge tone="warning">{issueCount} issues</Badge>
                    )}
                  </div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {scr.screen_label || `Screen ${idx + 1}`}
                  </div>
                  {scr.screen_description && (
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {scr.screen_description}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {screens.length < 2 && (
            <div style={{ padding: "10px", background: "#fffbeb", borderRadius: "6px", fontSize: "12px", color: "#b45309" }}>
              <Icon name="warning" size={14} style={{ display: "inline", marginRight: "4px" }} />
              Multi-screen flow analysis requires at least 2 screenshots.
            </div>
          )}
        </div>

        {/* CENTER COLUMN: Screenshot Viewer with Bounding Box Overlays */}
        <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px", minHeight: "500px" }}>
          {activeScreen ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #f1f5f9", paddingBottom: "10px" }}>
                <div>
                  <h2 style={{ fontSize: "15px", fontWeight: 700, margin: 0 }}>
                    {activeScreen.screen_label || `Screen ${activeScreen.sequence_index + 1}`}
                  </h2>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>
                    Sequence #{activeScreen.sequence_index + 1} of {screens.length}
                    {activeScreen.width_px && activeScreen.height_px ? ` • ${activeScreen.width_px}×${activeScreen.height_px}px` : ""}
                  </span>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const curIdx = screens.findIndex((s) => s.id === activeScreen.id);
                      if (curIdx > 0) setActiveScreenId(screens[curIdx - 1].id);
                    }}
                    disabled={screens.findIndex((s) => s.id === activeScreen.id) === 0}
                  >
                    ← Prev
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const curIdx = screens.findIndex((s) => s.id === activeScreen.id);
                      if (curIdx < screens.length - 1) setActiveScreenId(screens[curIdx + 1].id);
                    }}
                    disabled={screens.findIndex((s) => s.id === activeScreen.id) === screens.length - 1}
                  >
                    Next →
                  </Button>
                </div>
              </div>

              {/* Viewport Canvas with Bounding Boxes */}
              <div style={{ position: "relative", width: "100%", flex: 1, display: "flex", justifyContent: "center", alignItems: "center", background: "#f8fafc", borderRadius: "6px", overflow: "hidden" }}>
                {activeScreen.download_url ? (
                  <div style={{ position: "relative", display: "inline-block", maxWidth: "100%", maxHeight: "70vh" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={activeScreen.download_url}
                      alt={activeScreen.screen_label || "Screenshot"}
                      style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain", display: "block" }}
                    />

                    {/* SVG Bounding Boxes Overlay */}
                    <svg
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "none",
                      }}
                      viewBox="0 0 1 1"
                      preserveAspectRatio="none"
                    >
                      {activeScreenBoxes.map((item, idx) => {
                        const isHovered = hoveredFindingId === item.findingId;
                        const isActive = activeFindingId === item.findingId;
                        const strokeColor = item.isCross
                          ? item.selected ? "#8b5cf6" : "#c4b5fd"
                          : item.selected ? "#f59e0b" : "#cbd5e1";

                        return (
                          <rect
                            key={`${item.findingId}-${idx}`}
                            x={item.box.x}
                            y={item.box.y}
                            width={item.box.width}
                            height={item.box.height}
                            fill={isActive || isHovered ? (item.isCross ? "rgba(139, 92, 246, 0.15)" : "rgba(245, 158, 11, 0.15)") : "none"}
                            stroke={strokeColor}
                            strokeWidth={isActive || isHovered ? 0.005 : 0.003}
                            strokeDasharray={item.isCross ? "0.01 0.005" : undefined}
                          />
                        );
                      })}
                    </svg>
                  </div>
                ) : (
                  <div style={{ color: "#94a3b8", fontSize: "13px" }}>No preview image available for this screen.</div>
                )}
              </div>
            </>
          ) : (
            <EmptyState title="No screen selected" description="Select a screen from the sequence on the left." />
          )}
        </div>

        {/* RIGHT COLUMN: Finding Panel with Scope Tabs */}
        <div className="card" style={{ padding: "14px", display: "flex", flexDirection: "column", height: "fit-content", maxHeight: "85vh" }}>
          {/* Tabs */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "4px", marginBottom: "12px", borderBottom: "1px solid #e2e8f0", paddingBottom: "8px" }}>
            <button
              onClick={() => setActiveTab("screen_issues")}
              style={{
                padding: "6px 4px",
                fontSize: "12px",
                fontWeight: activeTab === "screen_issues" ? 700 : 500,
                color: activeTab === "screen_issues" ? "#2563eb" : "#64748b",
                borderBottom: activeTab === "screen_issues" ? "2px solid #2563eb" : "none",
                background: "none",
                border: "none",
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              Screen ({currentScreenFindings.length})
            </button>
            <button
              onClick={() => setActiveTab("cross_screen_issues")}
              style={{
                padding: "6px 4px",
                fontSize: "12px",
                fontWeight: activeTab === "cross_screen_issues" ? 700 : 500,
                color: activeTab === "cross_screen_issues" ? "#8b5cf6" : "#64748b",
                borderBottom: activeTab === "cross_screen_issues" ? "2px solid #8b5cf6" : "none",
                background: "none",
                border: "none",
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              Cross-Screen ({crossFindings.length})
            </button>
            <button
              onClick={() => setActiveTab("journey_overview")}
              style={{
                padding: "6px 4px",
                fontSize: "12px",
                fontWeight: activeTab === "journey_overview" ? 700 : 500,
                color: activeTab === "journey_overview" ? "#0f172a" : "#64748b",
                borderBottom: activeTab === "journey_overview" ? "2px solid #0f172a" : "none",
                background: "none",
                border: "none",
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              Overview
            </button>
          </div>

          {/* Finding Cards / Content Container */}
          <div style={{ overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "10px", paddingRight: "4px" }}>
            {activeTab === "screen_issues" && (
              <>
                {currentScreenFindings.length === 0 ? (
                  <div style={{ padding: "30px 10px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                    {!isAnalyzed ? "Run flow analysis to evaluate screen issues." : "No screen-level findings identified for this screen."}
                  </div>
                ) : (
                  currentScreenFindings.map((f) => {
                    const isSelected = selectedFindingIds.has(f.id);
                    return (
                      <div
                        key={f.id}
                        onMouseEnter={() => setHoveredFindingId(f.id)}
                        onMouseLeave={() => setHoveredFindingId(null)}
                        onClick={() => setActiveFindingId(f.id)}
                        style={{
                          padding: "10px",
                          borderRadius: "6px",
                          border: activeFindingId === f.id ? "1.5px solid #3b82f6" : "1px solid #e2e8f0",
                          background: isSelected ? "#ffffff" : "#f8fafc",
                          opacity: isSelected ? 1 : 0.65,
                          cursor: "pointer",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "6px" }}>
                          <SeverityBadge severity={f.severity} />
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleFindingSelection(f.id);
                            }}
                            style={{ cursor: "pointer" }}
                          />
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "#1e293b", margin: "6px 0 3px" }}>
                          {f.title}
                        </div>
                        <div style={{ fontSize: "12px", color: "#475569", lineHeight: 1.4 }}>
                          {f.description}
                        </div>
                        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px", background: "#f1f5f9", padding: "4px 6px", borderRadius: "4px" }}>
                          <strong>Fix:</strong> {f.recommended_fix}
                        </div>
                      </div>
                    );
                  })
                )}
              </>
            )}

            {activeTab === "cross_screen_issues" && (
              <>
                {crossFindings.length === 0 ? (
                  <div style={{ padding: "30px 10px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                    {!isAnalyzed ? "Run flow analysis to identify cross-screen issues." : "No cross-screen discrepancies found across this flow."}
                  </div>
                ) : (
                  crossFindings.map((f) => {
                    const isSelected = selectedFindingIds.has(f.id);
                    return (
                      <div
                        key={f.id}
                        onMouseEnter={() => setHoveredFindingId(f.id)}
                        onMouseLeave={() => setHoveredFindingId(null)}
                        onClick={() => setActiveFindingId(f.id)}
                        style={{
                          padding: "10px",
                          borderRadius: "6px",
                          border: activeFindingId === f.id ? "1.5px solid #8b5cf6" : "1px solid #e2e8f0",
                          background: isSelected ? "#faf5ff" : "#f8fafc",
                          opacity: isSelected ? 1 : 0.65,
                          cursor: "pointer",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "6px" }}>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <SeverityBadge severity={f.severity} />
                            <Badge tone="blue">Cross-Screen</Badge>
                          </div>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleFindingSelection(f.id);
                            }}
                            style={{ cursor: "pointer" }}
                          />
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "#1e293b", margin: "6px 0 3px" }}>
                          {f.title}
                        </div>
                        <div style={{ fontSize: "12px", color: "#475569", lineHeight: 1.4 }}>
                          {f.description}
                        </div>

                        {/* Affected Screen Chips */}
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "8px" }}>
                          <span style={{ fontSize: "10px", color: "#64748b", alignSelf: "center" }}>Screens:</span>
                          {f.affected_screen_ids.map((sid) => {
                            const scrIdx = screens.findIndex((s) => s.id === sid);
                            return (
                              <button
                                key={sid}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveScreenId(sid);
                                }}
                                style={{
                                  fontSize: "10px",
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  border: "1px solid #cbd5e1",
                                  background: sid === activeScreen?.id ? "#3b82f6" : "#ffffff",
                                  color: sid === activeScreen?.id ? "#ffffff" : "#475569",
                                  cursor: "pointer",
                                }}
                              >
                                #{scrIdx >= 0 ? scrIdx + 1 : "?"}
                              </button>
                            );
                          })}
                        </div>

                        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px", background: "#f3e8ff", padding: "4px 6px", borderRadius: "4px" }}>
                          <strong>Cohesion Fix:</strong> {f.recommended_fix}
                        </div>
                      </div>
                    );
                  })
                )}
              </>
            )}

            {activeTab === "journey_overview" && (
              <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
                {flowReport?.journey_report ? (
                  <>
                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a" }}>Journey Summary</strong>
                      <p style={{ color: "#475569", margin: "4px 0" }}>{flowReport.journey_report.journey_summary}</p>
                    </div>

                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a" }}>Assessment</strong>
                      <p style={{ color: "#475569", margin: "4px 0" }}>{flowReport.journey_report.overall_assessment}</p>
                    </div>

                    <div>
                      <strong style={{ fontSize: "13px", color: "#15803d" }}>Strengths</strong>
                      <ul style={{ margin: "4px 0", paddingLeft: "18px", color: "#475569" }}>
                        {flowReport.journey_report.strengths.map((str, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>
                            <strong>{str.title}:</strong> {str.description}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <strong style={{ fontSize: "13px", color: "#b91c1c" }}>Major Friction Points</strong>
                      <ul style={{ margin: "4px 0", paddingLeft: "18px", color: "#475569" }}>
                        {flowReport.journey_report.major_friction_points.map((fr, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>
                            <strong>{fr.title}:</strong> {fr.description}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <strong style={{ fontSize: "13px", color: "#0f172a" }}>Recommended Flow Improvements</strong>
                      <ol style={{ margin: "4px 0", paddingLeft: "18px", color: "#475569" }}>
                        {flowReport.journey_report.recommended_improvements.map((imp, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>{imp}</li>
                        ))}
                      </ol>
                    </div>

                    <div style={{ padding: "8px", background: "#f8fafc", borderRadius: "4px", color: "#64748b", fontSize: "11px" }}>
                      <strong>Static Analysis Limitations:</strong> {flowReport.journey_report.limitations}
                    </div>
                  </>
                ) : (
                  <div style={{ padding: "30px 10px", textAlign: "center", color: "#94a3b8" }}>
                    Run flow analysis to view the complete journey intelligence report.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Selection Controls Footer */}
          {isAnalyzed && (
            <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: "10px", marginTop: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                {selectedFindingIds.size} of {totalFindings} selected
              </span>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  onClick={selectAll}
                  style={{ fontSize: "11px", color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: "2px" }}
                >
                  Select all
                </button>
                <span style={{ color: "#cbd5e1" }}>•</span>
                <button
                  onClick={deselectAll}
                  style={{ fontSize: "11px", color: "#64748b", background: "none", border: "none", cursor: "pointer", padding: "2px" }}
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Google Stitch Brief Dialog */}
      {promptModalOpen && promptContent && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setPromptModalOpen(false); }}>
          <section className="dialog prompt-dialog" role="dialog" aria-modal="true" style={{ maxWidth: "800px", width: "90%" }}>
            <div className="dialog-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <Badge tone="blue">Multi-Screen Google Stitch Brief</Badge>
                <h2 style={{ margin: "4px 0 0" }}>Google Stitch Flow Redesign Brief</h2>
                <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                  Cohesive multi-screen brief addressing {selectedFindingIds.size} selected issues across {screens.length} screens.
                </p>
              </div>
              <button className="icon-button" onClick={() => setPromptModalOpen(false)}>
                <Icon name="close" />
              </button>
            </div>

            <div className="stitch-handoff-banner" style={{ margin: "12px 0", padding: "10px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "6px", fontSize: "12px", color: "#166534" }}>
              <strong>Handoff:</strong> Provide all {screens.length} original screenshots to Google Stitch in order, then paste this prompt into the generation window.
            </div>

            <textarea
              readOnly
              value={promptContent}
              style={{
                width: "100%",
                height: "350px",
                fontFamily: "monospace",
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
                  value={userInstructions}
                  onChange={(e) => setUserInstructions(e.target.value)}
                  style={{ fontSize: "12px", padding: "6px 10px", borderRadius: "4px", border: "1px solid #cbd5e1", width: "280px" }}
                />
                <Button variant="secondary" onClick={handleGeneratePrompt} disabled={generatingPrompt}>
                  Regenerate
                </Button>
              </div>
              <Button variant="primary" onClick={handleCopyPrompt}>
                <Icon name="copy" size={15} />
                {promptCopied ? "Copied to Clipboard!" : "Copy Full Brief"}
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function jsonBody(obj: unknown) {
  return JSON.stringify(obj);
}
