"""Add audit prompts and prompt versions tables.

Revision ID: 0003_audit_prompts_and_versions
Revises: 0002_screens_analysis_findings
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_audit_prompts_and_versions"
down_revision = "0002_screens_analysis_findings"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    # 1. Create audit_prompts
    op.create_table(
        "audit_prompts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("audit_id", uuid_type, nullable=False),
        sa.Column("screen_asset_id", uuid_type, sa.ForeignKey("screen_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("original_generated_content", sa.Text(), nullable=False),
        sa.Column("selected_finding_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("user_instructions", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False, server_default="forteux-prompt-engine"),
        sa.Column("model", sa.String(128), nullable=False, server_default="stitch-prompt-v1"),
        sa.Column("template_version", sa.String(32), nullable=False, server_default="v1.0"),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["audit_id", "tenant_id"],
            ["audits.id", "audits.tenant_id"],
            ondelete="CASCADE",
            name="fk_audit_prompt_audit_tenant",
        ),
    )
    op.create_index("ix_audit_prompts_audit", "audit_prompts", ["audit_id"])
    op.create_index("ix_audit_prompts_tenant", "audit_prompts", ["tenant_id"])

    # 2. Create prompt_versions
    op.create_table(
        "prompt_versions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("prompt_id", uuid_type, sa.ForeignKey("audit_prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("selected_finding_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("user_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_versions_prompt", "prompt_versions", ["prompt_id", "version_number"])


def downgrade() -> None:
    op.drop_index("ix_prompt_versions_prompt", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_audit_prompts_tenant", table_name="audit_prompts")
    op.drop_index("ix_audit_prompts_audit", table_name="audit_prompts")
    op.drop_table("audit_prompts")
