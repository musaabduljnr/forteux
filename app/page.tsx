"use client";

import Link from "next/link";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, MetricCard, PageHeader, SectionTitle } from "@/components/ui";
import { formatDate } from "@/lib/demo-data";

export default function DashboardPage() {
  const { audits, projects, documents } = useAppState();
  const recentAudits = audits.slice(0, 4);
  const recentProjects = projects.slice(0, 3);
  const readyDocuments = documents.filter((document) => document.status === "ready").length;
  const screensAnalysed = audits.reduce((total, audit) => total + audit.screens.length, 0);
  const issuesFound = audits.reduce((total, audit) => total + audit.issues.length, 0);

  return (
    <div className="page-stack">
      <div className="dashboard-welcome">
        <PageHeader eyebrow="Monday, November 16, 2026" title="Good morning, Musa" description="Turn your interface screens into clearer, more confident design decisions." action={<Button href="/audits/new" icon="plus">New audit</Button>} />
        <div className="welcome-mark"><span className="welcome-spark"><Icon name="spark" size={24} /></span><span className="welcome-line welcome-line-one" /><span className="welcome-line welcome-line-two" /></div>
      </div>
      <div className="demo-notice"><span><strong>Sample workspace</strong> Dashboard activity and example records are illustrative demo data, not live product statistics.</span><Link href="/audits/demo">View demo workspace <Icon name="arrow" size={14} /></Link></div>
      <section>
        <SectionTitle title="Your overview" description="A snapshot of activity across this workspace." />
        <div className="metrics-grid">
          <MetricCard label="Total audits" value={audits.length} detail="Sample workspace records" icon="eye" tint="blue" />
          <MetricCard label="Screens analysed" value={screensAnalysed} detail="Illustrative screen count" icon="image" tint="green" />
          <MetricCard label="Issues identified" value={issuesFound} detail="Includes demo fixtures" icon="warning" tint="amber" />
          <MetricCard label="Projects" value={projects.length} detail="Across this workspace" icon="folder" tint="violet" />
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel recent-audits-panel">
          <SectionTitle title="Recent audits" action={<Link className="inline-link" href="/history">View history <Icon name="arrow" size={15} /></Link>} />
          {recentAudits.length > 0 ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Audit</th><th>Mode</th><th>Screens</th><th>Issues</th><th>Updated</th><th>Status</th><th><span className="visually-hidden">Open</span></th></tr></thead>
                <tbody>{recentAudits.map((audit) => (
                  <tr key={audit.id}>
                    <td><Link href={`/audits/${audit.id}`} className="table-primary">{audit.name}</Link><span className="table-subtitle">{projects.find((project) => project.id === audit.projectId)?.name ?? "Project"}</span></td>
                    <td>{audit.mode === "multi" ? "Multi-screen" : "Single screen"}</td>
                    <td>{audit.screens.length}</td>
                    <td>{audit.issues.length || "—"}</td>
                    <td>{formatDate(audit.createdAt)}</td>
                    <td><Badge tone="demo">Demo</Badge></td>
                    <td><Link href={`/audits/${audit.id}`} aria-label={`Open ${audit.name}`} className="icon-button table-open"><Icon name="arrow" size={16} /></Link></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <EmptyState icon="eye" title="No audits yet" description="Your audits will appear here once you add a screen." action={<Button href="/audits/new" variant="secondary" icon="plus">Start an audit</Button>} />}
        </section>

        <section className="panel projects-panel">
          <SectionTitle title="Projects" action={<Link className="inline-link" href="/projects">All projects <Icon name="arrow" size={15} /></Link>} />
          {recentProjects.length > 0 ? <div className="project-list">
            {recentProjects.map((project, index) => (
              <Link href={`/projects/${project.id}`} className="project-list-item" key={project.id}>
                <span className={`project-avatar project-avatar-${index % 4}`}>{project.name.slice(0, 1).toUpperCase()}</span>
                <span className="project-list-copy"><strong>{project.name}</strong><small>{audits.filter((audit) => audit.projectId === project.id).length} audits · Updated {formatDate(project.updatedAt)}</small></span>
                <Icon name="chevron" size={17} />
              </Link>
            ))}
            <Button href="/projects" variant="secondary" className="full-width-button" icon="plus">Create a project</Button>
          </div> : <EmptyState icon="folder" title="No projects yet" description="Create a project to keep your audits organised." action={<Button href="/projects" variant="secondary" icon="plus">Create a project</Button>} />}
        </section>

        <section className="panel knowledge-overview">
          <SectionTitle title="Knowledge library" description="Reference material for future audits." action={<Link className="inline-link" href="/knowledge">Manage library <Icon name="arrow" size={15} /></Link>} />
          <div className="knowledge-summary">
            <div className="knowledge-summary-icon"><Icon name="book" size={19} /></div>
            <div><strong>{documents.length} example documents</strong><span>{readyDocuments} marked ready · Demo metadata only</span></div>
            <Button href="/knowledge" variant="secondary">Open library</Button>
          </div>
        </section>
      </div>
      <div className="dashboard-footnote"><Icon name="info" size={15} />Sample activity is stored in this browser only. It is not connected to an account or backend.</div>
    </div>
  );
}
