"""Add design_system_analyses table for Phase 08 Design System Extraction & Consistency.

Revision ID: 0006_design_system_extraction
Revises: 0005_multi_screen_flow
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_design_system_extraction"
down_revision = "0005_multi_screen_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "design_system_analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("audit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("audits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("consistency_score", sa.Float(), nullable=True),
        sa.Column("score_breakdown_json", sa.Text(), nullable=True),
        sa.Column("extraction_coverage", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("color_palette_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("typography_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("spacing_layout_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("shapes_surfaces_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("components_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("tokens_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("consistency_issues_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("recommendations_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("limitations_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("stitch_prompt", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(64), server_default="forteux-design-system-engine", nullable=False),
        sa.Column("model", sa.String(128), server_default="gemini-2.0-flash", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'analyzing', 'completed', 'failed')",
            name="ck_design_system_status",
        ),
    )
    op.create_index(
        "ix_design_system_tenant_project_audit",
        "design_system_analyses",
        ["tenant_id", "project_id", "audit_id"],
    )
    op.create_index(
        "ix_design_system_audit_created",
        "design_system_analyses",
        ["audit_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_design_system_audit_created", table_name="design_system_analyses")
    op.drop_index("ix_design_system_tenant_project_audit", table_name="design_system_analyses")
    op.drop_table("design_system_analyses")
