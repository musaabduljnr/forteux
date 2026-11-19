'use client';

import Link from 'next/link';
import { useState, useEffect, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Icon } from '@/components/icons';
import { Badge, Button, EmptyState, Modal, PageHeader } from '@/components/ui';
import type { ProjectFull } from '@/lib/types';

const CATEGORIES = ['All', 'Fintech', 'E-commerce', 'SaaS', 'Healthcare', 'Education', 'Travel', 'Food & Delivery', 'Productivity', 'Other'];

function formatDate(iso: string) {
  try {
    return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function ProjectsPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<ProjectFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // create modal
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [platformType, setPlatformType] = useState('');

  // filters
  const [query, setQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');

  useEffect(() => {
    void fetchProjects();
  }, []);

  async function fetchProjects() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/backend/v1/projects');
      if (res.status === 401) { setError('401'); setLoading(false); return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- API shape may vary
      const data: any = await res.json();
      // API may return {items:[]} or [] directly
      const items: ProjectFull[] = Array.isArray(data) ? data : (data?.items ?? []);
      // Try to enrich with stats for each project
      const enriched = await Promise.all(
        items.map(async (p) => {
          try {
            const sr = await fetch(`/api/backend/v1/projects/${p.id}/stats`);
            if (sr.ok) {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any -- stats shape unknown
              const stats: any = await sr.json();
              return { ...p, audit_count: stats.audit_count ?? p.audit_count ?? 0, screen_count: stats.screen_count ?? p.screen_count ?? 0, design_system_count: stats.design_system_count ?? p.design_system_count ?? 0 };
            }
          } catch { /* ignore stats failure */ }
          return p;
        })
      );
      setProjects(enriched);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }

  async function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch('/api/backend/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed, description: description.trim() || null, category: category || null, platform_type: platformType.trim() || null }),
      });
      if (res.status === 401) { setCreateError('Please sign in to create a project.'); return; }
      if (!res.ok) { const e = await res.json().catch(() => ({})); setCreateError((e as { detail?: string }).detail ?? `HTTP ${res.status}`); return; }
      const created: ProjectFull = await res.json() as ProjectFull;
      setDialogOpen(false);
      setName(''); setDescription(''); setCategory(''); setPlatformType('');
      router.push(`/projects/${created.id}`);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Could not create project');
    } finally {
      setCreating(false);
    }
  }

  if (error === '401') {
    return (
      <div className="page-stack">
        <PageHeader eyebrow="Workspace" title="Projects" description="Keep related audits, screens, and design references together." />
        <EmptyState icon="folder" title="Please sign in" description="Sign in to view and manage your projects." />
      </div>
    );
  }

  const filtered = projects
    .filter((p) => `${p.name} ${p.description ?? ''}`.toLowerCase().includes(query.toLowerCase()))
    .filter((p) => categoryFilter === 'All' || p.category === categoryFilter);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace"
        title="Projects"
        description="Keep related audits, screens, and design references together."
        action={<Button onClick={() => setDialogOpen(true)} icon="plus">New project</Button>}
      />

      {loading ? (
        <div className="demo-notice"><span>Loading projects…</span></div>
      ) : error ? (
        <div className="demo-notice"><span><strong>Error</strong> {error} — <button className="inline-link" onClick={() => { void fetchProjects(); }}>Retry</button></span></div>
      ) : projects.length === 0 ? (
        <div className="demo-notice"><span><strong>No projects yet.</strong> Create your first project to get started.</span></div>
      ) : null}

      {!loading && !error && (
        <>
          <div className="list-toolbar">
            <label className="search-field">
              <Icon name="search" size={18} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search projects" aria-label="Search projects" />
              {query && <button aria-label="Clear search" onClick={() => setQuery('')}><Icon name="close" size={15} /></button>}
            </label>
            <label className="toolbar-select">
              <Icon name="filter" size={16} />
              <span className="visually-hidden">Category filter</span>
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c === 'All' ? 'All categories' : c}</option>)}
              </select>
            </label>
            <span className="toolbar-count">{filtered.length} {filtered.length === 1 ? 'project' : 'projects'}</span>
          </div>

          {filtered.length ? (
            <div className="project-card-grid">
              {filtered.map((project, index) => (
                <article className="project-card" key={project.id}>
                  <div className="project-card-top">
                    <span className={`project-avatar project-avatar-large project-avatar-${index % 4}`}>
                      {project.name.slice(0, 1).toUpperCase()}
                    </span>
                    <Badge tone={project.archived_at ? 'neutral' : 'success'}>
                      {project.archived_at ? 'Archived' : 'Active'}
                    </Badge>
                    {project.category && <Badge tone="blue">{project.category}</Badge>}
                    <Link className="icon-button" href={`/projects/${project.id}`} aria-label={`Open ${project.name} details`}>
                      <Icon name="chevron" />
                    </Link>
                  </div>
                  <Link href={`/projects/${project.id}`} className="project-card-title">{project.name}</Link>
                  <p>{project.description || 'No description yet.'}</p>
                  {project.platform_type && <p style={{ fontSize: '0.78rem', opacity: 0.65, marginTop: 2 }}>{project.platform_type}</p>}
                  <div className="project-card-stats">
                    <span><Icon name="eye" size={15} />{project.audit_count ?? 0} audits</span>
                    <span><Icon name="image" size={15} />{project.screen_count ?? 0} screens</span>
                  </div>
                  <div className="project-card-bottom">
                    <span>Updated {formatDate(project.updated_at)}</span>
                    <Link href={`/projects/${project.id}`} aria-label={`Open ${project.name}`}><Icon name="arrow" size={17} /></Link>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="folder"
              title={projects.length ? 'No matching projects' : 'Create your first project'}
              description={projects.length ? 'Try a different search or category filter.' : 'Projects help keep your audits and reference material organised.'}
              action={!projects.length ? <Button onClick={() => setDialogOpen(true)} icon="plus">Create a project</Button> : undefined}
            />
          )}
        </>
      )}

      {dialogOpen && (
        <Modal
          title="Create a project"
          description="Start a workspace for a product, feature, or team initiative."
          onClose={() => { setDialogOpen(false); setCreateError(null); }}
          footer={
            <>
              <Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" form="create-project-form" icon="plus" disabled={creating}>
                {creating ? 'Creating…' : 'Create project'}
              </Button>
            </>
          }
        >
          <form id="create-project-form" className="form-grid modal-form" onSubmit={(e) => { void submitProject(e); }}>
            {createError && <div className="demo-notice" style={{ gridColumn: '1 / -1' }}><span><strong>Error</strong> {createError}</span></div>}
            <label className="form-field form-field-wide">
              <span>Project name</span>
              <input autoFocus required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Mobile onboarding" />
            </label>
            <label className="form-field form-field-wide">
              <span>Description <em>Optional</em></span>
              <textarea rows={3} maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What is this project about?" />
            </label>
            <label className="form-field">
              <span>Category <em>Optional</em></span>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">— Select —</option>
                {CATEGORIES.filter((c) => c !== 'All').map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label className="form-field">
              <span>Platform type <em>Optional</em></span>
              <input maxLength={100} value={platformType} onChange={(e) => setPlatformType(e.target.value)} placeholder="e.g. iOS, Web, Android" />
            </label>
          </form>
        </Modal>
      )}
    </div>
  );
}
