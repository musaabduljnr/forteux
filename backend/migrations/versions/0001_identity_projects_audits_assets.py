"""Create identity, project, audit, and asset ownership tables.

Revision ID: 0001_foundation
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

uuid_type = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("oidc_issuer", sa.String(512), nullable=False),
        sa.Column("oidc_subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("display_name", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("oidc_issuer", "oidc_subject", name="uq_user_oidc_identity"),
    )
    op.create_table(
        "tenants",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("plan", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("id", "tenant_id", name="uq_project_id_tenant"),
    )
    op.create_index("ix_projects_tenant_updated", "projects", ["tenant_id", "updated_at"])
    op.create_table(
        "audits",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("created_by", uuid_type, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("context_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mode IN ('single', 'multi')", name="ck_audit_mode"),
        sa.ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="RESTRICT",
            name="fk_audit_project_tenant",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_audit_id_tenant"),
    )
    op.create_index("ix_audits_tenant_project_created", "audits", ["tenant_id", "project_id", "created_at"])
    op.create_table(
        "screen_assets",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", uuid_type, nullable=False),
        sa.Column("uploaded_by", uuid_type, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("object_key", sa.String(900), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("declared_content_type", sa.String(100), nullable=False),
        sa.Column("declared_size", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending_upload', 'uploaded_unverified', 'deleting', 'deleted')",
            name="ck_screen_asset_status",
        ),
        sa.CheckConstraint("declared_size > 0", name="ck_screen_asset_positive_size"),
        sa.ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="RESTRICT",
            name="fk_screen_asset_project_tenant",
        ),
        sa.UniqueConstraint("object_key", name="uq_screen_asset_object_key"),
        sa.UniqueConstraint("uploaded_by", "idempotency_key", name="uq_screen_asset_idempotency"),
    )
    op.create_index(
        "ix_screen_assets_tenant_project_created",
        "screen_assets",
        ["tenant_id", "project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_screen_assets_tenant_project_created", table_name="screen_assets")
    op.drop_table("screen_assets")
    op.drop_index("ix_audits_tenant_project_created", table_name="audits")
    op.drop_table("audits")
    op.drop_index("ix_projects_tenant_updated", table_name="projects")
    op.drop_table("projects")
    op.drop_table("memberships")
    op.drop_table("tenants")
    op.drop_table("users")
