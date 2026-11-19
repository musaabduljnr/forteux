"""Add project history, activity events, and export jobs for Phase 09.

Revision ID: 0007_phase09_project_history_exports
Revises: 0006_design_system_extraction
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_phase09_project_history_exports"
down_revision = "0006_design_system_extraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ALTER projects: add new columns with batch mode for SQLite compatibility ---
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("platform_type", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_url", sa.String(900), nullable=True))
        batch_op.add_column(sa.Column("context_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))

    # --- ALTER audits: add new columns with batch mode for SQLite compatibility ---
    with op.batch_alter_table("audits") as batch_op:
        batch_op.add_column(sa.Column("version_number", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(
            sa.Column(
                "parent_job_id",
                sa.Uuid(as_uuid=True),
                sa.ForeignKey("analysis_jobs.id", ondelete="SET NULL", name="fk_audit_parent_job"),
                nullable=True,
            )
        )

    # --- CREATE TABLE project_activity_events ---
    op.create_table(
        "project_activity_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_activity_events_tenant_project_created",
        "project_activity_events",
        ["tenant_id", "project_id", "created_at"],
    )

    # --- CREATE TABLE export_jobs ---
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "audit_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("audits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("export_type", sa.String(80), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("file_content", sa.Text(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "export_type IN ('single_audit','multi_audit','design_system','stitch_prompt','project_package')",
            name="ck_export_job_type",
        ),
        sa.CheckConstraint(
            "format IN ('json','markdown','csv','zip')",
            name="ck_export_job_format",
        ),
        sa.CheckConstraint(
            "status IN ('pending','generating','completed','failed')",
            name="ck_export_job_status",
        ),
    )
    op.create_index(
        "ix_export_jobs_tenant_project_created",
        "export_jobs",
        ["tenant_id", "project_id", "created_at"],
    )


def downgrade() -> None:
    # Drop tables in reverse
    op.drop_index("ix_export_jobs_tenant_project_created", table_name="export_jobs")
    op.drop_table("export_jobs")

    op.drop_index("ix_project_activity_events_tenant_project_created", table_name="project_activity_events")
    op.drop_table("project_activity_events")

    # Drop columns from audits using batch mode
    with op.batch_alter_table("audits") as batch_op:
        batch_op.drop_column("parent_job_id")
        batch_op.drop_column("version_number")

    # Drop columns from projects using batch mode
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("archived_at")
        batch_op.drop_column("context_text")
        batch_op.drop_column("thumbnail_url")
        batch_op.drop_column("platform_type")
        batch_op.drop_column("category")
