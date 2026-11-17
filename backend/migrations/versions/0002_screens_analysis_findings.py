"""Add audit screens, image dimensions, analysis jobs, and findings.

Revision ID: 0002_screens_analysis_findings
Revises: 0001_foundation
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_screens_analysis_findings"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    # 1. Update screen_assets table with image dimensions and verified metadata
    op.add_column("screen_assets", sa.Column("width_px", sa.Integer(), nullable=True))
    op.add_column("screen_assets", sa.Column("height_px", sa.Integer(), nullable=True))
    op.add_column("screen_assets", sa.Column("orientation", sa.Integer(), nullable=True))
    op.add_column("screen_assets", sa.Column("sha256", sa.String(64), nullable=True))
    op.add_column("screen_assets", sa.Column("verified_mime_type", sa.String(100), nullable=True))

    # 2. Create audit_screens
    op.create_table(
        "audit_screens",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("audit_id", uuid_type, nullable=False),
        sa.Column("screen_asset_id", uuid_type, sa.ForeignKey("screen_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False, default=0),
        sa.Column("screen_label", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_audit_screen_audit_tenant",
        ),
        sa.UniqueConstraint("audit_id", "sequence_index", name="uq_audit_screen_sequence"),
    )
    op.create_index("ix_audit_screens_audit_sequence", "audit_screens", ["audit_id", "sequence_index"])

    # 3. Create analysis_jobs
    op.create_table(
        "analysis_jobs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("audit_id", uuid_type, nullable=False),
        sa.Column("screen_asset_id", uuid_type, sa.ForeignKey("screen_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_analysis_job_audit_tenant",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_analysis_job_status",
        ),
    )
    op.create_index("ix_analysis_jobs_audit_created", "analysis_jobs", ["audit_id", "created_at"])

    # 4. Create findings
    op.create_table(
        "findings",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("audit_id", uuid_type, nullable=False),
        sa.Column("screen_asset_id", uuid_type, sa.ForeignKey("screen_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analysis_job_id", uuid_type, sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("recommended_fix", sa.Text(), nullable=False),
        sa.Column("design_principle", sa.String(255), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("bounding_boxes_json", sa.Text(), nullable=False, default="[]"),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_finding_audit_tenant",
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_finding_severity",
        ),
        sa.CheckConstraint(
            "evidence_type IN ('observed', 'inferred')",
            name="ck_finding_evidence_type",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_finding_confidence_range",
        ),
    )
    op.create_index("ix_findings_audit_created", "findings", ["audit_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_findings_audit_created", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_analysis_jobs_audit_created", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_audit_screens_audit_sequence", table_name="audit_screens")
    op.drop_table("audit_screens")
    op.drop_column("screen_assets", "verified_mime_type")
    op.drop_column("screen_assets", "sha256")
    op.drop_column("screen_assets", "orientation")
    op.drop_column("screen_assets", "height_px")
    op.drop_column("screen_assets", "width_px")
