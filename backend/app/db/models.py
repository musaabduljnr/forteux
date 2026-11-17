from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oidc_issuer", "oidc_subject", name="uq_user_oidc_identity"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    oidc_issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    oidc_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="personal", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(24), default="owner", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_project_id_tenant"),
        Index("ix_projects_tenant_updated", "tenant_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="RESTRICT",
            name="fk_audit_project_tenant",
        ),
        UniqueConstraint("id", "tenant_id", name="uq_audit_id_tenant"),
        CheckConstraint("mode IN ('single', 'multi')", name="ck_audit_mode"),
        Index("ix_audits_tenant_project_created", "tenant_id", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    context_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScreenAsset(Base):
    __tablename__ = "screen_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="RESTRICT",
            name="fk_screen_asset_project_tenant",
        ),
        UniqueConstraint("object_key", name="uq_screen_asset_object_key"),
        Index("ix_screen_assets_tenant_project_created", "tenant_id", "project_id", "created_at"),
        CheckConstraint(
            "status IN ('pending_upload', 'uploaded_unverified', 'uploaded_verified', 'deleting', 'deleted')",
            name="ck_screen_asset_status",
        ),
        UniqueConstraint("uploaded_by", "idempotency_key", name="uq_screen_asset_idempotency"),
        CheckConstraint("declared_size > 0", name="ck_screen_asset_positive_size"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    uploaded_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    object_key: Mapped[str] = mapped_column(String(900), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    declared_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_upload", nullable=False)

    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    orientation: Mapped[int | None] = mapped_column(Integer, default=1)
    sha256: Mapped[str | None] = mapped_column(String(64))
    verified_mime_type: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditScreen(Base):
    __tablename__ = "audit_screens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_audit_screen_audit_tenant",
        ),
        ForeignKeyConstraint(
            ["screen_asset_id"],
            ["screen_assets.id"],
            ondelete="CASCADE",
            name="fk_audit_screen_asset",
        ),
        UniqueConstraint("audit_id", "sequence_index", name="uq_audit_screen_sequence"),
        Index("ix_audit_screens_audit_sequence", "audit_id", "sequence_index"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    screen_asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    screen_label: Mapped[str | None] = mapped_column(String(200))
    screen_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_analysis_job_audit_tenant",
        ),
        Index("ix_analysis_jobs_audit_created", "audit_id", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_analysis_job_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    screen_asset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("screen_assets.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    flow_report_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_finding_audit_tenant",
        ),
        ForeignKeyConstraint(
            ["analysis_job_id"],
            ["analysis_jobs.id"],
            ondelete="CASCADE",
            name="fk_finding_job",
        ),
        Index("ix_findings_audit_created", "audit_id", "created_at"),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_finding_severity",
        ),
        CheckConstraint(
            "evidence_type IN ('observed', 'inferred')",
            name="ck_finding_evidence_type",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_finding_confidence_range",
        ),
        CheckConstraint(
            "scope IN ('screen_level', 'cross_screen')",
            name="ck_finding_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    screen_asset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("screen_assets.id", ondelete="SET NULL"))
    analysis_job_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)

    scope: Mapped[str] = mapped_column(String(16), default="screen_level", nullable=False)
    affected_screen_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_fix: Mapped[str] = mapped_column(Text, nullable=False)
    design_principle: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    bounding_boxes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    limitations: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditPrompt(Base):
    __tablename__ = "audit_prompts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_audit_prompt_audit_tenant",
        ),
        Index("ix_audit_prompts_audit", "audit_id"),
        Index("ix_audit_prompts_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    screen_asset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("screen_assets.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    original_generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    selected_finding_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    user_instructions: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="forteux-prompt-engine")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="stitch-prompt-v1")
    template_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["prompt_id"],
            ["audit_prompts.id"],
            ondelete="CASCADE",
            name="fk_prompt_version_prompt",
        ),
        Index("ix_prompt_versions_prompt", "prompt_id", "version_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    prompt_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    selected_finding_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    user_instructions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_knowledge_documents_tenant", "tenant_id"),
        Index("ix_knowledge_documents_tenant_project", "tenant_id", "project_id"),
        Index("ix_knowledge_documents_tenant_created", "tenant_id", "created_at"),
        CheckConstraint("scope IN ('global', 'project')", name="ck_knowledge_document_scope"),
        CheckConstraint(
            "status IN ('uploaded', 'validating', 'extracting', 'chunking', 'embedding', 'indexing', 'ready', 'failed', 'reprocessing', 'deleting', 'deleted')",
            name="ck_knowledge_document_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    scope: Mapped[str] = mapped_column(String(16), default="project", nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Uncategorised", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    active_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version"),
        Index("ix_document_versions_document", "document_id"),
        Index("ix_document_versions_sha256", "sha256"),
        CheckConstraint(
            "status IN ('uploaded', 'extracting', 'chunking', 'embedding', 'ready', 'failed')",
            name="ck_document_version_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(900), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    extractor_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    extraction_warnings: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[KnowledgeDocument] = relationship(back_populates="versions")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="version", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_document_version", "document_version_id"),
        Index("ix_knowledge_chunks_tenant", "tenant_id"),
        Index("ix_knowledge_chunks_tenant_project", "tenant_id", "project_id"),
        Index("ix_knowledge_chunks_document_index", "document_id", "chunk_index"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_heading: Mapped[str | None] = mapped_column(String(500))
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
    version: Mapped[DocumentVersion] = relationship(back_populates="chunks")


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"
    __table_args__ = (
        Index("ix_finding_evidence_finding", "finding_id"),
        Index("ix_finding_evidence_chunk", "chunk_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_or_paraphrase: Mapped[str | None] = mapped_column(Text)
    page_number_snapshot: Mapped[int | None] = mapped_column(Integer)
    section_heading_snapshot: Mapped[str | None] = mapped_column(String(500))
    retrieval_score: Mapped[float | None] = mapped_column(Float)
    retrieval_rank: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DeletionTask(Base):
    __tablename__ = "deletion_tasks"
    __table_args__ = (
        Index("ix_deletion_tasks_document", "document_id"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_deletion_task_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(900))
    chunks_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DesignSystemAnalysis(Base):
    __tablename__ = "design_system_analyses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_design_system_tenant",
        ),
        ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="RESTRICT",
            name="fk_design_system_project",
        ),
        ForeignKeyConstraint(
            ["audit_id"],
            ["audits.id"],
            ondelete="CASCADE",
            name="fk_design_system_audit",
        ),
        Index("ix_design_system_tenant_project_audit", "tenant_id", "project_id", "audit_id"),
        Index("ix_design_system_audit_created", "audit_id", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'analyzing', 'completed', 'failed')",
            name="ck_design_system_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    consistency_score: Mapped[float | None] = mapped_column(Float)
    score_breakdown_json: Mapped[str | None] = mapped_column(Text)
    extraction_coverage: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)

    color_palette_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    typography_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    spacing_layout_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    shapes_surfaces_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    components_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    tokens_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    consistency_issues_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    stitch_prompt: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[str] = mapped_column(String(64), default="forteux-design-system-engine", nullable=False)
    model: Mapped[str] = mapped_column(String(128), default="gemini-2.0-flash", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
