BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(64) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_foundation

CREATE TABLE users (
    id UUID NOT NULL, 
    oidc_issuer VARCHAR(512) NOT NULL, 
    oidc_subject VARCHAR(255) NOT NULL, 
    email VARCHAR(320), 
    display_name VARCHAR(200), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    disabled_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_user_oidc_identity UNIQUE (oidc_issuer, oidc_subject)
);

CREATE TABLE tenants (
    id UUID NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    plan VARCHAR(40) NOT NULL, 
    status VARCHAR(24) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE memberships (
    tenant_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role VARCHAR(24) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (tenant_id, user_id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE projects (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    created_by UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_project_id_tenant UNIQUE (id, tenant_id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_projects_tenant_updated ON projects (tenant_id, updated_at);

CREATE TABLE audits (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    created_by UUID NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    mode VARCHAR(16) NOT NULL, 
    status VARCHAR(24) NOT NULL, 
    context_json TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_audit_mode CHECK (mode IN ('single', 'multi')), 
    CONSTRAINT fk_audit_project_tenant FOREIGN KEY(project_id, tenant_id) REFERENCES projects (id, tenant_id) ON DELETE RESTRICT, 
    CONSTRAINT uq_audit_id_tenant UNIQUE (id, tenant_id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_audits_tenant_project_created ON audits (tenant_id, project_id, created_at);

CREATE TABLE screen_assets (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    uploaded_by UUID NOT NULL, 
    object_key VARCHAR(900) NOT NULL, 
    original_filename VARCHAR(255) NOT NULL, 
    declared_content_type VARCHAR(100) NOT NULL, 
    declared_size BIGINT NOT NULL, 
    idempotency_key VARCHAR(128) NOT NULL, 
    status VARCHAR(32) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_screen_asset_status CHECK (status IN ('pending_upload', 'uploaded_unverified', 'deleting', 'deleted')), 
    CONSTRAINT ck_screen_asset_positive_size CHECK (declared_size > 0), 
    CONSTRAINT fk_screen_asset_project_tenant FOREIGN KEY(project_id, tenant_id) REFERENCES projects (id, tenant_id) ON DELETE RESTRICT, 
    CONSTRAINT uq_screen_asset_object_key UNIQUE (object_key), 
    CONSTRAINT uq_screen_asset_idempotency UNIQUE (uploaded_by, idempotency_key), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_screen_assets_tenant_project_created ON screen_assets (tenant_id, project_id, created_at);

INSERT INTO alembic_version (version_num) VALUES ('0001_foundation') RETURNING alembic_version.version_num;

-- Running upgrade 0001_foundation -> 0002_screens_analysis_findings

ALTER TABLE screen_assets ADD COLUMN width_px INTEGER;

ALTER TABLE screen_assets ADD COLUMN height_px INTEGER;

ALTER TABLE screen_assets ADD COLUMN orientation INTEGER;

ALTER TABLE screen_assets ADD COLUMN sha256 VARCHAR(64);

ALTER TABLE screen_assets ADD COLUMN verified_mime_type VARCHAR(100);

CREATE TABLE audit_screens (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    audit_id UUID NOT NULL, 
    screen_asset_id UUID NOT NULL, 
    sequence_index INTEGER NOT NULL, 
    screen_label VARCHAR(200), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_audit_screen_audit_tenant FOREIGN KEY(audit_id, tenant_id) REFERENCES audits (id, tenant_id) ON DELETE CASCADE, 
    CONSTRAINT uq_audit_screen_sequence UNIQUE (audit_id, sequence_index), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(screen_asset_id) REFERENCES screen_assets (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_screens_audit_sequence ON audit_screens (audit_id, sequence_index);

CREATE TABLE analysis_jobs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    audit_id UUID NOT NULL, 
    screen_asset_id UUID, 
    status VARCHAR(32) NOT NULL, 
    provider VARCHAR(64) NOT NULL, 
    model VARCHAR(128) NOT NULL, 
    summary TEXT, 
    error_message TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_analysis_job_audit_tenant FOREIGN KEY(audit_id, tenant_id) REFERENCES audits (id, tenant_id) ON DELETE CASCADE, 
    CONSTRAINT ck_analysis_job_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(screen_asset_id) REFERENCES screen_assets (id) ON DELETE SET NULL
);

CREATE INDEX ix_analysis_jobs_audit_created ON analysis_jobs (audit_id, created_at);

CREATE TABLE findings (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    audit_id UUID NOT NULL, 
    screen_asset_id UUID, 
    analysis_job_id UUID NOT NULL, 
    category VARCHAR(64) NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    description TEXT NOT NULL, 
    why_it_matters TEXT NOT NULL, 
    recommended_fix TEXT NOT NULL, 
    design_principle VARCHAR(255), 
    severity VARCHAR(32) NOT NULL, 
    confidence FLOAT NOT NULL, 
    evidence_type VARCHAR(32) NOT NULL, 
    evidence TEXT NOT NULL, 
    bounding_boxes_json TEXT NOT NULL, 
    limitations TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_finding_audit_tenant FOREIGN KEY(audit_id, tenant_id) REFERENCES audits (id, tenant_id) ON DELETE CASCADE, 
    CONSTRAINT ck_finding_severity CHECK (severity IN ('critical', 'high', 'medium', 'low')), 
    CONSTRAINT ck_finding_evidence_type CHECK (evidence_type IN ('observed', 'inferred')), 
    CONSTRAINT ck_finding_confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(screen_asset_id) REFERENCES screen_assets (id) ON DELETE SET NULL, 
    FOREIGN KEY(analysis_job_id) REFERENCES analysis_jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_findings_audit_created ON findings (audit_id, created_at);

UPDATE alembic_version SET version_num='0002_screens_analysis_findings' WHERE alembic_version.version_num = '0001_foundation';

-- Running upgrade 0002_screens_analysis_findings -> 0003_audit_prompts_and_versions

CREATE TABLE audit_prompts (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    audit_id UUID NOT NULL, 
    screen_asset_id UUID, 
    content TEXT NOT NULL, 
    original_generated_content TEXT NOT NULL, 
    selected_finding_ids_json TEXT DEFAULT '[]' NOT NULL, 
    user_instructions TEXT, 
    provider VARCHAR(64) DEFAULT 'forteux-prompt-engine' NOT NULL, 
    model VARCHAR(128) DEFAULT 'stitch-prompt-v1' NOT NULL, 
    template_version VARCHAR(32) DEFAULT 'v1.0' NOT NULL, 
    version_number INTEGER DEFAULT '1' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT fk_audit_prompt_audit_tenant FOREIGN KEY(audit_id, tenant_id) REFERENCES audits (id, tenant_id) ON DELETE CASCADE, 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(screen_asset_id) REFERENCES screen_assets (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_prompts_audit ON audit_prompts (audit_id);

CREATE INDEX ix_audit_prompts_tenant ON audit_prompts (tenant_id);

CREATE TABLE prompt_versions (
    id UUID NOT NULL, 
    prompt_id UUID NOT NULL, 
    version_number INTEGER NOT NULL, 
    content TEXT NOT NULL, 
    selected_finding_ids_json TEXT DEFAULT '[]' NOT NULL, 
    user_instructions TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(prompt_id) REFERENCES audit_prompts (id) ON DELETE CASCADE
);

CREATE INDEX ix_prompt_versions_prompt ON prompt_versions (prompt_id, version_number);

UPDATE alembic_version SET version_num='0003_audit_prompts_and_versions' WHERE alembic_version.version_num = '0002_screens_analysis_findings';

-- Running upgrade 0003_audit_prompts_and_versions -> 0004_knowledge_library

CREATE TABLE knowledge_documents (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID, 
    scope VARCHAR(16) DEFAULT 'project' NOT NULL, 
    display_name VARCHAR(255) NOT NULL, 
    category VARCHAR(100) DEFAULT 'Uncategorised' NOT NULL, 
    description TEXT, 
    uploaded_by UUID NOT NULL, 
    active_version_id UUID, 
    status VARCHAR(32) DEFAULT 'uploaded' NOT NULL, 
    error_message TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_knowledge_document_scope CHECK (scope IN ('global', 'project')), 
    CONSTRAINT ck_knowledge_document_status CHECK (status IN ('uploaded', 'validating', 'extracting', 'chunking', 'embedding', 'indexing', 'ready', 'failed', 'reprocessing', 'deleting', 'deleted')), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE RESTRICT
);

COMMENT ON COLUMN knowledge_documents.project_id IS 'NULL = global tenant library; set = project-specific';

CREATE INDEX ix_knowledge_documents_tenant ON knowledge_documents (tenant_id);

CREATE INDEX ix_knowledge_documents_tenant_project ON knowledge_documents (tenant_id, project_id);

CREATE INDEX ix_knowledge_documents_tenant_created ON knowledge_documents (tenant_id, created_at);

CREATE TABLE document_versions (
    id UUID NOT NULL, 
    document_id UUID NOT NULL, 
    version_number INTEGER NOT NULL, 
    object_key VARCHAR(900) NOT NULL, 
    original_filename VARCHAR(255) NOT NULL, 
    mime_type VARCHAR(100) NOT NULL, 
    byte_size BIGINT NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    page_count INTEGER, 
    chunk_count INTEGER, 
    extractor_version VARCHAR(32) DEFAULT 'v1.0' NOT NULL, 
    embedding_model VARCHAR(128), 
    status VARCHAR(32) DEFAULT 'uploaded' NOT NULL, 
    extraction_warnings TEXT, 
    error_message TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    processed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_document_version_status CHECK (status IN ('uploaded', 'extracting', 'chunking', 'embedding', 'ready', 'failed')), 
    CONSTRAINT uq_document_version UNIQUE (document_id, version_number), 
    FOREIGN KEY(document_id) REFERENCES knowledge_documents (id) ON DELETE CASCADE
);

CREATE INDEX ix_document_versions_document ON document_versions (document_id);

CREATE INDEX ix_document_versions_sha256 ON document_versions (sha256);

CREATE TABLE knowledge_chunks (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID, 
    document_id UUID NOT NULL, 
    document_version_id UUID NOT NULL, 
    chunk_index INTEGER NOT NULL, 
    text TEXT NOT NULL, 
    page_start INTEGER, 
    page_end INTEGER, 
    section_heading VARCHAR(500), 
    char_count INTEGER NOT NULL, 
    embedding_json TEXT, 
    embedding_model VARCHAR(128), 
    embedding_dimensions INTEGER, 
    metadata_json TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(document_id) REFERENCES knowledge_documents (id) ON DELETE CASCADE, 
    FOREIGN KEY(document_version_id) REFERENCES document_versions (id) ON DELETE CASCADE
);

CREATE INDEX ix_knowledge_chunks_document_version ON knowledge_chunks (document_version_id);

CREATE INDEX ix_knowledge_chunks_tenant ON knowledge_chunks (tenant_id);

CREATE INDEX ix_knowledge_chunks_tenant_project ON knowledge_chunks (tenant_id, project_id);

CREATE INDEX ix_knowledge_chunks_document_index ON knowledge_chunks (document_id, chunk_index);

CREATE TABLE finding_evidence (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    finding_id UUID NOT NULL, 
    chunk_id UUID NOT NULL, 
    document_id UUID NOT NULL, 
    document_display_name VARCHAR(255) NOT NULL, 
    quote_or_paraphrase TEXT, 
    page_number_snapshot INTEGER, 
    section_heading_snapshot VARCHAR(500), 
    retrieval_score FLOAT, 
    retrieval_rank INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(finding_id) REFERENCES findings (id) ON DELETE CASCADE, 
    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks (id) ON DELETE CASCADE
);

CREATE INDEX ix_finding_evidence_finding ON finding_evidence (finding_id);

CREATE INDEX ix_finding_evidence_chunk ON finding_evidence (chunk_id);

CREATE TABLE deletion_tasks (
    id UUID NOT NULL, 
    document_id UUID NOT NULL, 
    document_version_id UUID, 
    tenant_id UUID NOT NULL, 
    status VARCHAR(32) DEFAULT 'pending' NOT NULL, 
    object_key VARCHAR(900), 
    chunks_deleted INTEGER DEFAULT '0' NOT NULL, 
    error_message TEXT, 
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_deletion_task_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
);

CREATE INDEX ix_deletion_tasks_document ON deletion_tasks (document_id);

UPDATE alembic_version SET version_num='0004_knowledge_library' WHERE alembic_version.version_num = '0003_audit_prompts_and_versions';

-- Running upgrade 0004_knowledge_library -> 0005_multi_screen_flow

ALTER TABLE audit_screens ADD COLUMN screen_description TEXT;

ALTER TABLE analysis_jobs ADD COLUMN flow_report_json TEXT;

ALTER TABLE findings ADD COLUMN scope VARCHAR(16) DEFAULT 'screen_level' NOT NULL;

ALTER TABLE findings ADD COLUMN affected_screen_ids_json TEXT DEFAULT '[]' NOT NULL;

UPDATE alembic_version SET version_num='0005_multi_screen_flow' WHERE alembic_version.version_num = '0004_knowledge_library';

-- Running upgrade 0005_multi_screen_flow -> 0006_design_system_extraction

CREATE TABLE design_system_analyses (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    audit_id UUID NOT NULL, 
    status VARCHAR(32) DEFAULT 'pending' NOT NULL, 
    consistency_score FLOAT, 
    score_breakdown_json TEXT, 
    extraction_coverage FLOAT, 
    confidence FLOAT, 
    summary TEXT, 
    color_palette_json TEXT DEFAULT '[]' NOT NULL, 
    typography_json TEXT DEFAULT '[]' NOT NULL, 
    spacing_layout_json TEXT DEFAULT '{}' NOT NULL, 
    shapes_surfaces_json TEXT DEFAULT '{}' NOT NULL, 
    components_json TEXT DEFAULT '[]' NOT NULL, 
    tokens_json TEXT DEFAULT '[]' NOT NULL, 
    consistency_issues_json TEXT DEFAULT '[]' NOT NULL, 
    recommendations_json TEXT DEFAULT '[]' NOT NULL, 
    limitations_json TEXT DEFAULT '[]' NOT NULL, 
    stitch_prompt TEXT, 
    provider VARCHAR(64) DEFAULT 'forteux-design-system-engine' NOT NULL, 
    model VARCHAR(128) DEFAULT 'gemini-2.0-flash' NOT NULL, 
    error_message TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_design_system_status CHECK (status IN ('pending', 'analyzing', 'completed', 'failed')), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT, 
    FOREIGN KEY(audit_id) REFERENCES audits (id) ON DELETE CASCADE
);

CREATE INDEX ix_design_system_tenant_project_audit ON design_system_analyses (tenant_id, project_id, audit_id);

CREATE INDEX ix_design_system_audit_created ON design_system_analyses (audit_id, created_at);

UPDATE alembic_version SET version_num='0006_design_system_extraction' WHERE alembic_version.version_num = '0005_multi_screen_flow';

-- Running upgrade 0006_design_system_extraction -> 0007_phase09_project_history_exports

ALTER TABLE projects ADD COLUMN category VARCHAR(100);

ALTER TABLE projects ADD COLUMN platform_type VARCHAR(100);

ALTER TABLE projects ADD COLUMN thumbnail_url VARCHAR(900);

ALTER TABLE projects ADD COLUMN context_text TEXT;

ALTER TABLE projects ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE audits ADD COLUMN version_number INTEGER DEFAULT '1' NOT NULL;

ALTER TABLE audits ADD COLUMN parent_job_id UUID;

ALTER TABLE audits ADD CONSTRAINT fk_audit_parent_job FOREIGN KEY(parent_job_id) REFERENCES analysis_jobs (id) ON DELETE SET NULL;

CREATE TABLE project_activity_events (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    event_type VARCHAR(80) NOT NULL, 
    resource_id UUID, 
    resource_type VARCHAR(80), 
    description TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_activity_events_tenant_project_created ON project_activity_events (tenant_id, project_id, created_at);

CREATE TABLE export_jobs (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    project_id UUID NOT NULL, 
    audit_id UUID, 
    created_by UUID NOT NULL, 
    export_type VARCHAR(80) NOT NULL, 
    format VARCHAR(20) NOT NULL, 
    status VARCHAR(24) DEFAULT 'pending' NOT NULL, 
    file_content TEXT, 
    file_size INTEGER, 
    error_message TEXT, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_export_job_type CHECK (export_type IN ('single_audit','multi_audit','design_system','stitch_prompt','project_package')), 
    CONSTRAINT ck_export_job_format CHECK (format IN ('json','markdown','csv','zip')), 
    CONSTRAINT ck_export_job_status CHECK (status IN ('pending','generating','completed','failed')), 
    FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT, 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
    FOREIGN KEY(audit_id) REFERENCES audits (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_export_jobs_tenant_project_created ON export_jobs (tenant_id, project_id, created_at);

UPDATE alembic_version SET version_num='0007_phase09_project_history_exports' WHERE alembic_version.version_num = '0006_design_system_extraction';

COMMIT;

