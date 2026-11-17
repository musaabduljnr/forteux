"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, EmptyState, PageHeader } from "@/components/ui";
import { formatDate } from "@/lib/demo-data";

export default function HistoryPage() {
  const { audits, projects } = useAppState();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("all");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState("newest");

  const filtered = useMemo(() => audits
    .filter((audit) => `${audit.name} ${projects.find((project) => project.id === audit.projectId)?.name ?? ""}`.toLowerCase().includes(query.toLowerCase()))
    .filter((audit) => mode === "all" || audit.mode === mode)
    .filter((audit) => status === "all" || (status === "demo" ? audit.status === "demo" : audit.status === status))
    .sort((a, b) => sort === "oldest" ? a.createdAt.localeCompare(b.createdAt) : a.createdAt.localeCompare(b.createdAt) * -1), [audits, mode, projects, query, sort, status]);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Workspace" title="Audit history" description="Find and revisit screen reviews across your projects." />
      <div className="demo-notice"><span><strong>Illustrative records</strong> Audit history is stored in this browser demo; no backend processing has occurred.</span></div>
      <div className="history-toolbar">
        <label className="search-field history-search"><Icon name="search" size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search audits or projects" aria-label="Search audit history" />{query && <button aria-label="Clear search" onClick={() => setQuery("")}><Icon name="close" size={15} /></button>}</label>
        <label className="toolbar-select"><Icon name="filter" size={16} /><span className="visually-hidden">Audit mode</span><select value={mode} onChange={(event) => setMode(event.target.value)}><option value="all">All modes</option><option value="single">Single screen</option><option value="multi">Multi-screen</option></select></label>
        <label className="toolbar-select"><span className="visually-hidden">Audit status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All statuses</option><option value="demo">Demo</option><option value="ready">Results ready</option><option value="in_progress">In progress</option><option value="failed">Failed</option></select></label>
        <label className="toolbar-select"><span className="visually-hidden">Sort order</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
      </div>
      <section className="panel history-panel">
        <div className="history-table-heading"><strong>{filtered.length} {filtered.length === 1 ? "audit" : "audits"}</strong><span>Sample records are marked Demo.</span></div>
        {filtered.length ? <div className="table-scroll">
          <table className="data-table history-table">
            <thead><tr><th>Audit name</th><th>Project</th><th>Mode</th><th>Date created</th><th>Screens</th><th>Issues</th><th>Status</th><th><span className="visually-hidden">Open</span></th></tr></thead>
            <tbody>{filtered.map((audit) => (
              <tr key={audit.id}>
                <td><Link href={`/audits/${audit.id}`} className="table-primary">{audit.name}</Link></td>
                <td>{projects.find((project) => project.id === audit.projectId)?.name ?? "Project removed"}</td>
                <td>{audit.mode === "multi" ? "Multi-screen UX" : "Single screen"}</td>
                <td>{formatDate(audit.createdAt)}</td>
                <td>{audit.screens.length}</td>
                <td>{audit.issues.length || "—"}</td>
                <td><Badge tone="demo">Demo only</Badge></td>
                <td><Link href={`/audits/${audit.id}`} className="icon-button table-open" aria-label={`Open ${audit.name}`}><Icon name="arrow" size={16} /></Link></td>
              </tr>
            ))}</tbody>
          </table>
        </div> : <EmptyState icon="history" title={audits.length ? "No audits match these filters" : "No audits yet"} description={audits.length ? "Adjust your search or filters to see more results." : "Create your first audit and it will appear here."} />}
      </section>
    </div>
  );
}
