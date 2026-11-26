"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, MetricCard, PageHeader, SectionTitle } from "@/components/ui";
import type { DashboardAuditItem, DashboardProjectItem, DashboardSummaryResponse } from "@/lib/types";

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
  } catch {
    return iso;
  }
}

interface DashboardStats {
  totalAudits: number;
  screensAnalysed: number;
  issuesIdentified: number;
  totalProjects: number;
}

export default function DashboardPage() {
  const supabase = createClient();

  const [supabaseUser, setSupabaseUser] = useState<User | null>(null);
  const [profileName, setProfileName] = useState("");
  const [todayDateStr, setTodayDateStr] = useState("");

  const [recentAudits, setRecentAudits] = useState<DashboardAuditItem[]>([]);
  const [recentProjects, setRecentProjects] = useState<DashboardProjectItem[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    totalAudits: 0,
    screensAnalysed: 0,
    issuesIdentified: 0,
    totalProjects: 0,
  });

  const [loading, setLoading] = useState(true);
  const [statsUnavailable, setStatsUnavailable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const now = new Date();
    setTodayDateStr(now.toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" }));

    async function bootstrap() {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setSupabaseUser(user);
        const metaName = user.user_metadata?.full_name || user.user_metadata?.name || user.email?.split("@")[0] || "";
        setProfileName(metaName);
        const { data: profile } = await supabase.from("profiles").select("full_name").eq("id", user.id).single();
        if (profile?.full_name) setProfileName(profile.full_name);
      } else {
        setLoading(false);
        return;
      }

      try {
        const res = await fetch("/api/backend/dashboard/summary");
        if (res.status === 401) {
          setStatsUnavailable(true);
          return;
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const summary = (await res.json()) as DashboardSummaryResponse;
        setRecentAudits(summary.recent_audits ?? []);
        setRecentProjects(summary.recent_projects ?? []);
        setStats({
          totalAudits: summary.total_audits ?? 0,
          screensAnalysed: summary.screens_analysed ?? 0,
          issuesIdentified: summary.issues_identified ?? 0,
          totalProjects: summary.total_projects ?? 0,
        });
      } catch (err) {
        setStatsUnavailable(true);
        setError(err instanceof Error ? err.message : "Could not load dashboard data");
      } finally {
        setLoading(false);
      }
    }

    void bootstrap();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const greetingName = profileName.trim().split(/\s+/)[0] || "Designer";
  const hasAudits = recentAudits.length > 0;
  const hasProjects = recentProjects.length > 0;

  return (
    <div className="page-stack">
      <div className="dashboard-welcome">
        <PageHeader
          eyebrow={todayDateStr || "Today"}
          title={`Welcome back, ${greetingName}`}
          description="Turn your interface screens into clearer, more confident design decisions."
          action={<Button href="/audits/new" icon="plus">{hasAudits ? "New audit" : "Start your first audit"}</Button>}
        />
        <div className="welcome-mark">
          <span className="welcome-spark"><Icon name="spark" size={24} /></span>
          <span className="welcome-line welcome-line-one" />
          <span className="welcome-line welcome-line-two" />
        </div>
      </div>

      {!loading && !supabaseUser && (
        <div className="demo-notice">
          <span>
            <strong>Sign in required.</strong> Sign in to view your projects and audits.
          </span>
          <Link href="/login">Sign in <Icon name="arrow" size={14} /></Link>
        </div>
      )}

      {error && (
        <div className="demo-notice">
          <span><strong>Dashboard metrics unavailable.</strong> {error}</span>
        </div>
      )}

      <section>
        <SectionTitle title="Your overview" description="A snapshot of activity across your workspace." />
        <div className="metrics-grid">
          <MetricCard
            label="Total audits"
            value={loading || statsUnavailable ? "—" : stats.totalAudits}
            detail={loading ? "Loading…" : statsUnavailable ? "Unavailable" : stats.totalAudits === 1 ? "1 audit created" : `${stats.totalAudits} audits created`}
            icon="eye"
            tint="blue"
          />
          <MetricCard
            label="Screens analysed"
            value={loading || statsUnavailable ? "—" : stats.screensAnalysed}
            detail={loading ? "Loading…" : statsUnavailable ? "Unavailable" : stats.screensAnalysed === 1 ? "1 screen analysed" : `${stats.screensAnalysed} screens analysed`}
            icon="image"
            tint="green"
          />
          <MetricCard
            label="Issues identified"
            value={loading || statsUnavailable ? "—" : stats.issuesIdentified}
            detail={loading ? "Loading…" : statsUnavailable ? "Unavailable" : stats.issuesIdentified === 1 ? "1 issue identified" : `${stats.issuesIdentified} issues identified`}
            icon="warning"
            tint="amber"
          />
          <MetricCard
            label="Projects"
            value={loading || statsUnavailable ? "—" : stats.totalProjects}
            detail={loading ? "Loading…" : statsUnavailable ? "Unavailable" : stats.totalProjects === 1 ? "1 project" : `${stats.totalProjects} projects`}
            icon="folder"
            tint="violet"
          />
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel recent-audits-panel">
          <SectionTitle
            title="Recent audits"
            action={<Link className="inline-link" href="/history">View history <Icon name="arrow" size={15} /></Link>}
          />
          {loading ? (
            <p style={{ padding: "2rem", textAlign: "center", opacity: 0.6 }}>Loading…</p>
          ) : hasAudits ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Audit</th>
                    <th>Mode</th>
                    <th>Screens</th>
                    <th>Issues</th>
                    <th>Created</th>
                    <th>Status</th>
                    <th><span className="visually-hidden">Open</span></th>
                  </tr>
                </thead>
                <tbody>
                  {recentAudits.map((audit) => (
                    <tr key={audit.id}>
                      <td>
                        <Link href={`/audits/${audit.id}`} className="table-primary">{audit.name}</Link>
                        <span className="table-subtitle">
                          <Link href={`/projects/${audit.project_id}`} style={{ color: "inherit", textDecoration: "none" }}>
                            {audit.project_name}
                          </Link>
                        </span>
                      </td>
                      <td>{audit.mode === "multi" ? "Multi-screen" : "Single screen"}</td>
                      <td>{audit.screen_count}</td>
                      <td>{audit.finding_count}</td>
                      <td>{formatDate(audit.created_at)}</td>
                      <td>
                        <Badge tone={audit.status === "completed" ? "success" : "neutral"}>
                          {audit.status}
                        </Badge>
                      </td>
                      <td>
                        <Link href={`/audits/${audit.id}`} aria-label={`Open ${audit.name}`} className="icon-button table-open">
                          <Icon name="arrow" size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon="eye"
              title="Your workspace is ready."
              description="Start your first UI/UX audit to see your findings, projects, and design insights here."
              action={<Button href="/audits/new" variant="secondary" icon="plus">Start your first audit</Button>}
            />
          )}
        </section>

        <section className="panel projects-panel">
          <SectionTitle
            title="Projects"
            action={<Link className="inline-link" href="/projects">All projects <Icon name="arrow" size={15} /></Link>}
          />
          {loading ? (
            <p style={{ padding: "2rem", textAlign: "center", opacity: 0.6 }}>Loading…</p>
          ) : hasProjects ? (
            <div className="project-list">
              {recentProjects.map((project, index) => (
                <Link href={`/projects/${project.id}`} className="project-list-item" key={project.id}>
                  <span className={`project-avatar project-avatar-${index % 4}`}>{project.name.slice(0, 1).toUpperCase()}</span>
                  <span className="project-list-copy">
                    <strong>{project.name}</strong>
                    <small>
                      {project.audit_count} {project.audit_count === 1 ? "audit" : "audits"} · Updated {formatDate(project.updated_at)}
                    </small>
                  </span>
                  <Icon name="chevron" size={17} />
                </Link>
              ))}
              <Button href="/projects" variant="secondary" className="full-width-button" icon="plus">Create a project</Button>
            </div>
          ) : (
            <EmptyState
              icon="folder"
              title="No projects yet"
              description="Create a project to organise your audits and design assets."
              action={<Button href="/projects" variant="secondary" icon="plus">Create a project</Button>}
            />
          )}
        </section>
      </div>

      <div className="dashboard-footnote">
        <Icon name="info" size={15} />
        {supabaseUser
          ? "Connected to Supabase PostgreSQL with Row Level Security."
          : "Sign in to sync your workspace across devices."}
      </div>
    </div>
  );
}
