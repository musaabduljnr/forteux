"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, Modal, PageHeader } from "@/components/ui";
import { formatDate } from "@/lib/demo-data";

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, audits, documents, createProject, notify } = useAppState();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const filtered = projects.filter((project) => `${project.name} ${project.description}`.toLowerCase().includes(query.toLowerCase()));

  function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    const id = createProject(trimmed, description.trim());
    setDialogOpen(false);
    setName("");
    setDescription("");
    notify("Project created in this browser demo.", "success");
    router.push(`/projects/${id}`);
  }

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Workspace" title="Projects" description="Keep related audits, screens, and design references together." action={<Button onClick={() => setDialogOpen(true)} icon="plus">New project</Button>} />
      <div className="demo-notice"><span><strong>Browser demo</strong> Project changes are local to this browser and are not synced to an account.</span></div>
      <div className="list-toolbar">
        <label className="search-field"><Icon name="search" size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search projects" aria-label="Search projects" />{query && <button aria-label="Clear search" onClick={() => setQuery("")}><Icon name="close" size={15} /></button>}</label>
        <span className="toolbar-count">{filtered.length} {filtered.length === 1 ? "project" : "projects"}</span>
      </div>
      {filtered.length ? <div className="project-card-grid">
        {filtered.map((project, index) => {
          const projectAudits = audits.filter((audit) => audit.projectId === project.id);
          const screenCount = projectAudits.reduce((total, audit) => total + audit.screens.length, 0);
          const projectDocs = documents.filter((document) => document.projectId === project.id).length;
          return (
            <article className="project-card" key={project.id}>
              <div className="project-card-top"><span className={`project-avatar project-avatar-large project-avatar-${index % 4}`}>{project.name.slice(0, 1).toUpperCase()}</span><Badge tone={project.status === "Active" ? "success" : "neutral"}>{project.status}</Badge><Link className="icon-button" href={`/projects/${project.id}`} aria-label={`Open ${project.name} details`}><Icon name="chevron" /></Link></div>
              <Link href={`/projects/${project.id}`} className="project-card-title">{project.name}</Link>
              <p>{project.description || "No description yet."}</p>
              <div className="project-card-stats"><span><Icon name="eye" size={15} />{projectAudits.length} audits</span><span><Icon name="image" size={15} />{screenCount} screens</span></div>
              <div className="project-card-bottom"><span>Updated {formatDate(project.updatedAt)}</span><Link href={`/projects/${project.id}`} aria-label={`Open ${project.name}`}><Icon name="arrow" size={17} /></Link></div>
              <span className="visually-hidden">{projectDocs} project knowledge documents</span>
            </article>
          );
        })}
      </div> : <EmptyState icon="folder" title={projects.length ? "No matching projects" : "Create your first project"} description={projects.length ? "Try another search term." : "Projects help keep your audits and reference material organised."} action={!projects.length ? <Button onClick={() => setDialogOpen(true)} icon="plus">Create a project</Button> : undefined} />}
      {dialogOpen && <Modal title="Create a project" description="Start a workspace for a product, feature, or team initiative." onClose={() => setDialogOpen(false)} footer={<><Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancel</Button><Button type="submit" form="create-project-form" icon="plus">Create project</Button></>}>
        <form id="create-project-form" className="form-grid modal-form" onSubmit={submitProject}>
          <label className="form-field form-field-wide"><span>Project name</span><input autoFocus required maxLength={80} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Mobile onboarding" /></label>
          <label className="form-field form-field-wide"><span>Description <em>Optional</em></span><textarea rows={3} maxLength={300} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What is this project about?" /></label>
        </form>
      </Modal>}
    </div>
  );
}
