-- ==============================================================================
-- FORTEUX PRODUCTION ROW LEVEL SECURITY (RLS) POLICIES FOR SUPABASE POSTGRESQL
-- ==============================================================================
-- Purpose: Enforce defense-in-depth tenant isolation at the PostgreSQL engine level.
-- When users connect directly to Supabase PostgREST or Supabase client libraries,
-- these policies restrict all queries to the tenant identified in the JWT claims.
-- ==============================================================================

-- 1. Helper function to extract tenant_id from Supabase JWT claims
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid AS $$
BEGIN
    RETURN (NULLIF(current_setting('request.jwt.claims', true)::json->>'tenant_id', '')::uuid);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 2. Helper function to extract user_id from Supabase JWT claims
CREATE OR REPLACE FUNCTION current_user_id() RETURNS uuid AS $$
BEGIN
    RETURN (NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ==============================================================================
-- 3. ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- ==============================================================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_activity_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_screens ENABLE ROW LEVEL SECURITY;
ALTER TABLE screen_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE design_system_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE finding_evidence ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 4. SERVICE ROLE BYPASS POLICIES (FastAPI backend uses service_role key)
-- ==============================================================================

CREATE POLICY "service_role_all_tenants" ON tenants FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_users" ON users FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_memberships" ON memberships FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_projects" ON projects FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_events" ON project_activity_events FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_audits" ON audits FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_screens" ON audit_screens FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_assets" ON screen_assets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_jobs" ON analysis_jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_findings" ON findings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_prompts" ON audit_prompts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_design_systems" ON design_system_analyses FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_exports" ON export_jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_knowledge_docs" ON knowledge_documents FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_doc_versions" ON document_versions FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_chunks" ON knowledge_chunks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all_evidence" ON finding_evidence FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ==============================================================================
-- 5. AUTHENTICATED USER TENANT ISOLATION POLICIES
-- ==============================================================================

-- Tenants: Users can only select their own tenant
CREATE POLICY "tenant_member_read_tenant" ON tenants
    FOR SELECT TO authenticated
    USING (id = current_tenant_id());

-- Users: Users can read members of their own tenant
CREATE POLICY "tenant_member_read_users" ON users
    FOR SELECT TO authenticated
    USING (id IN (SELECT user_id FROM memberships WHERE tenant_id = current_tenant_id()));

-- Projects: Tenant members can read and create projects in their tenant
CREATE POLICY "tenant_projects_policy" ON projects
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Project Activity:
CREATE POLICY "tenant_events_policy" ON project_activity_events
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Audits:
CREATE POLICY "tenant_audits_policy" ON audits
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Screen Assets:
CREATE POLICY "tenant_assets_policy" ON screen_assets
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Findings: Join via audits
CREATE POLICY "tenant_findings_policy" ON findings
    FOR ALL TO authenticated
    USING (audit_id IN (SELECT id FROM audits WHERE tenant_id = current_tenant_id()))
    WITH CHECK (audit_id IN (SELECT id FROM audits WHERE tenant_id = current_tenant_id()));

-- Audit Prompts:
CREATE POLICY "tenant_prompts_policy" ON audit_prompts
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Design System Analyses: Join via audits
CREATE POLICY "tenant_design_system_policy" ON design_system_analyses
    FOR ALL TO authenticated
    USING (audit_id IN (SELECT id FROM audits WHERE tenant_id = current_tenant_id()))
    WITH CHECK (audit_id IN (SELECT id FROM audits WHERE tenant_id = current_tenant_id()));

-- Export Jobs:
CREATE POLICY "tenant_exports_policy" ON export_jobs
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Knowledge Documents & Chunks:
CREATE POLICY "tenant_knowledge_docs_policy" ON knowledge_documents
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY "tenant_knowledge_chunks_policy" ON knowledge_chunks
    FOR ALL TO authenticated
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- ==============================================================================
-- 6. PGVECTOR INDEXING EXTENSION DDL FOR SUPABASE
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- Note: When migrating knowledge_chunks from embedding_json TEXT to vector(768):
-- ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding vector(768);
-- CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
