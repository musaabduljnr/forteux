"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useAppState } from "@/components/app-state";
import { Icon } from "@/components/icons";
import { Badge, Button, EmptyState, Modal, PageHeader, SectionTitle } from "@/components/ui";
import { formatDate } from "@/lib/demo-data";

export default function ProjectDetailsPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const projectId = params.projectId;
  const { projects, audits, documents, updateProject, deleteProject, notify } = useAppState();
  const project = projects.find((item) => item.id === projectId);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const projectAudits = audits.filter((audit) => audit.projectId === projectId);
  const projectDocuments = documents.filter((document) => document.projectId === projectId);

  if (!project) return <div className="page-stack"><EmptyState icon="folder" title="Project not found" description="This project is no longer available in the local demo workspace." action={<Button href="/projects" variant="secondary">Back to projects</Button>} /></div>;

  function saveProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    updateProject(projectId, { name: name.trim(), description: description.trim() });
    setEditing(false);
    notify("Project details updated locally.", "success");
  }

  return (
    <div className="page-stack">
      <div className="project-detail-header">
        <div className="project-detail-mark">{project.name.slice(0, 1).toUpperCase()}</div>
        <PageHeader eyebrow={<span className="breadcrumb"><Link href="/projects">Projects</Link><Icon name="chevron" size={14} /><span>Overview</span></span>} title={project.name} description={project.description || "No project description."} action={<div className="button-row"><Button variant="secondary" icon="edit" onClick={() => { setName(project.name); setDescription(project.description); setEditing(true); }}>Edit project</Button><Button href="/audits/new" icon="plus">New audit</Button></div>} />
      </div>
      <div className="demo-notice"><span><strong>Local demo project</strong> Project changes affect only this browser workspace.</span><Badge tone={project.status === "Active" ? "success" : "neutral"}>{project.status}</Badge></div>
      <div className="metrics-grid metrics-grid-three">
        <div className="mini-metric"><span>Audits</span><strong>{projectAudits.length}</strong><small>Illustrative records</small></div>
        <div className="mini-metric"><span>Screens</span><strong>{projectAudits.reduce((total, audit) => total + audit.screens.length, 0)}</strong><small>Across project audits</small></div>
        <div className="mini-metric"><span>Knowledge sources</span><strong>{projectDocuments.length}</strong><small>Example metadata</small></div>
      </div>
      <section className="panel">
        <SectionTitle title="Project audits" description="Review recent audits in this project." action={<Link className="inline-link" href="/history">Full history <Icon name="arrow" size={15} /></Link>} />
        {projectAudits.length ? <div className="project-audit-list">{projectAudits.map((audit) => <Link className="project-audit-row" href={`/audits/${audit.id}`} key={audit.id}><span className="audit-row-icon"><Icon name={audit.mode === "multi" ? "layers" : "image"} size={18} /></span><span><strong>{audit.name}</strong><small>{audit.mode === "multi" ? "Multi-screen UX audit" : "Single-screen audit"} · {audit.screens.length} screens</small></span><Badge tone="demo">Demo</Badge><span className="audit-row-date">{formatDate(audit.createdAt)}</span><Icon name="chevron" size={17} /></Link>)}</div> : <EmptyState icon="eye" title="No audits in this project" description="Create an audit to start reviewing screens." action={<Button href="/audits/new" variant="secondary" icon="plus">New audit</Button>} />}
      </section>
      <section className="panel">
        <SectionTitle title="Project knowledge" description="Reference documents available within this project." action={<Link className="inline-link" href={`/knowledge?project=${project.id}`}>Manage knowledge <Icon name="arrow" size={15} /></Link>} />
        {projectDocuments.length ? <div className="project-audit-list">{projectDocuments.map((document) => <Link href={`/knowledge?project=${project.id}`} className="project-audit-row" key={document.id}><span className="audit-row-icon"><Icon name="file" size={18} /></span><span><strong>{document.name}</strong><small>{document.category} · {document.pages || "Page count unavailable"}</small></span><Badge tone={document.status === "ready" ? "success" : "warning"}>{document.status === "ready" ? "Ready (sample)" : document.status}</Badge><span className="audit-row-date">{formatDate(document.updatedAt)}</span><Icon name="chevron" size={17} /></Link>)}</div> : <EmptyState icon="book" title="No project references" description="Add project-specific guidance from the knowledge library." action={<Button href={`/knowledge?project=${project.id}`} variant="secondary" icon="plus">Add a reference</Button>} />}
      </section>
      <section className="danger-zone"><div><strong>Delete this project</strong><p>Removes the project and its local demo audits and references from this browser.</p></div><Button variant="danger" icon="trash" onClick={() => setConfirmDelete(true)}>Delete project</Button></section>
      {editing && <Modal title="Edit project" description="Update this project’s name or description." onClose={() => setEditing(false)} footer={<><Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button><Button type="submit" form="edit-project-form">Save changes</Button></>}>
        <form id="edit-project-form" className="form-grid modal-form" onSubmit={saveProject}>
          <label className="form-field form-field-wide"><span>Project name</span><input autoFocus required maxLength={80} value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label className="form-field form-field-wide"><span>Description</span><textarea rows={3} maxLength={300} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        </form>
      </Modal>}
      {confirmDelete && <Modal title="Delete project?" description={`“${project.name}” and its local demo records will be removed from this browser.`} onClose={() => setConfirmDelete(false)} footer={<><Button variant="secondary" onClick={() => setConfirmDelete(false)}>Keep project</Button><Button variant="danger" icon="trash" onClick={() => { deleteProject(projectId); setConfirmDelete(false); notify("Project removed from this browser demo.", "success"); router.push("/projects"); }}>Delete project</Button></>}>
        <div className="confirmation-callout"><Icon name="warning" size={19} /><p>This demo action is local only. It does not delete any server-side data.</p></div>
      </Modal>}
    </div>
  );
}
