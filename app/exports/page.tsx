'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Icon } from '@/components/icons';
import { Badge, Button, EmptyState, PageHeader } from '@/components/ui';
import type { ExportJob, ProjectFull } from '@/lib/types';

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

interface ExportItemWithProject extends ExportJob {
  projectName?: string;
}

export default function ExportCentrePage() {
  const [exportsList, setExportsList] = useState<ExportItemWithProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formatFilter, setFormatFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    void loadAllExports();
  }, []);

  async function loadAllExports() {
    setLoading(true);
    setError(null);
    try {
      const projRes = await fetch('/api/backend/v1/projects');
      if (projRes.status === 401) {
        setError('Please sign in to view your exports.');
        return;
      }
      if (!projRes.ok) throw new Error(`HTTP ${projRes.status}`);
      const projects: ProjectFull[] = await projRes.json();

      const allItems: ExportItemWithProject[] = [];
      await Promise.all(
        projects.slice(0, 15).map(async (p) => {
          try {
            const expRes = await fetch(`/api/backend/v1/projects/${p.id}/exports`);
            if (expRes.ok) {
              const jobs: ExportJob[] = await expRes.json();
              for (const j of jobs) {
                allItems.push({ ...j, projectName: p.name });
              }
            }
          } catch {
            /* ignore individual project export failure */
          }
        })
      );

      allItems.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setExportsList(allItems);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load exports');
    } finally {
      setLoading(false);
    }
  }

  function handleDownload(item: ExportItemWithProject) {
    window.open(`/api/backend/v1/projects/${item.project_id}/exports/${item.id}/download`, '_blank');
  }

  const filtered = exportsList.filter((item) => {
    if (formatFilter !== 'all' && item.format !== formatFilter) return false;
    if (typeFilter !== 'all' && item.export_type !== typeFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchProject = item.projectName?.toLowerCase().includes(q);
      const matchType = item.export_type.toLowerCase().includes(q);
      if (!matchProject && !matchType) return false;
    }
    return true;
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace"
        title="Export Centre"
        description="Access and download generated report documents, design tokens, and analysis archives."
      />

      <div className="history-toolbar">
        <label className="search-field history-search">
          <Icon name="search" size={18} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by project or report type"
            aria-label="Search exports"
          />
          {search && (
            <button aria-label="Clear search" onClick={() => setSearch('')}>
              <Icon name="close" size={15} />
            </button>
          )}
        </label>

        <label className="toolbar-select">
          <Icon name="filter" size={16} />
          <span className="visually-hidden">Format</span>
          <select value={formatFilter} onChange={(e) => setFormatFilter(e.target.value)}>
            <option value="all">All Formats</option>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
            <option value="csv">CSV</option>
            <option value="zip">ZIP Manifest</option>
          </select>
        </label>

        <label className="toolbar-select">
          <span className="visually-hidden">Type</span>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="all">All Types</option>
            <option value="single_audit">Single Screen Audit</option>
            <option value="multi_audit">Multi-Screen User Flow</option>
            <option value="design_system">Design System</option>
            <option value="stitch_prompt">Stitch Prompt</option>
            <option value="project_package">Project Package</option>
          </select>
        </label>
      </div>

      <section className="panel history-panel">
        <div className="history-table-heading">
          <strong>{filtered.length} {filtered.length === 1 ? 'export' : 'exports'}</strong>
          <span>Ready for download</span>
        </div>

        {loading ? (
          <p style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading export records…</p>
        ) : error ? (
          <div className="demo-notice" style={{ margin: '1rem' }}>
            <span><strong>Notice</strong> {error}</span>
          </div>
        ) : filtered.length ? (
          <div className="table-scroll">
            <table className="data-table history-table">
              <thead>
                <tr>
                  <th>Report Type</th>
                  <th>Project</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Size</th>
                  <th>Generated</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((exp) => (
                  <tr key={exp.id}>
                    <td style={{ fontWeight: 500, textTransform: 'capitalize' }}>
                      {exp.export_type.replace('_', ' ')}
                    </td>
                    <td>
                      <Link href={`/projects/${exp.project_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                        {exp.projectName || 'View Project'}
                      </Link>
                    </td>
                    <td>
                      <Badge tone="blue">{exp.format.toUpperCase()}</Badge>
                    </td>
                    <td>
                      <Badge tone={exp.status === 'completed' ? 'success' : 'neutral'}>
                        {exp.status}
                      </Badge>
                    </td>
                    <td>{formatBytes(exp.file_size)}</td>
                    <td>{formatDate(exp.created_at)}</td>
                    <td>
                      {exp.download_available ? (
                        <Button variant="secondary" onClick={() => handleDownload(exp)}>
                          Download
                        </Button>
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
            title={exportsList.length ? 'No matching exports' : 'No exports generated yet'}
            description={
              exportsList.length
                ? 'Try adjusting your format or type filters.'
                : 'Open any project and generate an export from the Exports tab.'
            }
            action={<Button href="/projects">Go to Projects</Button>}
          />
        )}
      </section>
    </div>
  );
}
