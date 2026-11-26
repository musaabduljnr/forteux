-- ==============================================================================
-- FORTEUX TABLE PRIVILEGES FOR AUTHENTICATED & ANON ROLES
-- ==============================================================================
-- RLS policies control ROW-level access, but Postgres table-level GRANTs must
-- also exist or PostgREST returns "permission denied for table <name>".
-- This migration adds the minimum required grants on every public table.
-- RLS policies on each table continue to enforce per-user row isolation.
-- ==============================================================================

-- ── profiles ─────────────────────────────────────────────────────────────────
-- Users read/write their own row (RLS: auth.uid() = id)
GRANT SELECT, INSERT, UPDATE ON public.profiles TO authenticated;

-- ── projects ─────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.projects TO authenticated;

-- ── audits ───────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audits TO authenticated;

-- ── audit_screens ─────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audit_screens TO authenticated;

-- ── findings ─────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.findings TO authenticated;

-- ── finding_evidence ─────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.finding_evidence TO authenticated;

-- ── analysis_jobs ─────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON public.analysis_jobs TO authenticated;

-- ── design_system_analyses ───────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON public.design_system_analyses TO authenticated;

-- ── export_jobs ───────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON public.export_jobs TO authenticated;

-- ── audit_prompts ─────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON public.audit_prompts TO authenticated;

-- ── prompt_versions ───────────────────────────────────────────────────────────
GRANT SELECT, INSERT ON public.prompt_versions TO authenticated;

-- ── knowledge_documents ───────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.knowledge_documents TO authenticated;

-- ── knowledge_chunks ──────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.knowledge_chunks TO authenticated;

-- ── document_versions ─────────────────────────────────────────────────────────
GRANT SELECT, INSERT ON public.document_versions TO authenticated;

-- ── screen_assets ─────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON public.screen_assets TO authenticated;

-- ── tenants ───────────────────────────────────────────────────────────────────
GRANT SELECT ON public.tenants TO authenticated;

-- ── memberships ───────────────────────────────────────────────────────────────
GRANT SELECT ON public.memberships TO authenticated;

-- ── project_activity_events ───────────────────────────────────────────────────
GRANT SELECT, INSERT ON public.project_activity_events TO authenticated;

-- ── deletion_tasks ────────────────────────────────────────────────────────────
GRANT SELECT, INSERT ON public.deletion_tasks TO authenticated;

-- ── users (app-level shadow of auth.users, if used) ──────────────────────────
GRANT SELECT ON public.users TO authenticated;

-- ── alembic_version (backend migration tracking — no frontend access needed) ─
-- No grant needed for authenticated/anon

-- ── Sequences (for serial/bigserial PKs if any) ───────────────────────────────
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
