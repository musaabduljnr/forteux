"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, MetricCard, PageHeader, SectionTitle } from "@/components/ui";
import { formatDate } from "@/lib/demo-data";

export default function DashboardPage() {
  const { audits, projects, documents, user: appUser } = useAppState();
  const [supabaseUser, setSupabaseUser] = useState<User | null>(null);
  const [userProfileName, setUserProfileName] = useState<string>("");
  const [todayDateStr, setTodayDateStr] = useState("");

  const supabase = createClient();

  useEffect(() => {
    // Format current date
    const now = new Date();
    const options: Intl.DateTimeFormatOptions = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
    setTodayDateStr(now.toLocaleDateString(undefined, options));

    async function loadProfile() {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setSupabaseUser(user);
        const name =
          user.user_metadata?.full_name ||
          user.user_metadata?.name ||
          user.email?.split("@")[0] ||
          "";
        if (name) setUserProfileName(name);

        const { data: profile } = await supabase
          .from("profiles")
          .select("full_name")
          .eq("id", user.id)
          .single();

        if (profile?.full_name) {
          setUserProfileName(profile.full_name);
        }
      }
    }
    loadProfile();
  }, [supabase]);

  const recentAudits = audits.slice(0, 4);
  const recentProjects = projects.slice(0, 3);
  const readyDocuments = documents.filter((document) => document.status === "ready").length;
  const screensAnalysed = audits.reduce((total, audit) => total + audit.screens.length, 0);
  const issuesFound = audits.reduce((total, audit) => total + audit.issues.length, 0);

  const greetingName = userProfileName
    ? userProfileName.split(" ")[0]
    : appUser.displayName.split(" ")[0] || "Designer";

  return (
    <div className="page-stack">
      <div className="dashboard-welcome">
        <PageHeader
          eyebrow={todayDateStr || "Today"}
          title={`Welcome back, ${greetingName}`}
          description="Turn your interface screens into clearer, more confident design decisions."
          action={<Button href="/audits/new" icon="plus">New audit</Button>}
        />
        <div className="welcome-mark">
          <span className="welcome-spark"><Icon name="spark" size={24} /></span>
          <span className="welcome-line welcome-line-one" />
          <span className="welcome-line welcome-line-two" />
        </div>
      </div>

      {!supabaseUser && (
        <div className="demo-notice">
          <span>
            <strong>Local workspace mode</strong> Sign in with Supabase Auth or Google OAuth to persist audits to the cloud.
          </span>
          <Link href="/login">Sign in <Icon name="arrow" size={14} /></Link>
        </div>
      )}

      <section>
        <SectionTitle title="Your overview" description="A snapshot of activity across your workspace." />
        <div className="metrics-grid">
          <MetricCard label="Total audits" value={audits.length} detail={audits.length === 1 ? "1 audit created" : `${audits.length} audits created`} icon="eye" tint="blue" />
          <MetricCard label="Screens analysed" value={screensAnalysed} detail={screensAnalysed === 1 ? "1 screen total" : `${screensAnalysed} screens total`} icon="image" tint="green" />
          <MetricCard label="Issues identified" value={issuesFound} detail={issuesFound === 1 ? "1 issue recorded" : `${issuesFound} issues recorded`} icon="warning" tint="amber" />
          <MetricCard label="Projects" value={projects.length} detail={projects.length === 1 ? "1 active project" : `${projects.length} active projects`} icon="folder" tint="violet" />
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel recent-audits-panel">
          <SectionTitle title="Recent audits" action={<Link className="inline-link" href="/history">View history <Icon name="arrow" size={15} /></Link>} />
          {recentAudits.length > 0 ? (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Audit</th>
                    <th>Mode</th>
                    <th>Screens</th>
                    <th>Issues</th>
                    <th>Updated</th>
                    <th>Status</th>
                    <th><span className="visually-hidden">Open</span></th>
                  </tr>
                </thead>
                <tbody>
                  {recentAudits.map((audit) => (
                    <tr key={audit.id}>
                      <td>
                        <Link href={`/audits/${audit.id}`} className="table-primary">{audit.name}</Link>
                        <span className="table-subtitle">{projects.find((project) => project.id === audit.projectId)?.name ?? "Project"}</span>
                      </td>
                      <td>{audit.mode === "multi" ? "Multi-screen" : "Single screen"}</td>
                      <td>{audit.screens.length}</td>
                      <td>{audit.issues.length || "—"}</td>
                      <td>{formatDate(audit.createdAt)}</td>
                      <td><Badge tone="demo">Active</Badge></td>
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
              title="No audits yet"
              description="Your audits will appear here once you upload and analyse a screen."
              action={<Button href="/audits/new" variant="secondary" icon="plus">Start an audit</Button>}
            />
          )}
        </section>

        <section className="panel projects-panel">
          <SectionTitle title="Projects" action={<Link className="inline-link" href="/projects">All projects <Icon name="arrow" size={15} /></Link>} />
          {recentProjects.length > 0 ? (
            <div className="project-list">
              {recentProjects.map((project, index) => (
                <Link href={`/projects/${project.id}`} className="project-list-item" key={project.id}>
                  <span className={`project-avatar project-avatar-${index % 4}`}>{project.name.slice(0, 1).toUpperCase()}</span>
                  <span className="project-list-copy">
                    <strong>{project.name}</strong>
                    <small>{audits.filter((audit) => audit.projectId === project.id).length} audits · Updated {formatDate(project.updatedAt)}</small>
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

        <section className="panel knowledge-overview">
          <SectionTitle title="Knowledge library" description="Reference material and design system guides." action={<Link className="inline-link" href="/knowledge">Manage library <Icon name="arrow" size={15} /></Link>} />
          <div className="knowledge-summary">
            <div className="knowledge-summary-icon"><Icon name="book" size={19} /></div>
            <div>
              <strong>{documents.length} reference documents</strong>
              <span>{readyDocuments} ready for context retrieval</span>
            </div>
            <Button href="/knowledge" variant="secondary">Open library</Button>
          </div>
        </section>
      </div>

      <div className="dashboard-footnote">
        <Icon name="info" size={15} />
        {supabaseUser ? "Connected to Supabase PostgreSQL with Row Level Security." : "Running with local workspace state. Sign in to sync across devices."}
      </div>
    </div>
  );
}
