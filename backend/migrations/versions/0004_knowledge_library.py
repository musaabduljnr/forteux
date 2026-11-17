"""Add knowledge library tables: knowledge_documents, document_versions, knowledge_chunks, finding_evidence.

Revision ID: 0004_knowledge_library
Revises: 0003_audit_prompts_and_versions
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_knowledge_library"
down_revision = "0003_audit_prompts_and_versions"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    # 1. knowledge_documents: top-level document record (one per logical document)
    op.create_table(
        "knowledge_documents",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "project_id",
            uuid_type,
            nullable=True,
            comment="NULL = global tenant library; set = project-specific"
        ),
        sa.Column("scope", sa.String(16), nullable=False, server_default="project"),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default="Uncategorised"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", uuid_type, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("active_version_id", uuid_type, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("scope IN ('global', 'project')", name="ck_knowledge_document_scope"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'validating', 'extracting', 'chunking', 'embedding', 'indexing', 'ready', 'failed', 'reprocessing', 'deleting', 'deleted')",
            name="ck_knowledge_document_status",
        ),
    )
    op.create_index("ix_knowledge_documents_tenant", "knowledge_documents", ["tenant_id"])
    op.create_index("ix_knowledge_documents_tenant_project", "knowledge_documents", ["tenant_id", "project_id"])
    op.create_index("ix_knowledge_documents_tenant_created", "knowledge_documents", ["tenant_id", "created_at"])

    # 2. document_versions: immutable per-upload version with extraction state
    op.create_table(
        "document_versions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("document_id", uuid_type, sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(900), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("extractor_version", sa.String(32), nullable=False, server_default="v1.0"),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("extraction_warnings", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('uploaded', 'extracting', 'chunking', 'embedding', 'ready', 'failed')",
            name="ck_document_version_status",
        ),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )
    op.create_index("ix_document_versions_document", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_sha256", "document_versions", ["sha256"])

    # 3. knowledge_chunks: extracted, chunked, and optionally embedded text passages
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", uuid_type, nullable=True),
        sa.Column("document_id", uuid_type, sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", uuid_type, sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_heading", sa.String(500), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        # Embedding stored as JSON array of floats — compatible with SQLite and PostgreSQL
        # On PostgreSQL with pgvector this column would be replaced by vector(N);
        # for now we store as Text and do cosine similarity in Python for dev/test.
        sa.Column("embedding_json", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_document_version", "knowledge_chunks", ["document_version_id"])
    op.create_index("ix_knowledge_chunks_tenant", "knowledge_chunks", ["tenant_id"])
    op.create_index("ix_knowledge_chunks_tenant_project", "knowledge_chunks", ["tenant_id", "project_id"])
    op.create_index("ix_knowledge_chunks_document_index", "knowledge_chunks", ["document_id", "chunk_index"])

    # 4. finding_evidence: source citations linking findings to retrieved knowledge chunks
    op.create_table(
        "finding_evidence",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("finding_id", uuid_type, sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", uuid_type, sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("document_display_name", sa.String(255), nullable=False),
        sa.Column("quote_or_paraphrase", sa.Text(), nullable=True),
        sa.Column("page_number_snapshot", sa.Integer(), nullable=True),
        sa.Column("section_heading_snapshot", sa.String(500), nullable=True),
        sa.Column("retrieval_score", sa.Float(), nullable=True),
        sa.Column("retrieval_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finding_evidence_finding", "finding_evidence", ["finding_id"])
    op.create_index("ix_finding_evidence_chunk", "finding_evidence", ["chunk_id"])

    # 5. deletion_tasks: tracks async document deletion cleanup
    op.create_table(
        "deletion_tasks",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("document_version_id", uuid_type, nullable=True),
        sa.Column("tenant_id", uuid_type, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("object_key", sa.String(900), nullable=True),
        sa.Column("chunks_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_deletion_task_status",
        ),
    )
    op.create_index("ix_deletion_tasks_document", "deletion_tasks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_deletion_tasks_document", table_name="deletion_tasks")
    op.drop_table("deletion_tasks")

    op.drop_index("ix_finding_evidence_chunk", table_name="finding_evidence")
    op.drop_index("ix_finding_evidence_finding", table_name="finding_evidence")
    op.drop_table("finding_evidence")

    op.drop_index("ix_knowledge_chunks_document_index", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_tenant_project", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_tenant", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_version", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_document_versions_sha256", table_name="document_versions")
    op.drop_index("ix_document_versions_document", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_knowledge_documents_tenant_created", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_tenant_project", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_tenant", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
