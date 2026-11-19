'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Icon } from '@/components/icons';
import { Badge, Button, EmptyState, PageHeader } from '@/components/ui';
import type { AuditRead, PaginatedAudits, ProjectFull } from '@/lib/types';

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

export default function HistoryPage() {
  const [audits, setAudits] = useState<AuditRead[]>([]);
  const [projectsMap, setProjectsMap] = useState<Record<string, string>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [mode, setMode] = useState('all');
  const [status, setStatus] = useState('all');
  const [sort, setSort] = useState('newest');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  useEffect(() => {
    void fetchHistory();
  }, [page, mode, status, sort]);

  async function loadProjects() {
    try {
      const res = await fetch('/api/backend/v1/projects');
      if (res.ok) {
        const data: ProjectFull[] = await res.json();
        const map: Record<string, string> = {};
        for (const p of data) {
          map[p.id] = p.name;
        }
        setProjectsMap(map);
      }
    } catch {
      /* ignore */
    }
  }

  async function fetchHistory() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        mode,
        status,
        sort,
      });
      const res = await fetch(`/api/backend/v1/projects/history?${params.toString()}`);
      if (res.status === 401) {
        setError('Please sign in to view audit history.');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: PaginatedAudits = await res.json();
      setAudits(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit history');
    } finally {
      setLoading(false);
    }
  }

  const filteredAudits = audits.filter((a) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const pName = projectsMap[a.project_id] || '';
    return a.name.toLowerCase().includes(q) || pName.toLowerCase().includes(q);
  });

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace"
        title="Audit history"
        description="Unified historical record of UI/UX audits and multi-screen flow analyses across all projects."
        action={<Button href="/audits/new" icon="plus">New audit</Button>}
      />

      <div className="history-toolbar">
        <label className="search-field history-search">
          <Icon name="search" size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search audits or projects"
            aria-label="Search audit history"
          />
          {query && (
            <button aria-label="Clear search" onClick={() => setQuery('')}>
              <Icon name="close" size={15} />
            </button>
          )}
        </label>

        <label className="toolbar-select">
          <Icon name="filter" size={16} />
          <span className="visually-hidden">Audit mode</span>
          <select value={mode} onChange={(e) => { setMode(e.target.value); setPage(1); }}>
            <option value="all">All modes</option>
            <option value="single">Single screen</option>
            <option value="multi">Multi-screen flow</option>
          </select>
        </label>

        <label className="toolbar-select">
          <span className="visually-hidden">Audit status</span>
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="all">All statuses</option>
            <option value="completed">Completed</option>
            <option value="draft">Draft</option>
            <option value="failed">Failed</option>
          </select>
        </label>

        <label className="toolbar-select">
          <span className="visually-hidden">Sort order</span>
          <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>

      <section className="panel history-panel">
        <div className="history-table-heading">
          <strong>{total} total {total === 1 ? 'audit' : 'audits'}</strong>
          <span>Showing page {page} of {totalPages}</span>
        </div>

        {loading ? (
          <p style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading history…</p>
        ) : error ? (
          <div className="demo-notice" style={{ margin: '1rem' }}>
            <span><strong>Notice</strong> {error}</span>
          </div>
        ) : filteredAudits.length ? (
          <>
            <div className="table-scroll">
              <table className="data-table history-table">
                <thead>
                  <tr>
                    <th>Audit name</th>
                    <th>Project</th>
                    <th>Mode</th>
                    <th>Date created</th>
                    <th>Status</th>
                    <th><span className="visually-hidden">Open</span></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAudits.map((audit) => (
                    <tr key={audit.id}>
                      <td>
                        <Link href={`/audits/${audit.id}`} className="table-primary">
                          {audit.name}
                        </Link>
                      </td>
                      <td>
                        <Link href={`/projects/${audit.project_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                          {projectsMap[audit.project_id] || 'View project'}
                        </Link>
                      </td>
                      <td>
                        <Badge tone={audit.mode === 'multi' ? 'blue' : 'neutral'}>
                          {audit.mode === 'multi' ? 'Multi-Screen' : 'Single Screen'}
                        </Badge>
                      </td>
                      <td>{formatDate(audit.created_at)}</td>
                      <td>
                        <Badge tone={audit.status === 'completed' ? 'success' : 'neutral'}>
                          {audit.status}
                        </Badge>
                      </td>
                      <td>
                        <Link href={`/audits/${audit.id}`} className="icon-button table-open" aria-label={`Open ${audit.name}`}>
                          <Icon name="arrow" size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderTop: '1px solid var(--border-color, #e2e8f0)' }}>
              <Button variant="secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                Previous
              </Button>
              <span style={{ fontSize: '0.85rem', opacity: 0.7 }}>
                Page {page} of {totalPages}
              </span>
              <Button variant="secondary" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                Next
              </Button>
            </div>
          </>
        ) : (
          <EmptyState
            icon="history"
            title={audits.length ? 'No audits match your search' : 'No audits found'}
            description={audits.length ? 'Try adjusting your search filters.' : 'Run your first screen audit to populate this history.'}
            action={<Button href="/audits/new" icon="plus">Create audit</Button>}
          />
        )}
      </section>
    </div>
  );
}
