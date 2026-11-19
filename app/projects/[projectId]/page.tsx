'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useState, useEffect, type FormEvent } from 'react';
import { Icon } from '@/components/icons';
import { Badge, Button, EmptyState, Modal, PageHeader, SectionTitle } from '@/components/ui';
import type {
  ActivityEvent,
  AnalysisComparison,
  AnalysisVersion,
  AuditRead,
  ExportJob,
  ProjectFull,
} from '@/lib/types';

function formatDate(iso?: string | null) {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatBytes(bytes?: number | null) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type TabType = 'overview' | 'audits' | 'exports' | 'activity';

export default function ProjectWorkspacePage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();
  const projectId = params.projectId;

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [project, setProject] = useState<ProjectFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Audits & Versions state
  const [audits, setAudits] = useState<AuditRead[]>([]);
  const [selectedAuditForVersions, setSelectedAuditForVersions] = useState<AuditRead | null>(null);
  const [versions, setVersions] = useState<AnalysisVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [earlierJobId, setEarlierJobId] = useState<string>('');
  const [laterJobId, setLaterJobId] = useState<string>('');
  const [comparison, setComparison] = useState<AnalysisComparison | null>(null);
  const [comparing, setComparing] = useState(false);

  // Exports state
  const [exportsList, setExportsList] = useState<ExportJob[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportType, setExportType] = useState<'single_audit' | 'multi_audit' | 'design_system' | 'stitch_prompt' | 'project_package'>('project_package');
  const [exportFormat, setExportFormat] = useState<'json' | 'markdown' | 'csv' | 'zip'>('json');
  const [exportAuditId, setExportAuditId] = useState<string>('');
  const [generatingExport, setGeneratingExport] = useState(false);

  // Activity state
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);

  // Edit / Delete modals
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editPlatform, setEditPlatform] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    void loadProject();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    if (activeTab === 'audits') void loadAudits();
    if (activeTab === 'exports') void loadExports();
    if (activeTab === 'activity') void loadActivity();
  }, [activeTab, projectId]);

  async function loadProject() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/stats`);
      if (res.status === 404) {
        setError('Project not found');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ProjectFull = await res.json();
      setProject(data);
      setEditName(data.name);
      setEditDescription(data.description || '');
      setEditCategory(data.category || '');
      setEditPlatform(data.platform_type || '');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  }

  async function loadAudits() {
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/audits`);
      if (res.ok) {
        const data: AuditRead[] = await res.json();
        setAudits(data);
      }
    } catch {
      /* ignore */
    }
  }

  async function loadExports() {
    setExportsLoading(true);
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/exports`);
      if (res.ok) {
        const data: ExportJob[] = await res.json();
        setExportsList(data);
      }
    } catch {
      /* ignore */
    } finally {
      setExportsLoading(false);
    }
  }

  async function loadActivity() {
    setActivityLoading(true);
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/activity`);
      if (res.ok) {
        const data: ActivityEvent[] = await res.json();
        setActivity(data);
      }
    } catch {
      /* ignore */
    } finally {
      setActivityLoading(false);
    }
  }

  async function handleSaveProject(e: FormEvent) {
    e.preventDefault();
    if (!editName.trim()) return;
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName.trim(),
          description: editDescription.trim() || null,
          category: editCategory.trim() || null,
          platform_type: editPlatform.trim() || null,
        }),
      });
      if (res.ok) {
        const updated: ProjectFull = await res.json();
        setProject(updated);
        setEditing(false);
      }
    } catch {
      /* ignore */
    }
  }

  async function toggleArchive() {
    if (!project) return;
    const action = project.archived_at ? 'restore' : 'archive';
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/${action}`, { method: 'POST' });
      if (res.ok) {
        const updated: ProjectFull = await res.json();
        setProject(updated);
      }
    } catch {
      /* ignore */
    }
  }

  async function handleDeleteProject() {
    setDeleting(true);
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        router.push('/projects');
      }
    } catch {
      setDeleting(false);
    }
  }

  async function openVersionsModal(audit: AuditRead) {
    setSelectedAuditForVersions(audit);
    setVersionsLoading(true);
    setComparison(null);
    setEarlierJobId('');
    setLaterJobId('');
    try {
      const res = await fetch(`/api/backend/v1/projects/${projectId}/audits/${audit.id}/versions`);
      if (res.ok) {
        const data: AnalysisVersion[] = await res.json();
        setVersions(data);
        if (data.length >= 2) {
          setEarlierJobId(data[0].job_id);
          setLaterJobId(data[data.length - 1].job_id);
        }
      }
    } catch {
      /* ignore */
    } finally {
      setVersionsLoading(false);
    }
  }

  async function handleCompareVersions() {
    if (!selectedAuditForVersions || !earlierJobId || !laterJobId) return;
    setComparing(true);
    try {
      const res = await fetch(
        `/api/backend/v1/projects/${projectId}/audits/${selectedAuditForVersions.id}/versions/compare?earlier_job_id=${earlierJobId}&later_job_id=${laterJobId}`
      );
      if (res.ok) {
        const data: AnalysisComparison = await res.json();
        setComparison(data);
      }
    } catch {
      /* ignore */
    } finally {
      setComparing(false);
    }
  }

  async function handleCreateExport(e: FormEvent) {
    e.preventDefault();
    setGeneratingExport(true);
    try {
      const payload: { export_type: string; format: string; audit_id?: string } = {
        export_type: exportType,
        format: exportFormat,
      };
      if (exportType in ['single_audit', 'multi_audit'] || exportAuditId) {
        payload.audit_id = exportAuditId;
      }
      const res = await fetch(`/api/backend/v1/projects/${projectId}/exports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setExportModalOpen(false);
        void loadExports();
      }
    } catch {
      /* ignore */
    } finally {
      setGeneratingExport(false);
    }
  }

  function downloadExport(exportId: string) {
    window.open(`/api/backend/v1/projects/${projectId}/exports/${exportId}/download`, '_blank');
  }

  if (loading) {
    return (
      <div className="page-stack">
        <PageHeader eyebrow="Workspace" title="Loading project…" description="Retrieving project data." />
        <div className="panel" style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading workspace…</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="page-stack">
        <EmptyState
          icon="folder"
          title={error || 'Project not found'}
          description="This project could not be found or you may not have access."
          action={<Button href="/projects" variant="secondary">Back to projects</Button>}
        />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="project-detail-header">
        <div className="project-detail-mark">{project.name.slice(0, 1).toUpperCase()}</div>
        <PageHeader
          eyebrow={
            <span className="breadcrumb">
              <Link href="/projects">Projects</Link>
              <Icon name="chevron" size={14} />
              <span>Workspace</span>
            </span>
          }
          title={project.name}
          description={project.description || 'No project description.'}
          action={
            <div className="button-row">
              <Button variant="secondary" icon="edit" onClick={() => setEditing(true)}>Edit details</Button>
              <Button href="/audits/new" icon="plus">New audit</Button>
            </div>
          }
        />
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
        <Badge tone={project.archived_at ? 'neutral' : 'success'}>
          {project.archived_at ? 'Archived' : 'Active'}
        </Badge>
        {project.category && <Badge tone="blue">{project.category}</Badge>}
        {project.platform_type && <Badge tone="neutral">{project.platform_type}</Badge>}
      </div>

      {/* Tabs navigation */}
      <div className="history-toolbar" style={{ borderBottom: '1px solid var(--border-color, #e2e8f0)', paddingBottom: '0.5rem' }}>
        <div className="button-row">
          <Button variant={activeTab === 'overview' ? 'primary' : 'secondary'} onClick={() => setActiveTab('overview')}>Overview</Button>
          <Button variant={activeTab === 'audits' ? 'primary' : 'secondary'} onClick={() => setActiveTab('audits')}>Audits & History</Button>
          <Button variant={activeTab === 'exports' ? 'primary' : 'secondary'} onClick={() => setActiveTab('exports')}>Exports</Button>
          <Button variant={activeTab === 'activity' ? 'primary' : 'secondary'} onClick={() => setActiveTab('activity')}>Activity</Button>
        </div>
      </div>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (
        <>
          <div className="metrics-grid metrics-grid-three">
            <div className="mini-metric">
              <span>Audits</span>
              <strong>{project.audit_count ?? 0}</strong>
              <small>Completed & active runs</small>
            </div>
            <div className="mini-metric">
              <span>Screens</span>
              <strong>{project.screen_count ?? 0}</strong>
              <small>Analyzed across audits</small>
            </div>
            <div className="mini-metric">
              <span>Design systems</span>
              <strong>{project.design_system_count ?? 0}</strong>
              <small>Extracted token models</small>
            </div>
          </div>

          <section className="panel">
            <SectionTitle title="Project overview" description="Key properties and context for this workspace." />
            <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', padding: '1rem 0' }}>
              <div>
                <small style={{ textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em', opacity: 0.6 }}>Category</small>
                <p style={{ margin: '0.25rem 0', fontWeight: 500 }}>{project.category || 'Not specified'}</p>
              </div>
              <div>
                <small style={{ textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em', opacity: 0.6 }}>Platform</small>
                <p style={{ margin: '0.25rem 0', fontWeight: 500 }}>{project.platform_type || 'General'}</p>
              </div>
              <div>
                <small style={{ textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em', opacity: 0.6 }}>Created</small>
                <p style={{ margin: '0.25rem 0', fontWeight: 500 }}>{formatDate(project.created_at)}</p>
              </div>
              <div>
                <small style={{ textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em', opacity: 0.6 }}>Last Updated</small>
                <p style={{ margin: '0.25rem 0', fontWeight: 500 }}>{formatDate(project.updated_at)}</p>
              </div>
            </div>
            {project.context_text && (
              <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-color, #e2e8f0)', paddingTop: '1rem' }}>
                <small style={{ textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em', opacity: 0.6 }}>Project Context</small>
                <p style={{ margin: '0.5rem 0', lineHeight: 1.5 }}>{project.context_text}</p>
              </div>
            )}
          </section>

          <section className="panel">
            <SectionTitle
              title="Workspace actions"
              description="Manage project status and lifecycle."
            />
            <div className="button-row" style={{ marginTop: '1rem' }}>
              <Button variant="secondary" onClick={() => { void toggleArchive(); }}>
                {project.archived_at ? 'Restore from archive' : 'Archive project'}
              </Button>
              <Button href={`/design-system`} variant="secondary">View design systems</Button>
              <Button href={`/knowledge?project=${project.id}`} variant="secondary">Manage project references</Button>
            </div>
          </section>

          <section className="danger-zone">
            <div>
              <strong>Delete this project</strong>
              <p>Permanently removes this project, all associated screenshots, analyses, findings, and exports.</p>
            </div>
            <Button variant="danger" icon="trash" onClick={() => setConfirmDelete(true)}>Delete project</Button>
          </section>
        </>
      )}

      {/* AUDITS TAB */}
      {activeTab === 'audits' && (
        <section className="panel">
          <SectionTitle
            title="Project audits"
            description="Explore completed reviews, screen sequences, and version iterations."
            action={<Button href="/audits/new" icon="plus" variant="secondary">New audit</Button>}
          />
          {audits.length ? (
            <div className="table-scroll" style={{ marginTop: '1rem' }}>
              <table className="data-table history-table">
                <thead>
                  <tr>
                    <th>Audit name</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.map((a) => (
                    <tr key={a.id}>
                      <td>
                        <Link href={`/audits/${a.id}`} className="table-primary">{a.name}</Link>
                      </td>
                      <td>
                        <Badge tone={a.mode === 'multi' ? 'blue' : 'neutral'}>
                          {a.mode === 'multi' ? 'Multi-Screen' : 'Single Screen'}
                        </Badge>
                      </td>
                      <td>
                        <Badge tone={a.status === 'completed' ? 'success' : 'neutral'}>{a.status}</Badge>
                      </td>
                      <td>{formatDate(a.created_at)}</td>
                      <td>
                        <div className="button-row">
                          <Button variant="secondary" onClick={() => { void openVersionsModal(a); }}>Versions</Button>
                          <Link href={`/audits/${a.id}`} className="icon-button" aria-label={`Open ${a.name}`}><Icon name="arrow" size={16} /></Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon="eye"
              title="No audits in this project"
              description="Create an audit to review your product screens."
              action={<Button href="/audits/new" icon="plus">Create audit</Button>}
            />
          )}
        </section>
      )}

      {/* EXPORTS TAB */}
      {activeTab === 'exports' && (
        <section className="panel">
          <SectionTitle
            title="Export centre"
            description="Download structured reports, JSON design tokens, Markdown documentation, and CSVs."
            action={<Button icon="plus" onClick={() => setExportModalOpen(true)}>Create export</Button>}
          />
          {exportsLoading ? (
            <p style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading exports…</p>
          ) : exportsList.length ? (
            <div className="table-scroll" style={{ marginTop: '1rem' }}>
              <table className="data-table history-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Format</th>
                    <th>Status</th>
                    <th>Size</th>
                    <th>Generated</th>
                    <th>Download</th>
                  </tr>
                </thead>
                <tbody>
                  {exportsList.map((exp) => (
                    <tr key={exp.id}>
                      <td style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                        {exp.export_type.replace('_', ' ')}
                      </td>
                      <td><Badge tone="blue">{exp.format.toUpperCase()}</Badge></td>
                      <td><Badge tone={exp.status === 'completed' ? 'success' : 'neutral'}>{exp.status}</Badge></td>
                      <td>{formatBytes(exp.file_size)}</td>
                      <td>{formatDate(exp.created_at)}</td>
                      <td>
                        {exp.download_available ? (
                          <Button variant="secondary" onClick={() => downloadExport(exp.id)}>Download</Button>
                        ) : (
                          <span style={{ fontSize: '0.8rem', opacity: 0.5 }}>Pending</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon="file"
              title="No exports generated yet"
              description="Export your findings as Markdown, JSON tokens, or spreadsheets."
              action={<Button icon="plus" onClick={() => setExportModalOpen(true)}>Generate export</Button>}
            />
          )}
        </section>
      )}

      {/* ACTIVITY TAB */}
      {activeTab === 'activity' && (
        <section className="panel">
          <SectionTitle
            title="Project activity history"
            description="A timeline of creation, analysis, updates, and export actions for this project."
          />
          {activityLoading ? (
            <p style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading timeline…</p>
          ) : activity.length ? (
            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {activity.map((evt) => (
                <div
                  key={evt.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color, #e2e8f0)',
                  }}
                >
                  <div>
                    <span style={{ marginRight: '0.5rem', display: 'inline-block' }}>
                      <Badge tone="neutral">{evt.event_type.replace('_', ' ')}</Badge>
                    </span>
                    <span>{evt.description}</span>
                  </div>
                  <small style={{ opacity: 0.6 }}>{formatDate(evt.created_at)}</small>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="history"
              title="No recorded activity yet"
              description="Activity events will appear as actions occur in this project."
            />
          )}
        </section>
      )}

      {/* EDIT PROJECT MODAL */}
      {editing && (
        <Modal
          title="Edit project details"
          description="Update workspace properties, categories, and context."
          onClose={() => setEditing(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
              <Button type="submit" form="edit-project-form">Save changes</Button>
            </>
          }
        >
          <form id="edit-project-form" className="form-grid modal-form" onSubmit={(e) => { void handleSaveProject(e); }}>
            <label className="form-field form-field-wide">
              <span>Project name</span>
              <input autoFocus required maxLength={200} value={editName} onChange={(e) => setEditName(e.target.value)} />
            </label>
            <label className="form-field form-field-wide">
              <span>Description</span>
              <textarea rows={3} maxLength={500} value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
            </label>
            <label className="form-field">
              <span>Category</span>
              <input maxLength={100} value={editCategory} onChange={(e) => setEditCategory(e.target.value)} placeholder="e.g. Fintech, SaaS" />
            </label>
            <label className="form-field">
              <span>Platform</span>
              <input maxLength={100} value={editPlatform} onChange={(e) => setEditPlatform(e.target.value)} placeholder="e.g. Mobile, Web" />
            </label>
          </form>
        </Modal>
      )}

      {/* CONFIRM DELETE MODAL */}
      {confirmDelete && (
        <Modal
          title="Delete project?"
          description={`“${project.name}” and all its audits, findings, and files will be permanently marked deleted.`}
          onClose={() => setConfirmDelete(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setConfirmDelete(false)}>Keep project</Button>
              <Button variant="danger" icon="trash" disabled={deleting} onClick={() => { void handleDeleteProject(); }}>
                {deleting ? 'Deleting…' : 'Delete permanently'}
              </Button>
            </>
          }
        >
          <div className="confirmation-callout">
            <Icon name="warning" size={19} />
            <p><strong>Safeguard Notice:</strong> Deleting this project revokes access to all historical reports, versions, and generated prompts for this project.</p>
          </div>
        </Modal>
      )}

      {/* VERSIONS & COMPARISON MODAL */}
      {selectedAuditForVersions && (
        <Modal
          title={`Analysis Versions: ${selectedAuditForVersions.name}`}
          description="Review version iterations and compare findings between runs."
          onClose={() => setSelectedAuditForVersions(null)}
          footer={<Button variant="secondary" onClick={() => setSelectedAuditForVersions(null)}>Close</Button>}
        >
          {versionsLoading ? (
            <p style={{ padding: '1rem', textAlign: 'center' }}>Loading analysis runs…</p>
          ) : versions.length ? (
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <p style={{ fontSize: '0.88rem', opacity: 0.8, marginBottom: '0.5rem' }}>Select two runs to evaluate progression and detected changes:</p>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.85rem' }}>
                    Earlier:
                    <select value={earlierJobId} onChange={(e) => setEarlierJobId(e.target.value)} style={{ marginLeft: '0.25rem' }}>
                      {versions.map((v) => (
                        <option key={v.job_id} value={v.job_id}>v{v.version_number} ({formatDate(v.created_at)})</option>
                      ))}
                    </select>
                  </label>
                  <label style={{ fontSize: '0.85rem' }}>
                    Later:
                    <select value={laterJobId} onChange={(e) => setLaterJobId(e.target.value)} style={{ marginLeft: '0.25rem' }}>
                      {versions.map((v) => (
                        <option key={v.job_id} value={v.job_id}>v{v.version_number} ({formatDate(v.created_at)})</option>
                      ))}
                    </select>
                  </label>
                  <Button variant="secondary" onClick={() => { void handleCompareVersions(); }} disabled={comparing || !earlierJobId || !laterJobId}>
                    {comparing ? 'Comparing…' : 'Compare'}
                  </Button>
                </div>
              </div>

              {comparison && (
                <div style={{ padding: '1rem', background: 'var(--panel-subtle, #f8fafc)', borderRadius: '8px', border: '1px solid var(--border-color, #e2e8f0)', marginBottom: '1rem' }}>
                  <h4 style={{ margin: '0 0 0.5rem' }}>Version Comparison Result</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <div className="mini-metric" style={{ padding: '0.5rem' }}>
                      <span>New</span><strong>{comparison.new_findings.length}</strong>
                    </div>
                    <div className="mini-metric" style={{ padding: '0.5rem' }}>
                      <span>Resolved</span><strong>{comparison.resolved_findings.length}</strong>
                    </div>
                    <div className="mini-metric" style={{ padding: '0.5rem' }}>
                      <span>Persistent</span><strong>{comparison.persistent_findings.length}</strong>
                    </div>
                    <div className="mini-metric" style={{ padding: '0.5rem' }}>
                      <span>Severity Changes</span><strong>{comparison.changed_severity_findings.length}</strong>
                    </div>
                  </div>
                  {comparison.limitations?.length > 0 && (
                    <div style={{ fontSize: '0.78rem', opacity: 0.65, borderTop: '1px solid #cbd5e1', paddingTop: '0.5rem' }}>
                      <strong>Comparison Notes:</strong>
                      <ul style={{ margin: '0.25rem 0', paddingLeft: '1.25rem' }}>
                        {comparison.limitations.map((lim, idx) => <li key={idx}>{lim}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <table className="data-table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Issues Found</th>
                    <th>Model</th>
                    <th>Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((v) => (
                    <tr key={v.job_id}>
                      <td><strong>v{v.version_number}</strong></td>
                      <td><Badge tone={v.status === 'completed' ? 'success' : 'neutral'}>{v.status}</Badge></td>
                      <td>{v.finding_count}</td>
                      <td>{v.model}</td>
                      <td>{formatDate(v.completed_at || v.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ textAlign: 'center', opacity: 0.6 }}>No analysis runs recorded yet for this audit.</p>
          )}
        </Modal>
      )}

      {/* CREATE EXPORT MODAL */}
      {exportModalOpen && (
        <Modal
          title="Create new export"
          description="Select report type and format to generate an export package."
          onClose={() => setExportModalOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setExportModalOpen(false)}>Cancel</Button>
              <Button type="submit" form="create-export-form" disabled={generatingExport}>
                {generatingExport ? 'Generating…' : 'Generate export'}
              </Button>
            </>
          }
        >
          <form id="create-export-form" className="form-grid modal-form" onSubmit={(e) => { void handleCreateExport(e); }}>
            <label className="form-field form-field-wide">
              <span>Export type</span>
              <select value={exportType} onChange={(e) => setExportType(e.target.value as typeof exportType)}>
                <option value="project_package">Complete Project Package</option>
                <option value="single_audit">Single Screen Audit Report</option>
                <option value="multi_audit">Multi-Screen User Flow Report</option>
                <option value="design_system">Design System & Token Catalog</option>
                <option value="stitch_prompt">Google Stitch Prompt Specification</option>
              </select>
            </label>

            {['single_audit', 'multi_audit'].includes(exportType) && (
              <label className="form-field form-field-wide">
                <span>Select audit</span>
                <select required value={exportAuditId} onChange={(e) => setExportAuditId(e.target.value)}>
                  <option value="">— Select an audit —</option>
                  {audits.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.mode})</option>
                  ))}
                </select>
              </label>
            )}

            <label className="form-field form-field-wide">
              <span>Format</span>
              <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as typeof exportFormat)}>
                <option value="json">JSON (Structured Data)</option>
                <option value="markdown">Markdown (.md Document)</option>
                <option value="csv">CSV (Tabular Spreadsheet)</option>
                <option value="zip">ZIP Package Manifest</option>
              </select>
            </label>
          </form>
        </Modal>
      )}
    </div>
  );
}
