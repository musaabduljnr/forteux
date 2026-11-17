"""Add multi-screen flow support: screen_description, flow_report_json, finding scope, and affected_screen_ids.

Revision ID: 0005_multi_screen_flow
Revises: 0004_knowledge_library
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_multi_screen_flow"
down_revision = "0004_knowledge_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add screen_description to audit_screens
    op.add_column("audit_screens", sa.Column("screen_description", sa.Text(), nullable=True))

    # 2. Add flow_report_json to analysis_jobs
    op.add_column("analysis_jobs", sa.Column("flow_report_json", sa.Text(), nullable=True))

    # 3. Add scope and affected_screen_ids_json to findings
    op.add_column("findings", sa.Column("scope", sa.String(16), server_default="screen_level", nullable=False))
    op.add_column("findings", sa.Column("affected_screen_ids_json", sa.Text(), server_default="[]", nullable=False))


def downgrade() -> None:
    op.drop_column("findings", "affected_screen_ids_json")
    op.drop_column("findings", "scope")
    op.drop_column("analysis_jobs", "flow_report_json")
    op.drop_column("audit_screens", "screen_description")
